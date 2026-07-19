# Vote

A small Flask and SQLAlchemy voting app built as a learning project.

## What it does

- Lecturers create voting sessions, questions, and answer options in advance
- Participants join a session by scanning a QR code with their phone
- Each participant can vote once per question
- Results update live in the browser through JavaScript polling

## Tech Stack

- Flask
- Flask-SQLAlchemy
- SQLite
- Jinja2 templates
- Plain JavaScript

## Run It

```bash
pip install -r requirements.txt
python vote.py
```

The app runs at `http://localhost:5000`.

If you want a QR code that a phone can reach, set `PUBLIC_BASE_URL` to a network-accessible host such as `http://192.168.1.20:5000` before starting the app.

## Screens

- `/` participant view
- `/admin` lecturer dashboard
- `/join/<token>` QR login entry point
- `/api/state` live participant data
- `/api/admin/state` live admin data

## Demo Data

The app creates a sample session with a few questions the first time it starts against an empty database.

If you want to seed again after clearing the database, run:

```bash
flask --app vote seed
```

## Project Structure

```text
vote.py            Flask application and routes
models.py          SQLAlchemy models
templates/         HTML templates
static/css/        Styling
static/js/        Frontend behavior
```

## Notes

- QR codes are rendered with an external QR image service using the session join URL.
- For real phone scanning, point `PUBLIC_BASE_URL` at a reachable host or tunnel URL.
- The implementation intentionally stays simple and framework-light so it is easy to study and extend.
