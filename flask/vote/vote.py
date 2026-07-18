"""
Vote Application

A beginner-friendly Flask application demonstrating:

- Flask application setup
- Environment configuration
- SQLAlchemy database integration
- Database-driven routes
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template

from config import config
from models import db, Poll

# Load environment variables from .env
load_dotenv()


# Create Flask application
app = Flask(__name__)


# Select configuration environment
environment = os.environ.get(
    "FLASK_ENV",
    "development"
)

app.config.from_object(
    config[environment]
)


# Initialize database
db.init_app(app)


# Create database tables
# This is acceptable for a beginner tutorial.
# Later chapters can introduce Flask-Migrate.
with app.app_context():
    db.create_all()


from models import Topic, Option, Poll


@app.cli.command("seed")
def seed():
    """
    Populate the database with sample data.
    """

    # Prevent duplicate data
    if Topic.query.first():
        print("Database already contains sample data.")
        return

    topic = Topic(
        title="What is your favorite programming language?"
    )

    db.session.add(topic)
    db.session.commit()

    options = [
        "Python",
        "Java",
        "C#",
        "JavaScript",
        "Go",
        "Rust"
    ]

    for name in options:

        option = Option(name=name)

        db.session.add(option)

        db.session.flush()

        poll = Poll(
            topic_id=topic.id,
            option_id=option.id,
            vote_count=0,
            status=True
        )

        db.session.add(poll)

    db.session.commit()

    print("Sample data inserted successfully.")


@app.route("/")
def home():
    """
    Home page.

    Displays available polls from database.
    """

    polls = Poll.query.all()

    return render_template(
        "index.html",
        polls=polls
    )


@app.route("/health")
def health():
    """
    Simple health check endpoint.
    """

    return {
        "status": "ok",
        "application": "vote"
    }


if __name__ == "__main__":

    app.run(
        debug=app.config["DEBUG"]
    )