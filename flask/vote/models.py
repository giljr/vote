"""
Database models for the voting application.

The schema is intentionally small:
- voting sessions hold the QR join token
- questions belong to sessions
- options belong to questions
- participants join through the QR link
- votes enforce one choice per question per participant
"""

from datetime import datetime
import secrets

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class TimestampMixin:
    """Shared timestamp columns for all models."""

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modified = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class VotingSession(db.Model, TimestampMixin):
    """A lecture or voting room that participants can join."""

    __tablename__ = "voting_sessions"

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), default="", nullable=False)
    join_token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(24),
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    questions = db.relationship(
        "Question",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Question.position, Question.id",
    )

    def __repr__(self):
        return f"<VotingSession {self.title}>"


class Question(db.Model, TimestampMixin):
    """A prompt participants can vote on."""

    __tablename__ = "questions"

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("voting_sessions.id"),
        nullable=False,
    )
    prompt = db.Column(db.String(500), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_open = db.Column(db.Boolean, default=True, nullable=False)

    session = db.relationship("VotingSession", back_populates="questions")
    options = db.relationship(
        "Option",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Option.position, Option.id",
    )
    votes = db.relationship(
        "Vote",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Question {self.prompt}>"


class Option(db.Model, TimestampMixin):
    """An answer option for a question."""

    __tablename__ = "options"

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False,
    )
    label = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    question = db.relationship("Question", back_populates="options")
    votes = db.relationship(
        "Vote",
        back_populates="option",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Option {self.label}>"


class Participant(db.Model, TimestampMixin):
    """A mobile participant that joined through the QR code."""

    __tablename__ = "participants"

    public_id = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_urlsafe(16),
    )
    display_name = db.Column(db.String(120), nullable=False)

    votes = db.relationship(
        "Vote",
        back_populates="participant",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Participant {self.display_name}>"


class Vote(db.Model, TimestampMixin):
    """Stores a single participant vote for a question."""

    __tablename__ = "votes"
    __table_args__ = (
        db.UniqueConstraint(
            "participant_id",
            "question_id",
            name="uq_participant_question_vote",
        ),
    )

    participant_id = db.Column(
        db.Integer,
        db.ForeignKey("participants.id"),
        nullable=False,
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id"),
        nullable=False,
    )
    option_id = db.Column(
        db.Integer,
        db.ForeignKey("options.id"),
        nullable=False,
    )

    participant = db.relationship("Participant", back_populates="votes")
    question = db.relationship("Question", back_populates="votes")
    option = db.relationship("Option", back_populates="votes")

    def __repr__(self):
        return f"<Vote participant={self.participant_id} question={self.question_id}>"
