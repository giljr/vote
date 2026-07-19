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
        return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    return url_for("index", _external=True).rstrip("/") + path


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
        return jsonify(
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
        return jsonify(
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

    return jsonify(
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

    return jsonify(
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
    db.session.delete(voting_session)
    db.session.commit()
    return jsonify({"sessions": []}), 200


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
    app.run(debug=app.config["DEBUG"])
