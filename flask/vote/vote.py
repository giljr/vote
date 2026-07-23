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
import math
import socket
import struct
import ipaddress
from datetime import datetime, timedelta
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
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from config import config
from models import (
    db,
    VotingSession,
    Question,
    Option,
    Participant,
    Vote,
    ParticipantSessionState,
    QuestionStart,
    AnswerAttempt,
)


load_dotenv()

app = Flask(__name__)
environment = os.environ.get("FLASK_ENV", "development")
app.config.from_object(config.get(environment, config["default"]))
app.secret_key = app.config["SECRET_KEY"]
db.init_app(app)


QUIZ_ACTIVE_MODE = "active"
QUIZ_COMPLETED_MODE = "completed"


def _utcnow():
    return datetime.utcnow()


def _isoformat(value):
    if value is None:
        return None
    return value.replace(microsecond=0).isoformat() + "Z"


def _coerce_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def _ensure_column(table_name, column_name, definition):
    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        return
    db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {definition}"))
    db.session.commit()


def _ensure_quiz_schema():
    """Add lightweight quiz columns for existing SQLite databases."""

    _ensure_column(
        "questions",
        "time_limit_seconds",
        "time_limit_seconds INTEGER NOT NULL DEFAULT 23",
    )
    _ensure_column(
        "questions",
        "points_base",
        "points_base INTEGER NOT NULL DEFAULT 10",
    )
    _ensure_column(
        "options",
        "is_correct",
        "is_correct BOOLEAN NOT NULL DEFAULT 0",
    )
    _ensure_column(
        "participants",
        "score",
        "score INTEGER NOT NULL DEFAULT 0",
    )


