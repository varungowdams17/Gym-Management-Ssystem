<div align="center">

# 🏋️ GymPro — Gym Management System

**A sleek, full-stack gym management dashboard built with Python Flask and SQLite.**  
Manage members, trainers, classes, and payments from one polished interface.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3.4-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-Templates-E34F26?style=for-the-badge&logo=html5&logoColor=white)

</div>

---

## ✨ Features

| Module | What you can do |
|---|---|
| 👥 **Members** | Add, edit, delete members — assign trainers and track membership type |
| 🏅 **Trainers** | Manage trainer profiles, specialties, and contact info |
| 📅 **Classes** | Schedule and manage gym classes with trainer assignments |
| 💳 **Payments** | Record and track member payments with notes |
| 🎁 **Offers** | View promotional plans and membership deals |
| 🔐 **Auth** | Secure login/logout with hashed passwords |

---

## 🖥️ Tech Stack

- **Backend** — Python 3.10+, Flask 2.3.4
- **Database** — SQLite (auto-initialized from `schema.sql`)
- **Frontend** — Jinja2 HTML templates, vanilla CSS with animated gradients
- **Security** — Werkzeug password hashing, Flask sessions

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/varungowdams17/DBMS.git
cd DBMS
```

### 2. Create and activate a virtual environment

```bash
# Create
python -m venv venv

# Activate — Windows CMD
venv\Scripts\activate.bat

# Activate — Windows PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1

# Activate — macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

### 5. Open in your browser

```
http://127.0.0.1:5000
```

---

## 📁 Project Structure

```
DBMS/
├── app.py               # Flask app — all routes and DB logic
├── schema.sql           # SQLite schema (auto-run on first launch)
├── gym.db               # SQLite database file (auto-created)
├── requirements.txt     # Python dependencies
│
├── templates/           # Jinja2 HTML templates
│   ├── base.html        # Shared layout with nav and header
│   ├── index.html       # Dashboard homepage
│   ├── members.html     # Member list
│   ├── trainers.html    # Trainer list
│   ├── classes.html     # Class schedule
│   ├── payments.html    # Payment records
│   ├── offers.html      # Membership offers
│   ├── login.html       # Login page
│   └── ...              # Add/edit forms
│
└── static/
    ├── css/style.css    # Animated gradient UI styles
    ├── js/main.js       # Frontend interactions
    └── videos/          # Background and showcase videos (add your own)
```

---

## 🗄️ Database Schema

The database is automatically created from `schema.sql` on first run.

```
members    — id, name, email, phone, membership_type, trainer_id, join_date
trainers   — id, name, specialty, phone, hire_date
classes    — id, class_name, schedule, trainer, created_at
payments   — id, member_name, amount, payment_date, notes
users      — id, email, phone, password_hash, created_at
```

---

## 🎥 Video Backgrounds (Optional)

The UI supports background and showcase videos. Place `.mp4` files in `static/videos/` with these names:

```
gym_background.mp4   — full-page background video
gym_cardio.mp4       — cardio section
gym_weights.mp4      — strength section
gym_yoga.mp4         — recovery section
gym_studio.mp4       — studio class section
```

If the files are missing, the app falls back gracefully to CSS gradients.

---

## 🔐 Authentication Note

There is no public registration page. To create the first admin user, run this in a Python shell:

```python
from app import get_db_connection
from werkzeug.security import generate_password_hash

conn = get_db_connection()
conn.execute(
    "INSERT INTO users (email, phone, password_hash) VALUES (?, ?, ?)",
    ("admin@gym.com", "9999999999", generate_password_hash("yourpassword"))
)
conn.commit()
conn.close()
```

Then log in at `http://127.0.0.1:5000/login`.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">
  Made with 💪 for gym admins who mean business.
</div>
