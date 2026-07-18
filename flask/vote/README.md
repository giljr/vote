# Vote — Flask Voting & Subscription Platform

A lightweight Flask web application that enables users to **subscribe to questions** and **submit answers** in real-time. Users can browse questions, follow topics they care about, and contribute their knowledge through answers.

## Features

- **Question Browsing** — View all posted questions and filter by category/topic
- **User Subscription** — Subscribe to questions to receive notifications about new answers
- **Answer Submission** — Users can submit answers to questions they're interested in
- **Real-time Updates** — See new answers as they're posted (optional WebSocket enhancement)
- **User Profiles** — Track your subscriptions and answer history
- **Voting System** — Upvote/downvote answers to highlight the best solutions

## Tech Stack

- **Framework**: Flask 3.1.3
- **Language**: Python 3.12+
- **Database**: (To be configured — SQLite/PostgreSQL recommended)
- **Frontend**: HTML/CSS/JavaScript (Jinja2 templates)

## Project Structure

```
vote/
├── vote.py              # Main Flask application
├── .venv/               # Virtual environment
├── requirements.txt     # Python dependencies (to be created)
├── templates/           # Jinja2 HTML templates (to be created)
├── static/              # CSS, JavaScript, images (to be created)
└── .github/
    └── copilot-instructions.md
```

## Quick Start

### 1. Activate Virtual Environment

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

**On Windows:**
```bash
.venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

**Option A — Direct Python:**
```bash
python vote.py
```

**Option B — Flask CLI:**
```bash
export FLASK_APP=vote:votr  # or set FLASK_APP=vote:votr on Windows
flask run --reload
```

The app will be available at `http://localhost:5000`

## Development

### Project Entry Point

The Flask app instance is named `votr` (not the conventional `app`). When using Flask CLI tools, always reference it as:
```bash
FLASK_APP=vote:votr flask <command>
```

### Add Dependencies

Update `requirements.txt` with new packages:
```bash
pip install <package-name>
pip freeze > requirements.txt
```

### Running Tests

Tests are not yet configured. To add pytest:
```bash
pip install pytest pytest-flask
pytest tests/
```

## Next Steps / Roadmap

- [ ] Set up database (SQLAlchemy ORM)
- [ ] Create user authentication (login/register)
- [ ] Build question model and database schema
- [ ] Add answer submission & voting logic
- [ ] Create HTML templates for question browsing
- [ ] Implement subscription functionality
- [ ] Add notification system
- [ ] Write unit and integration tests
- [ ] Deploy to production (Gunicorn + Nginx)

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Commit with a clear message: `git commit -m "Add feature description"`
4. Push to your branch: `git push origin feature/your-feature`
5. Open a pull request

## License

MIT

## Contact

For questions or suggestions, open an issue on [GitHub](https://github.com/giljr/vote).
