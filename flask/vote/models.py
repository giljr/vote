from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Base(db.Model):
    """Base model for other models to inherit from."""
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    date_modified = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


class Topics(Base):
    """Model for poll topics."""
    title = db.Column(db.String(500))

    def __repr__(self):
        return self.title


class Options(Base):
    """Model for poll options."""
    name = db.Column(db.String(200))

    def __repr__(self):
        return self.name


class Polls(Base):
    """Model to connect topics and options together."""
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'))
    option_id = db.Column(db.Integer, db.ForeignKey('options.id'))
    vote_count = db.Column(db.Integer, default=0)
    status = db.Column(db.Boolean)  # Mark poll as open or closed

    # Relationships for easier access across related models
    topic = db.relationship(
        'Topics',
        foreign_keys=[topic_id],
        backref=db.backref('polls', lazy='dynamic')
    )
    option = db.relationship('Options', foreign_keys=[option_id])

    def __repr__(self):
        return f"Poll: {self.option.name}"