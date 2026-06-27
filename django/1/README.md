# 🐍 Episode 1 — Django Project + First App

## Django MVC EXPOSED (You've Been Learning It Wrong)

Welcome to **Episode 1** of the *Django from Zero to Pro* series.

In this episode, we move from theory to practice by creating your first Django project and your first app.

---

## 🎯 Goal

By the end of this episode, you will have:

* A Django project named `first_project`
* A Django app named `first_app`
* A working Django development server
* A clean base structure for future development

---

## 🧠 Quick Concept Recap (MVT)

Django uses **MVT (Model–View–Template)**:

| Django   | Role                     |
| -------- | ------------------------ |
| Model    | Database layer           |
| View     | Logic layer (Controller) |
| Template | UI layer                 |

> Django = MVC disguised as MVT

---

## 🚀 Project Setup

### 1. Create project folder

```bash
mkdir -p django/1
cd django/1
```

---

### 2. Create virtual environment

```bash
python3 -m venv env
source env/bin/activate
```

---

### 3. Install Django

```bash
python -m pip install --upgrade pip
python -m pip install django
```

---

### 4. Create Django project

```bash
django-admin startproject first_project .
```

---

### 5. Create first app

```bash
python manage.py startapp first_app
```

---

## ⚙️ Register the App

Edit `first_project/settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'first_app',
]
```

---

## 🧪 Run Database Migrations

```bash
python manage.py migrate
```

---

## 🚀 Start Development Server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

---

## 📁 Final Structure

```text
django/
└── 1/
    ├── env/
    ├── manage.py
    ├── first_project/
    ├── first_app/
    └── requirements.txt
```

---

## 💾 Git Snapshot

```bash
git add .
git commit -m "Episode 1 - Create Django project and first app"
git tag django_v0.1
git push origin master
git push origin django_v0.1
```

---

## 🧭 Next Episode

👉 Episode 2 — Django Models & Database Basics
👉 Episode 3 — Django Project Structure Explained
👉 Episode 4 — Django Admin Deep Dive
👉 Episode 5 — Dockerizing Django Project
