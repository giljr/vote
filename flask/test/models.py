from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Base(db.Model):
    """
    Base model.

    Provides common fields:
    - id
    - creation date
    - modification date
    """

    __abstract__ = True

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    date_created = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    date_modified = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class Topic(Base):
    """
    Represents a voting topic.
    """

    __tablename__ = "topics"

    title = db.Column(
        db.String(500),
        nullable=False
    )

    def __repr__(self):
        return f"<Topic {self.title}>"

class Option(Base):
    """
    Represents a possible voting option.
    """

    __tablename__ = "options"

    name = db.Column(
        db.String(200),
        nullable=False
    )

    def __repr__(self):
        return f"<Option {self.name}>"

class Poll(Base):
    """
    Connects a topic with available options.

    Example:

    Topic:
        Favorite programming language?

    Options:
        Python
        Ruby
        JavaScript
    """

    __tablename__ = "polls"

    topic_id = db.Column(
        db.Integer,
        db.ForeignKey("topics.id"),
        nullable=False
    )

    option_id = db.Column(
        db.Integer,
        db.ForeignKey("options.id"),
        nullable=False
    )

    vote_count = db.Column(
        db.Integer,
        default=0
    )

    status = db.Column(
        db.Boolean,
        default=True
    )

    topic = db.relationship(
        "Topic",
        backref=db.backref(
            "polls",
            lazy=True
        )
    )

    option = db.relationship(
        "Option"
    )

    def __repr__(self):
        return (
            f"<Poll "
            f"{self.topic.title}: "
            f"{self.option.name}>"
    )