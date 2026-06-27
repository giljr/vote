# 🐍 Django from Zero to Pro — Episode 0

## Development Environment Setup

Welcome to the **Django from Zero to Pro** series!

This episode focuses on creating a clean and professional Django development environment. Before writing any application code, we'll prepare everything needed for the rest of the course.

## What You'll Learn

* Create a Python virtual environment
* Install Django
* Create your first Django project
* Run the development server
* Organize your project with a clean structure

## Project Structure

```text
0/
├── env/
├── first_project/
├── manage.py
├── requirements.txt
└── README.md
```

## Getting Started

Create and activate the virtual environment:

```bash
python3 -m venv env
source env/bin/activate
```

Install Django:

```bash
python -m pip install django
```

Create the project:

```bash
django-admin startproject first_project .
```

Run the server:

```bash
python manage.py migrate
python manage.py runserver
```

## Next Episode

➡️ **Episode 1 — Creating Your First Django Project**
