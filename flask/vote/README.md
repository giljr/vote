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
- For real phone scanning, point `PUBLIC_BASE_URL` at a reachable host or tunnel URL, or open the admin page through your laptop's LAN IP instead of `127.0.0.1`.
- If you are testing locally from a phone, use the QR base URL field on the admin page to point the QR code at your laptop's reachable address.
- The implementation intentionally stays simple and framework-light so it is easy to study and extend.
