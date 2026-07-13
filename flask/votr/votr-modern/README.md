# Vote Modern

A Flask-based voting application with signup/login, poll management, and QR code support.

## Features

- User signup and login
- Admin poll creation and management
- Public voting pages
- QR code generation for sharing polls and login

## Requirements

- Python 3.10+

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
export FLASK_APP=votr.py
export FLASK_DEBUG=1
python -m flask run --host=0.0.0.0 --port=5001
```

Then open:

- http://127.0.0.1:5001/
- http://127.0.0.1:5001/login/qr

## Notes

- The app uses SQLite by default.
- QR login is available through the login QR page.