def _ensure_default_correct_options():
    """Old sessions did not have a correct option; use the first one as a default."""

    changed = False
    for question in Question.query.all():
        if question.options and not any(option.is_correct for option in question.options):
            question.options[0].is_correct = True
            changed = True
    if changed:
        db.session.commit()


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
        time_limit_seconds=app.config["QUIZ_DEFAULT_TIME_LIMIT_SECONDS"],
        points_base=app.config["QUIZ_DEFAULT_POINTS_BASE"],
    )
    question_one.options = [
        Option(label="Routing", position=1, is_correct=True),
        Option(label="Templates", position=2),
        Option(label="Database models", position=3),
    ]

    question_two = Question(
        prompt="How confident do you feel with SQLAlchemy?",
        position=2,
        time_limit_seconds=app.config["QUIZ_DEFAULT_TIME_LIMIT_SECONDS"],
        points_base=app.config["QUIZ_DEFAULT_POINTS_BASE"],
    )
    question_two.options = [
        Option(label="Getting started", position=1),
        Option(label="Pretty comfortable", position=2, is_correct=True),
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
    _ensure_quiz_schema()
    try:
        _seed_demo_data()
        _ensure_default_correct_options()
    except OperationalError as exc:
        message = str(exc).lower()
        if "no column named" not in message and "has no column named" not in message:
            raise
        db.session.rollback()
        db.drop_all()
        db.create_all()
        _ensure_quiz_schema()
        _seed_demo_data()
        _ensure_default_correct_options()


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
    return AnswerAttempt.query.filter_by(question_id=question_id).count()


def _deadline_for(start, question):
    return start.started_at + timedelta(seconds=question.time_limit_seconds)


def _remaining_seconds(start, question, now=None):
    now = now or _utcnow()
    remaining = (_deadline_for(start, question) - now).total_seconds()
    return max(0, math.ceil(remaining))


def _clamped_time_used(started_at, answered_at, time_limit_seconds):
    elapsed = (answered_at - started_at).total_seconds()
    return _coerce_int(math.floor(elapsed), 0, 0, time_limit_seconds)


def _calculate_points(is_correct, points_base, time_limit_seconds, time_used_seconds):
    clamped_time = _coerce_int(time_used_seconds, 0, 0, time_limit_seconds)
    bonus = max(time_limit_seconds - clamped_time, 0)
    if not is_correct:
        return 0, 0
    return bonus, points_base + bonus


def _get_correct_option(question):
    return next((option for option in question.options if option.is_correct), None)


def _get_attempt(participant_id, question_id):
    return AnswerAttempt.query.filter_by(
        participant_id=participant_id,
        question_id=question_id,
    ).first()


def _get_or_create_question_start(participant, question):
    question_start = QuestionStart.query.filter_by(
        participant_id=participant.id,
        question_id=question.id,
    ).first()
    if question_start is not None:
        return question_start, False

    question_start = QuestionStart(
        participant_id=participant.id,
        question_id=question.id,
        started_at=_utcnow(),
    )
    db.session.add(question_start)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        question_start = QuestionStart.query.filter_by(
            participant_id=participant.id,
            question_id=question.id,
        ).first()
        if question_start is not None:
            return question_start, False
        raise
    return question_start, True


def _serialize_attempt(attempt):
    if attempt is None:
        return None
    return {
        "id": attempt.id,
        "selected_option_id": attempt.option_id,
        "is_correct": attempt.is_correct,
        "timed_out": attempt.timed_out,
        "points_base": attempt.points_base,
        "bonus_points": attempt.bonus_points,
        "points_awarded": attempt.points_awarded,
        "time_started_at": _isoformat(attempt.time_started_at),
        "time_answered_at": _isoformat(attempt.time_answered_at),
        "time_used_seconds": attempt.time_used_seconds,
    }


def _serialize_question(question, participant_id=None, reveal_correct=False, include_timing=False):
    attempts = (
        db.session.query(
            AnswerAttempt.option_id,
            db.func.count(AnswerAttempt.id),
        )
        .filter(
            AnswerAttempt.question_id == question.id,
            AnswerAttempt.option_id.isnot(None),
        )
        .group_by(AnswerAttempt.option_id)
        .all()
    )
    answer_counts = {option_id: count for option_id, count in attempts}
    total_answers = AnswerAttempt.query.filter_by(question_id=question.id).count()
    participant_attempt = None
    question_start = None

    if participant_id is not None:
        participant_attempt = AnswerAttempt.query.filter_by(
            participant_id=participant_id,
            question_id=question.id,
        ).first()
        question_start = QuestionStart.query.filter_by(
            participant_id=participant_id,
            question_id=question.id,
        ).first()

    reveal_correct = reveal_correct or participant_id is None or participant_attempt is not None
    correct_option = _get_correct_option(question)

    options = []
    for option in question.options:
        count = answer_counts.get(option.id, 0)
        options.append(
            {
                "id": option.id,
                "label": option.label,
                "position": option.position,
                "answers": count,
                "votes": count,
                "percent": round((count / total_answers) * 100) if total_answers else 0,
                "selected": participant_attempt is not None
                and participant_attempt.option_id == option.id,
                "is_correct": option.is_correct if reveal_correct else False,
            }
        )

    payload = {
        "id": question.id,
        "prompt": question.prompt,
        "position": question.position,
        "is_open": question.is_open,
        "time_limit_seconds": question.time_limit_seconds,
        "points_base": question.points_base,
        "total_votes": total_answers,
        "total_answers": total_answers,
        "has_voted": participant_attempt is not None,
        "has_attempt": participant_attempt is not None,
        "selected_option_id": participant_attempt.option_id if participant_attempt else None,
        "correct_option_id": correct_option.id if reveal_correct and correct_option else None,
        "attempt": _serialize_attempt(participant_attempt),
        "options": options,
    }

    if include_timing and question_start is not None:
        payload["started_at"] = _isoformat(question_start.started_at)
        payload["deadline_at"] = _isoformat(_deadline_for(question_start, question))
        payload["remaining_seconds"] = _remaining_seconds(question_start, question)

    return payload


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


def _session_questions(voting_session):
    return list(voting_session.questions)


def _first_question(voting_session):
    questions = _session_questions(voting_session)
    return questions[0] if questions else None


def _ensure_participant_progress(participant, voting_session):
    progress = ParticipantSessionState.query.filter_by(
        participant_id=participant.id,
        session_id=voting_session.id,
    ).first()
    first_question = _first_question(voting_session)
    question_ids = {question.id for question in _session_questions(voting_session)}

    if progress is None:
        progress = ParticipantSessionState(
            participant_id=participant.id,
            session_id=voting_session.id,
            current_question_id=first_question.id if first_question else None,
            mode=QUIZ_ACTIVE_MODE,
        )
        db.session.add(progress)
        db.session.flush()
        return progress

    if progress.mode == QUIZ_COMPLETED_MODE:
        return progress

    if progress.current_question_id not in question_ids:
        progress.current_question_id = first_question.id if first_question else None
    return progress


def _session_attempts(participant, voting_session):
    question_ids = [question.id for question in _session_questions(voting_session)]
    if not question_ids:
        return []
    return AnswerAttempt.query.filter(
        AnswerAttempt.participant_id == participant.id,
        AnswerAttempt.question_id.in_(question_ids),
    ).all()


def _quiz_stats(participant, voting_session):
    attempts = _session_attempts(participant, voting_session)
    answered = len(attempts)
    correct = sum(1 for attempt in attempts if attempt.is_correct)
    return {
        "answered_count": answered,
        "correct_count": correct,
        "accuracy_percent": round((correct / answered) * 100) if answered else 0,
        "score": participant.score or 0,
    }


def _question_index(voting_session, question_id):
    for index, question in enumerate(_session_questions(voting_session), start=1):
        if question.id == question_id:
            return index
    return 0


def _record_attempt(participant, question, option=None, requested_timeout=False):
    existing_attempt = _get_attempt(participant.id, question.id)
    if existing_attempt is not None:
        return existing_attempt, False, None

    question_start, _ = _get_or_create_question_start(participant, question)
    answered_at = _utcnow()
    deadline_reached = answered_at >= _deadline_for(question_start, question)

    if requested_timeout and not deadline_reached:
        return None, False, "time_remaining"

    timed_out = deadline_reached
    if not timed_out and option is None:
        return None, False, "option_required"

    selected_option = None if timed_out else option
    is_correct = bool(selected_option and selected_option.is_correct)
    time_used = _clamped_time_used(
        question_start.started_at,
        answered_at,
        question.time_limit_seconds,
    )
    bonus_points, points_awarded = _calculate_points(
        is_correct,
        question.points_base,
        question.time_limit_seconds,
        time_used,
    )

    attempt = AnswerAttempt(
        participant_id=participant.id,
        question_id=question.id,
        option_id=selected_option.id if selected_option else None,
        is_correct=is_correct,
        timed_out=timed_out,
        points_base=question.points_base,
        bonus_points=bonus_points,
        points_awarded=points_awarded,
        time_started_at=question_start.started_at,
        time_answered_at=answered_at,
        time_used_seconds=time_used,
    )
    db.session.add(attempt)
    participant.score = (participant.score or 0) + points_awarded

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing_attempt = _get_attempt(participant.id, question.id)
        if existing_attempt is not None:
            return existing_attempt, False, None
        raise

    return attempt, True, None


def _status_for_question(attempt, remaining_seconds):
    if attempt is None:
        return "timed_out" if remaining_seconds <= 0 else "answering"
    if attempt.timed_out:
        return "timed_out"
    return "answered_correct" if attempt.is_correct else "answered_incorrect"


def _participant_state_payload(participant, voting_session):
    progress = _ensure_participant_progress(participant, voting_session)
    questions = _session_questions(voting_session)
    stats = _quiz_stats(participant, voting_session)
    payload = {
        "participant": {
            "id": participant.id,
            "display_name": participant.display_name,
        },
        "server_now": _isoformat(_utcnow()),
        "session": _serialize_session(voting_session, participant_id=participant.id),
        "quiz": {
            "state": "completed" if progress.mode == QUIZ_COMPLETED_MODE else "loading",
            "mode": "review" if progress.mode == QUIZ_COMPLETED_MODE else "active",
            "question": None,
            "questions": [],
            "question_index": 0,
            "question_count": len(questions),
            "progress_percent": 100 if progress.mode == QUIZ_COMPLETED_MODE and questions else 0,
            "advance_delay_seconds": app.config["QUIZ_FEEDBACK_SECONDS"],
            "is_last_question": False,
            **stats,
        },
    }

    if not questions:
        db.session.commit()
        return payload

    if progress.mode == QUIZ_COMPLETED_MODE:
        payload["quiz"]["questions"] = [
            _serialize_question(
                question,
                participant_id=participant.id,
                reveal_correct=True,
                include_timing=True,
            )
            for question in questions
        ]
        db.session.commit()
        return payload

    current_question = db.session.get(Question, progress.current_question_id)
    if current_question is None:
        current_question = questions[0]
        progress.current_question_id = current_question.id

    question_start, _ = _get_or_create_question_start(participant, current_question)
    db.session.commit()

    attempt = _get_attempt(participant.id, current_question.id)
    remaining = _remaining_seconds(question_start, current_question)
    if attempt is None and remaining <= 0:
        attempt, _, _ = _record_attempt(
            participant,
            current_question,
            requested_timeout=True,
        )
        stats = _quiz_stats(participant, voting_session)
        question_start = QuestionStart.query.filter_by(
            participant_id=participant.id,
            question_id=current_question.id,
        ).first()

    index = _question_index(voting_session, current_question.id)
    payload["server_now"] = _isoformat(_utcnow())
    payload["session"] = _serialize_session(voting_session, participant_id=participant.id)
    payload["quiz"].update(
        {
            "state": _status_for_question(attempt, _remaining_seconds(question_start, current_question)),
            "question": _serialize_question(
                current_question,
                participant_id=participant.id,
                reveal_correct=attempt is not None,
                include_timing=True,
            ),
            "question_index": index,
            "progress_percent": round((index / len(questions)) * 100),
            "is_last_question": index == len(questions),
            **stats,
        }
    )
    return payload


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
    return render_template(
        "admin.html",
        sessions=sessions,
        default_time_limit=app.config["QUIZ_DEFAULT_TIME_LIMIT_SECONDS"],
        default_points_base=app.config["QUIZ_DEFAULT_POINTS_BASE"],
    )


@app.route("/join/<token>")
def join_session(token):
    """Authenticate a participant by QR-scanned join token."""

    voting_session = VotingSession.query.filter_by(join_token=token).first_or_404()
    participant = Participant(
        display_name=f"Participant {secrets.token_hex(3).upper()}",
    )
    db.session.add(participant)
    db.session.flush()
    _ensure_participant_progress(participant, voting_session)
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

    return _json_no_cache(_participant_state_payload(participant, voting_session))


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
    correct_option_index = _coerce_int(payload.get("correct_option_index"), 0, 0, max(len(options) - 1, 0))
    time_limit_seconds = _coerce_int(
        payload.get("time_limit_seconds"),
        app.config["QUIZ_DEFAULT_TIME_LIMIT_SECONDS"],
        1,
        600,
    )
    points_base = _coerce_int(
        payload.get("points_base"),
        app.config["QUIZ_DEFAULT_POINTS_BASE"],
        0,
        1000,
    )

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    if len(options) < 2:
        return jsonify({"error": "at least two options are required"}), 400

    question = Question(
        prompt=prompt,
        position=(len(voting_session.questions) + 1),
        time_limit_seconds=time_limit_seconds,
        points_base=points_base,
    )
    question.options = [
        Option(
            label=label,
            position=index + 1,
            is_correct=index == correct_option_index,
        )
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
        AnswerAttempt.query.filter(AnswerAttempt.question_id.in_(question_ids)).delete(
            synchronize_session=False,
        )
        QuestionStart.query.filter(QuestionStart.question_id.in_(question_ids)).delete(
            synchronize_session=False,
        )
        ParticipantSessionState.query.filter_by(session_id=voting_session.id).delete(
            synchronize_session=False,
        )
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
    """Record one idempotent quiz attempt per participant per question."""

    participant = _require_participant()
    question = Question.query.get_or_404(question_id)
    voting_session = db.session.get(VotingSession, session.get("session_id"))
    if voting_session is None or question.session_id != voting_session.id:
        return jsonify({"error": "question does not belong to your session"}), 403
    if not question.is_open:
        return jsonify({"error": "this question is closed"}), 409
    payload = request.get_json(silent=True) or {}
    option_id = payload.get("option_id")
    requested_timeout = bool(payload.get("timeout"))

    if option_id is None and not requested_timeout:
        return jsonify({"error": "option_id is required"}), 400

    option = None
    if option_id is not None:
        option = Option.query.filter_by(id=option_id, question_id=question.id).first()
    if option_id is not None and option is None:
        return jsonify({"error": "invalid option"}), 400

    attempt, created, error = _record_attempt(
        participant,
        question,
        option=option,
        requested_timeout=requested_timeout,
    )
    if error == "time_remaining":
        return _json_no_cache(
            {
                "error": "time remains for this question",
                **_participant_state_payload(participant, voting_session),
            },
            status=409,
        )
    if error == "option_required":
        return jsonify({"error": "option_id is required"}), 400

    status = 201 if created else 200
    return _json_no_cache(
        {
            "message": "attempt recorded" if created else "attempt already recorded",
            "attempt": _serialize_attempt(attempt),
            **_participant_state_payload(participant, voting_session),
        },
        status=status,
    )


@app.route("/api/quiz/advance", methods=["POST"])
def api_advance_quiz():
    """Advance the active participant flow after feedback."""

    participant = _require_participant()
    voting_session = db.session.get(VotingSession, session.get("session_id"))
    if voting_session is None:
        return jsonify({"error": "no active session"}), 404

    progress = _ensure_participant_progress(participant, voting_session)
    questions = _session_questions(voting_session)
    if not questions:
        db.session.commit()
        return _json_no_cache(_participant_state_payload(participant, voting_session))

    if progress.mode == QUIZ_COMPLETED_MODE:
        db.session.commit()
        return _json_no_cache(_participant_state_payload(participant, voting_session))

    current_question = db.session.get(Question, progress.current_question_id)
    if current_question is None:
        current_question = questions[0]
        progress.current_question_id = current_question.id

    attempt = _get_attempt(participant.id, current_question.id)
    if attempt is None:
        question_start, _ = _get_or_create_question_start(participant, current_question)
        if _remaining_seconds(question_start, current_question) > 0:
            db.session.commit()
            return _json_no_cache(
                {
                    "error": "answer or timeout required before advancing",
                    **_participant_state_payload(participant, voting_session),
                },
                status=409,
            )
        _record_attempt(participant, current_question, requested_timeout=True)

    current_index = _question_index(voting_session, current_question.id)
    if current_index < len(questions):
        next_question = questions[current_index]
        progress.current_question_id = next_question.id
        progress.mode = QUIZ_ACTIVE_MODE
        _get_or_create_question_start(participant, next_question)
    else:
        progress.current_question_id = None
        progress.mode = QUIZ_COMPLETED_MODE
        progress.completed_at = _utcnow()

    db.session.commit()
    return _json_no_cache(_participant_state_payload(participant, voting_session))


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
    AnswerAttempt.query.filter_by(question_id=question.id).delete(
        synchronize_session=False,
    )
    QuestionStart.query.filter_by(question_id=question.id).delete(
        synchronize_session=False,
    )
    ParticipantSessionState.query.filter_by(current_question_id=question.id).update(
        {"current_question_id": None},
        synchronize_session=False,
    )
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
