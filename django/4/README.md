# 🐳 Episode 4 — Dockerize Django Like a Pro

## The Production Setup Every Developer Should Know

In this episode, we take our Django project from a local development setup to a **Dockerized, production-style environment**.

No more “it works on my machine”.

Now everything is **reproducible, portable, and team-ready**.

---

## 🎯 What You Learn

By the end of this episode, you will have:

* A fully Dockerized Django project
* Reproducible development environment
* Clean separation between app and runtime
* Foundation for production deployment

---

## 🧠 Why Docker?

Docker solves one big problem:

> “It works on my machine”

With Docker you get:

* Same environment everywhere
* No dependency conflicts
* Easy onboarding for new developers
* Production-like setup locally

---

## 📦 Base Project (From Episode 2)

This episode is based on:

```text id="ep4base"
django/2/
```

We copy it into:

```text id="ep4copy"
django/4/
```

---

## 🐳 Step 1 — Dockerize the Project

You will add:

### 📄 Dockerfile

Defines how Django runs inside a container.

### 📄 docker-compose.yml

Defines services (Django, database, etc).

### 📄 .dockerignore

Prevents unnecessary files from being copied.

---

## ⚙️ Step 2 — Build & Run Containers

```bash id="ep4build"
docker compose up --build
```

This will:

* Build Django image
* Start containers
* Expose app on port 8000

---

## 🌐 Step 3 — Access Application

Open:

```text id="ep4url"
http://localhost:8000/
```

---

## ⚠️ Common Issue

If you see:

```text id="ep4hosterror"
DisallowedHost: Invalid HTTP_HOST header
```

Fix in `settings.py`:

```python id="ep4allowedhosts"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
```

---

## 🧱 Final Architecture

```text id="ep4structure"
Browser
   ↓
Docker Container
   ↓
Django App
   ↓
Database (SQLite/PostgreSQL later)
```

---

## 🚀 What You Achieved

✔ Django running inside Docker
✔ Portable development environment
✔ Production-style architecture
✔ Clean separation of concerns

---

## 🧠 Key Idea

> Docker = consistent environment across all machines

---

## 🧭 Next Episode

👉 Episode 5 — Docker Compose + Production Setup
👉 Episode 6 — Deploy Django to the Cloud
