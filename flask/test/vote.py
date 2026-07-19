import os
import json

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

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
def index():
    """
    Home page.

    Displays available polls from database.
    """

    polls = Poll.query.all()

    return render_template(
        "index.html",
        polls=polls
    )

@app.route("/polls")
def polls():
    """
    Poll creation page.

    Displays the poll creation form with live preview.
    """

    return render_template("polls.html")

@app.route("/api/polls", methods=["POST"])
def create_poll():
    """
    API endpoint to create a new poll.
    
    Expects JSON:
    {
        "title": "Poll title",
        "description": "Optional description",
        "options": ["Option 1", "Option 2", ...]
    }
    """
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        options = data.get("options", [])
        
        if not title:
            return jsonify({"error": "Title is required"}), 400
        
        if not options or len(options) < 2:
            return jsonify({"error": "At least 2 options required"}), 400
        
        # Create topic
        topic = Topic(title=title)
        db.session.add(topic)
        db.session.flush()
        
        # Create poll entries for each option
        for option_name in options:
            option_name = option_name.strip()
            if option_name:
                option = Option(name=option_name)
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
        
        return jsonify({
            "success": True,
            "message": "Poll created successfully",
            "poll_id": topic.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/vote", methods=["POST"])
def vote():
    """
    API endpoint to cast a vote.
    
    Expects JSON:
    {
        "poll_id": 123
    }
    """
    
    try:
        data = request.get_json()
        poll_id = data.get("poll_id")
        
        if not poll_id:
            return jsonify({"error": "Poll ID required"}), 400
        
        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({"error": "Poll not found"}), 404
        
        # Increment vote count
        poll.vote_count += 1
        db.session.commit()
        
        # Get all polls for this topic to calculate percentages
        topic_polls = Poll.query.filter_by(topic_id=poll.topic_id).all()
        total_votes = sum(p.vote_count for p in topic_polls)
        
        # Build response with all options and their vote percentages
        options_data = []
        for p in topic_polls:
            percentage = (p.vote_count / total_votes * 100) if total_votes > 0 else 0
            options_data.append({
                'poll_id': p.id,
                'option': p.option.name,
                'votes': p.vote_count,
                'percentage': round(percentage, 1)
            })
        
        return jsonify({
            "success": True,
            "message": "Vote recorded",
            "total_votes": total_votes,
            "options": options_data
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

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