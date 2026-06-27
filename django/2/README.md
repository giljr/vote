# 🐍 Episode 2 — Django Just Got Real

## Your First Database Table (ORM Magic Explained)

In this episode, we turn our Django project into a working backend by creating a real database table using Django ORM.

---

## 🎯 What You Learn

By the end of this episode, you will have:

* A Django model (`Task`)
* A real database table created via migrations
* Django Admin enabled for data management
* A working CRUD backend (via admin panel)

---

## 🧠 Core Concept — Django ORM

| Concept | Meaning          |
| ------- | ---------------- |
| Model   | Database table   |
| Class   | Table structure  |
| Object  | Row in the table |

> Django automatically converts Python models into SQL.

---

## 🧱 Step 1 — Create Model

```python id="ep2model"
from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

---

## 🔁 Step 2 — Create Migrations

```bash id="ep2makemigrations"
python manage.py makemigrations
```

---

## 🏗️ Step 3 — Apply Migrations

```bash id="ep2migrate"
python manage.py migrate
```

This creates the actual SQLite database tables.

---

## 👤 Step 4 — Enable Admin Access

```python id="ep2admin"
from django.contrib import admin
from .models import Task

admin.site.register(Task)
```

---

## 🔐 Step 5 — Create Admin User

```bash id="ep2superuser"
python manage.py createsuperuser
```

---

## 🚀 Step 6 — Run Server

```bash id="ep2run"
python manage.py runserver
```

Open:

```text id="ep2url"
http://127.0.0.1:8000/admin/
```

---

## 📁 Final Result

You now have:

* Django project running
* `Task` database model
* SQLite database created
* Admin panel fully working
* Full CRUD via Django admin

---

## ⚠️ Common Mistakes

* Forgetting to add app in `INSTALLED_APPS`
* Not running `makemigrations`
* Not running `migrate`
* Expecting database tables without migrations

---

## 🧭 Next Episode

👉 Episode 3 — Django File Structure Explained
👉 Episode 4 — Django Admin Customization
👉 Episode 5 — Dockerizing Your Django Project
