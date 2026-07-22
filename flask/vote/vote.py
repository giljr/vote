"""
Real-time voting application built with Flask and SQLAlchemy.

The app keeps the implementation intentionally small:
- lecturers create sessions, questions, and options
- participants join with a QR code
- participants cast one vote per question
- the frontend polls JSON endpoints to update results live
"""

import os
import secrets
import fcntl
import socket
import struct
import ipaddress
from urllib.parse import urlparse, urlunparse
from urllib.parse import urljoin

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency for local development
    def load_dotenv():
        return False
from flask import (
    Flask,
    abort,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import OperationalError

from config import config
from models import db, VotingSession, Question, Option, Participant, Vote


load_dotenv()

app = Flask(__name__)
environment = os.environ.get("FLASK_ENV", "development")
app.config.from_object(config.get(environment, config["default"]))
app.secret_key = app.config["SECRET_KEY"]
db.init_app(app)


def _seed_demo_data():
    """Create a small demo session when the database is empty."""

    if VotingSession.query.first():
        return

    session_obj = VotingSession(
        title="Intro to Flask voting",
        description="A sample session you can use right away.",
    )

    question_one = Question(
        prompt="Which topic should we cover first?",
        position=1,
    )
    question_one.options = [
        Option(label="Routing", position=1),
        Option(label="Templates", position=2),
        Option(label="Database models", position=3),
    ]

    question_two = Question(
        prompt="How confident do you feel with SQLAlchemy?",
        position=2,
    )
    question_two.options = [
        Option(label="Getting started", position=1),
        Option(label="Pretty comfortable", position=2),
        Option(label="Ready to teach it", position=3),
    ]

    session_obj.questions = [question_one, question_two]
    db.session.add(session_obj)
    db.session.commit()


def _build_public_url(path):
    """Build a URL that participants on a phone can reach."""

    base_url = app.config.get("PUBLIC_BASE_URL")
    if base_url:
        return urljoin(_normalize_join_base(base_url).rstrip("/") + "/", path.lstrip("/"))

    host_url = request.host_url.rstrip("/")
    if host_url.startswith("http://127.0.0.1") or host_url.startswith("http://localhost"):
        host_url = _lan_base_url()
    return _normalize_join_base(host_url).rstrip("/") + path


def _normalize_join_base(base_url):
    """Prefer plain HTTP for local/private hosts to avoid certificate errors."""

    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""
    if _is_private_or_local_host(hostname) and parsed.scheme == "https":
        parsed = parsed._replace(scheme="http")
    return urlunparse(parsed)


def _is_private_or_local_host(hostname):
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True

    try:
        return ipaddress.ip_address(hostname).is_private or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return hostname.endswith(".local")


def _lan_base_url():
    """Best-effort LAN URL for QR links when PUBLIC_BASE_URL is not set."""

    port = os.environ.get("PORT", "5000")

    try:
        for _, interface in socket.if_nameindex():
            if interface == "lo":
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    iface_bytes = struct.pack("256s", interface[:15].encode("utf-8"))
                    response = fcntl.ioctl(sock.fileno(), 0x8915, iface_bytes)
                    candidate = socket.inet_ntoa(response[20:24])
                    if not candidate.startswith("127."):
                        return f"http://{candidate}:{port}"
            except OSError:
                continue
    except PermissionError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
    except OSError:
        local_ip = "127.0.0.1"
    return f"http://{local_ip}:{port}"


with app.app_context():
    db.create_all()
    try:
        _seed_demo_data()
    except OperationalError as exc:
        message = str(exc).lower()
        if "no column named" not in message and "has no column named" not in message:
            raise
        db.session.rollback()
        db.drop_all()
        db.create_all()
        _seed_demo_data()


def _current_participant():
    participant_id = session.get("participant_id")
    if not participant_id:
        return None
    return db.session.get(Participant, participant_id)


def _require_participant():
    participant = _current_participant()
    if participant is None:
        abort(401)
    return participant


def _question_vote_count(question_id):
    return Vote.query.filter_by(question_id=question_id).count()


def _serialize_question(question, participant_id=None):
    votes = (
        db.session.query(
            Vote.option_id,
            db.func.count(Vote.id),
        )
        .filter(Vote.question_id == question.id)
        .group_by(Vote.option_id)
        .all()
    )
    vote_counts = {option_id: count for option_id, count in votes}
    total_votes = sum(vote_counts.values())
    participant_vote = None

    if participant_id is not None:
        participant_vote = Vote.query.filter_by(
            participant_id=participant_id,
            question_id=question.id,
        ).first()

    options = []
    for option in question.options:
        count = vote_counts.get(option.id, 0)
        options.append(
            {
                "id": option.id,
                "label": option.label,
                "position": option.position,
                "votes": count,
                "percent": round((count / total_votes) * 100) if total_votes else 0,
                "selected": participant_vote is not None
                and participant_vote.option_id == option.id,
            }
        )

    return {
        "id": question.id,
        "prompt": question.prompt,
        "position": question.position,
        "is_open": question.is_open,
        "total_votes": total_votes,
        "has_voted": participant_vote is not None,
        "selected_option_id": participant_vote.option_id if participant_vote else None,
        "options": options,
    }


def _serialize_session(voting_session, participant_id=None):
    return {
        "id": voting_session.id,
        "title": voting_session.title,
        "description": voting_session.description,
        "is_active": voting_session.is_active,
        "join_url": _build_public_url(url_for("join_session", token=voting_session.join_token)),
        "join_token": voting_session.join_token,
        "questions": [
            _serialize_question(question, participant_id=participant_id)
            for question in voting_session.questions
        ],
    }


def _json_no_cache(payload, status=200):
    response = make_response(jsonify(payload), status)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.context_processor
def inject_current_participant():
    """Expose the logged-in participant to templates."""

    return {"current_participant": _current_participant()}


@app.route("/")
def index():
    """Participant dashboard and public entry point."""

    participant = _current_participant()
    active_session = None
    if participant is not None:
        active_session = (
            VotingSession.query.filter_by(id=session.get("session_id")).first()
        )

    sessions = VotingSession.query.order_by(VotingSession.date_created.desc()).all()
    return render_template(
        "index.html",
        participant=participant,
        active_session=active_session,
        sessions=sessions,
    )


@app.route("/admin")
def admin():
    """Simple lecturer/admin dashboard."""

    sessions = VotingSession.query.order_by(VotingSession.date_created.desc()).all()
    return render_template("admin.html", sessions=sessions)


@app.route("/join/<token>")
def join_session(token):
    """Authenticate a participant by QR-scanned join token."""

    voting_session = VotingSession.query.filter_by(join_token=token).first_or_404()
    participant = Participant(
        display_name=f"Participant {secrets.token_hex(3).upper()}",
    )
    db.session.add(participant)
    db.session.commit()

    session["participant_id"] = participant.id
    session["session_id"] = voting_session.id

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    """Clear the current participant session."""

    session.pop("participant_id", None)
    session.pop("session_id", None)
    return redirect(url_for("index"))


@app.route("/api/state")
def api_state():
    """Return the current participant session state."""

    participant = _current_participant()
    if participant is None:
        return _json_no_cache(
            {
                "participant": None,
                "session": None,
                "sessions": [
                    _serialize_session(voting_session)
                    for voting_session in VotingSession.query.order_by(
                        VotingSession.date_created.desc()
                    )
                ],
            }
        )

    voting_session = db.session.get(VotingSession, session.get("session_id"))
    if voting_session is None:
        session.pop("session_id", None)
        return _json_no_cache(
            {
                "participant": {
                    "id": participant.id,
                    "display_name": participant.display_name,
                },
                "session": None,
                "sessions": [
                    _serialize_session(voting_session)
                    for voting_session in VotingSession.query.order_by(
                        VotingSession.date_created.desc()
                    )
                ],
            }
        )

    return _json_no_cache(
        {
            "participant": {
                "id": participant.id,
                "display_name": participant.display_name,
            },
            "session": _serialize_session(
                voting_session,
                participant_id=participant.id,
            ),
        }
    )


@app.route("/api/admin/state")
def api_admin_state():
    """Return all sessions for the admin UI."""

    return _json_no_cache(
        {
            "sessions": [
                _serialize_session(voting_session)
                for voting_session in VotingSession.query.order_by(
                    VotingSession.date_created.desc()
                )
            ]
        }
    )


@app.route("/api/sessions", methods=["POST"])
def api_create_session():
    """Create a voting session from the admin UI."""

    payload = request.get_json(force=True)
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()

    if not title:
        return jsonify({"error": "title is required"}), 400

    voting_session = VotingSession(
        title=title,
        description=description,
    )
    db.session.add(voting_session)
    db.session.commit()

    return jsonify(_serialize_session(voting_session)), 201


@app.route("/api/sessions/<int:session_id>/questions", methods=["POST"])
def api_create_question(session_id):
    """Create a question with answer options."""

    voting_session = VotingSession.query.get_or_404(session_id)
    payload = request.get_json(force=True)
    prompt = (payload.get("prompt") or "").strip()
    raw_options = payload.get("options") or []
    options = [value.strip() for value in raw_options if value and value.strip()]

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    if len(options) < 2:
        return jsonify({"error": "at least two options are required"}), 400

    question = Question(
        prompt=prompt,
        position=(len(voting_session.questions) + 1),
    )
    question.options = [
        Option(label=label, position=index + 1)
        for index, label in enumerate(options)
    ]
    voting_session.questions.append(question)
    db.session.commit()

    return jsonify(_serialize_session(voting_session)), 201


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def api_delete_session(session_id):
    """Delete a voting session."""

    voting_session = VotingSession.query.get_or_404(session_id)
    question_ids = [question.id for question in voting_session.questions]

    if session.get("session_id") == voting_session.id:
        session.pop("participant_id", None)
        session.pop("session_id", None)

    if question_ids:
        Vote.query.filter(Vote.question_id.in_(question_ids)).delete(
            synchronize_session=False,
        )
        Option.query.filter(
            Option.question_id.in_(question_ids),
        ).delete(synchronize_session=False)
        Question.query.filter(Question.id.in_(question_ids)).delete(
            synchronize_session=False,
        )

    VotingSession.query.filter_by(id=voting_session.id).delete(
        synchronize_session=False,
    )
    db.session.commit()
    return jsonify(
        {
            "sessions": [
                _serialize_session(session_obj)
                for session_obj in VotingSession.query.order_by(
                    VotingSession.date_created.desc()
                )
            ]
        }
    ), 200


@app.route("/api/questions/<int:question_id>/vote", methods=["POST"])
def api_vote(question_id):
    """Record one vote per participant per question."""

    participant = _require_participant()
    question = Question.query.get_or_404(question_id)
    if not question.is_open:
        return jsonify({"error": "this question is closed"}), 409
    payload = request.get_json(force=True)
    option_id = payload.get("option_id")

    if option_id is None:
        return jsonify({"error": "option_id is required"}), 400

    option = Option.query.filter_by(id=option_id, question_id=question.id).first()
    if option is None:
        return jsonify({"error": "invalid option"}), 400

    existing_vote = Vote.query.filter_by(
        participant_id=participant.id,
        question_id=question.id,
    ).first()
    if existing_vote is not None:
        if existing_vote.option_id == option.id:
            return jsonify(
                {
                    "message": "vote already recorded",
                    "question": _serialize_question(question, participant.id),
                }
            )
        return jsonify({"error": "you have already voted on this question"}), 409

    vote = Vote(
        participant_id=participant.id,
        question_id=question.id,
        option_id=option.id,
    )
    db.session.add(vote)
    db.session.commit()

    return jsonify(
        {
            "message": "vote recorded",
            "question": _serialize_question(question, participant.id),
        }
    ), 201


@app.route("/api/questions/<int:question_id>/toggle", methods=["POST"])
def api_toggle_question(question_id):
    """Open or close a question from the admin UI."""

    question = Question.query.get_or_404(question_id)
    question.is_open = not question.is_open
    db.session.commit()
    return jsonify(_serialize_session(question.session)), 200


@app.route("/api/questions/<int:question_id>", methods=["DELETE"])
def api_delete_question(question_id):
    """Delete a question from the admin UI."""

    question = Question.query.get_or_404(question_id)
    session_obj = question.session
    db.session.delete(question)
    db.session.commit()
    return jsonify(_serialize_session(session_obj)), 200


@app.cli.command("seed")
def seed():
    """Reset the demo session content if the database is empty."""

    if VotingSession.query.first():
        print("Database already contains voting sessions.")
        return

    _seed_demo_data()
    print("Sample voting session inserted successfully.")


@app.route("/health")
def health():
    """Simple health check endpoint."""

    return {"status": "ok", "application": "vote"}


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
        debug=app.config["DEBUG"],
    )
