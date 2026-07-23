# Vote

A small Flask and SQLAlchemy classroom quiz app built as a learning project.

## What it does

- Lecturers create sessions, questions, answer options, correct answers, time limits, and base points in advance
- Participants join a session by scanning a QR code with their phone
- Each participant answers one timed attempt per question
- The server stores the question start time, calculates the deadline, grades the attempt, and awards score
- Participants see immediate feedback, a speed bonus, and controlled advance between questions

## Tech Stack

- Flask
- Flask-SQLAlchemy
- SQLite
- Jinja2 templates
- Plain JavaScript

## Quiz Rules

- Default time limit: `QUIZ_DEFAULT_TIME_LIMIT_SECONDS=23`
- Default base points: `QUIZ_DEFAULT_POINTS_BASE=10`
- Feedback delay before auto-advance: `QUIZ_FEEDBACK_SECONDS=10`
- Score formula: `bonus = max(time_limit_seconds - time_used_seconds, 0)` and `points_awarded = points_base + bonus` only when the answer is correct
- The browser never sends trusted time, score, correctness, or timeout state. It only submits an option or a timeout request; the server validates the current deadline and computes the result.

The participant state machine uses these states:

```text
loading
answering
submitting
answered_correct
answered_incorrect
timed_out
advancing
completed
error
```

## Run It

```bash
pip install -r requirements.txt
python vote.py
```

The app binds to `0.0.0.0:5000` by default, so you can reach it from your laptop and other devices on the same network.

If you want a QR code that a phone can reach, open the admin page using your computer's LAN address, or set `PUBLIC_BASE_URL` to a network-accessible host such as `http://192.168.1.20:5000` before starting the app. The QR join link creates the participant session automatically when it is opened.

For quick local testing, you can also open `/admin`, paste your laptop's LAN URL into the QR base URL field, and save it there. That changes only the QR preview and lets a phone join without changing server config.

If you do not want to override anything, leave the QR base URL blank and the app will use the server-generated join link.

## Screens

- `/` participant view
- `/admin` lecturer dashboard
- `/join/<token>` QR login entry point
- `/api/state` live participant data
- `/api/admin/state` live admin data
- `/api/questions/<question_id>/vote` idempotent answer/timeout endpoint
- `/api/quiz/advance` manual or automatic participant advance endpoint

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 FLASK_ENV=testing .venv/bin/python -m unittest test_quiz_flow.py
```

The suite covers correct/incorrect answers, timeout, score boundaries, tampered client payloads, invalid options, idempotent replays, deadline persistence after reload, manual/automatic advance, review mode, finalization, keyboard semantics, responsive CSS, and reduced-motion support.

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
test_quiz_flow.py  Server and frontend-contract tests
```

## Notes

- QR codes are rendered with an external QR image service using the session join URL.
- For real phone scanning, point `PUBLIC_BASE_URL` at a reachable host or tunnel URL, or open the admin page through your laptop's LAN IP instead of `127.0.0.1`.
- If you are testing locally from a phone, use the QR base URL field on the admin page to point the QR code at your laptop's reachable address.
- The implementation intentionally stays simple and framework-light so it is easy to study and extend.
