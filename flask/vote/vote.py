"""
Vote Application
A Flask web app for subscribing to questions and submitting answers.
"""
import os
from flask import Flask
from config import config
from models import db

from dotenv import load_dotenv

load_dotenv()

# Create Flask application instance
app = Flask(__name__)

# Load configuration based on FLASK_ENV (default: development)
environment = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[environment])

# Initialize SQLAlchemy with the Flask app
db.init_app(app)

# Create database tables (run once on first startup)
with app.app_context():
    db.create_all()


@app.route('/')
def home():
    """Home route - returns welcome message."""
    return 'hello world'


if __name__ == '__main__':
    app.run()