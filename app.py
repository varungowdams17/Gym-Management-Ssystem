import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gym-dev-secret-2024")

# On Render/production, use /tmp for writable storage; locally use project dir
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.environ.get("DB_DIR", BASE_DIR), "gym.db")


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS trainers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            phone TEXT NOT NULL,
            hire_date TEXT NOT NULL DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            membership_type TEXT NOT NULL,
            trainer_id INTEGER,
            join_date TEXT NOT NULL DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            schedule TEXT NOT NULL,
            trainer TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            notes TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not password:
            flash("Password is required.")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for("register"))
        if not email and not phone:
            flash("Provide at least an email or phone number.")
            return redirect(url_for("register"))

        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO users (email, phone, password_hash) VALUES (?, ?, ?)",
                (email or None, phone or None, generate_password_hash(password)),
            )
            conn.commit()
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            flash("An account with that email or phone already exists.")
            return redirect(url_for("register"))
        conn.close()

        session.clear()
        session["user_id"] = user_id
        session["user_name"] = email or phone
        flash("Account created. Welcome!")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        identifier = request.form.get("email_or_phone", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        if "@" in identifier:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (identifier,)).fetchone()
        else:
            user = conn.execute("SELECT * FROM users WHERE phone = ?", (identifier,)).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid credentials.")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["email"] or user["phone"]
        flash("Logged in successfully.")
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("login"))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    uid = session["user_id"]
    conn = get_db()
    mc = conn.execute("SELECT COUNT(*) FROM members  WHERE user_id=?", (uid,)).fetchone()[0]
    tc = conn.execute("SELECT COUNT(*) FROM trainers WHERE user_id=?", (uid,)).fetchone()[0]
    cc = conn.execute("SELECT COUNT(*) FROM classes  WHERE user_id=?", (uid,)).fetchone()[0]
    pc = conn.execute("SELECT COUNT(*) FROM payments WHERE user_id=?", (uid,)).fetchone()[0]
    conn.close()
    return render_template("index.html",
        member_count=mc, trainer_count=tc, class_count=cc, payment_count=pc)


@app.route("/offers")
@login_required
def offers():
    return render_template("offers.html")


# ── Members ───────────────────────────────────────────────────────────────────

@app.route("/members")
@login_required
def members():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute(
        "SELECT members.*, trainers.name AS trainer_name FROM members "
        "LEFT JOIN trainers ON members.trainer_id = trainers.id AND trainers.user_id = ? "
        "WHERE members.user_id = ? ORDER BY members.id DESC", (uid, uid)
    ).fetchall()
    conn.close()
    return render_template("members.html", members=rows)


@app.route("/members/add", methods=["GET", "POST"])
@login_required
def add_member():
    uid = session["user_id"]
    membership_type = request.args.get("membership_type", "Monthly")
    conn = get_db()
    trainers = conn.execute("SELECT id, name FROM trainers WHERE user_id=? ORDER BY name", (uid,)).fetchall()
    conn.close()
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        membership_type = request.form["membership_type"].strip()
        trainer_id = request.form.get("trainer_id") or None
        if trainer_id:
            trainer_id = int(trainer_id)
        if not name or not email or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_member"))
        conn = get_db()
        conn.execute(
            "INSERT INTO members (user_id, name, email, phone, membership_type, trainer_id) VALUES (?,?,?,?,?,?)",
            (uid, name, email, phone, membership_type, trainer_id)
        )
        conn.commit()
        conn.close()
        flash("Member added successfully.")
        return redirect(url_for("members"))
    return render_template("add_member.html", membership_type=membership_type, trainers=trainers)


@app.route("/members/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_member(id):
    uid = session["user_id"]
    conn = get_db()
    member = conn.execute("SELECT * FROM members WHERE id=? AND user_id=?", (id, uid)).fetchone()
    trainers = conn.execute("SELECT id, name FROM trainers WHERE user_id=? ORDER BY name", (uid,)).fetchall()
    conn.close()
    if not member:
        flash("Member not found.")
        return redirect(url_for("members"))
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        membership_type = request.form["membership_type"].strip()
        trainer_id = request.form.get("trainer_id") or None
        if trainer_id:
            trainer_id = int(trainer_id)
        if not name or not email or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("edit_member", id=id))
        conn = get_db()
        conn.execute(
            "UPDATE members SET name=?,email=?,phone=?,membership_type=?,trainer_id=? WHERE id=? AND user_id=?",
            (name, email, phone, membership_type, trainer_id, id, uid)
        )
        conn.commit()
        conn.close()
        flash("Member updated.")
        return redirect(url_for("members"))
    return render_template("edit_member.html", member=member, trainers=trainers)


@app.route("/members/delete/<int:id>", methods=["POST"])
@login_required
def delete_member(id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM members WHERE id=? AND user_id=?", (id, uid))
    conn.commit()
    conn.close()
    flash("Member deleted.")
    return redirect(url_for("members"))


# ── Trainers ──────────────────────────────────────────────────────────────────

@app.route("/trainers")
@login_required
def trainers():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute("SELECT * FROM trainers WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    conn.close()
    return render_template("trainers.html", trainers=rows)


@app.route("/trainers/add", methods=["GET", "POST"])
@login_required
def add_trainer():
    uid = session["user_id"]
    if request.method == "POST":
        name = request.form["name"].strip()
        specialty = request.form["specialty"].strip()
        phone = request.form["phone"].strip()
        if not name or not specialty or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_trainer"))
        conn = get_db()
        conn.execute(
            "INSERT INTO trainers (user_id, name, specialty, phone) VALUES (?,?,?,?)",
            (uid, name, specialty, phone)
        )
        conn.commit()
        conn.close()
        flash("Trainer added successfully.")
        return redirect(url_for("trainers"))
    return render_template("add_trainer.html")


@app.route("/trainers/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_trainer(id):
    uid = session["user_id"]
    conn = get_db()
    trainer = conn.execute("SELECT * FROM trainers WHERE id=? AND user_id=?", (id, uid)).fetchone()
    conn.close()
    if not trainer:
        flash("Trainer not found.")
        return redirect(url_for("trainers"))
    if request.method == "POST":
        name = request.form["name"].strip()
        specialty = request.form["specialty"].strip()
        phone = request.form["phone"].strip()
        if not name or not specialty or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("edit_trainer", id=id))
        conn = get_db()
        conn.execute(
            "UPDATE trainers SET name=?,specialty=?,phone=? WHERE id=? AND user_id=?",
            (name, specialty, phone, id, uid)
        )
        conn.commit()
        conn.close()
        flash("Trainer updated.")
        return redirect(url_for("trainers"))
    return render_template("edit_trainer.html", trainer=trainer)


@app.route("/trainers/delete/<int:id>", methods=["POST"])
@login_required
def delete_trainer(id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM trainers WHERE id=? AND user_id=?", (id, uid))
    conn.commit()
    conn.close()
    flash("Trainer deleted.")
    return redirect(url_for("trainers"))


# ── Classes ───────────────────────────────────────────────────────────────────

@app.route("/classes")
@login_required
def classes():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute("SELECT * FROM classes WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    conn.close()
    return render_template("classes.html", classes=rows)


@app.route("/classes/add", methods=["GET", "POST"])
@login_required
def add_class():
    uid = session["user_id"]
    if request.method == "POST":
        class_name = request.form["class_name"].strip()
        schedule = request.form["schedule"].strip()
        trainer = request.form["trainer"].strip()
        if not class_name or not schedule or not trainer:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_class"))
        conn = get_db()
        conn.execute(
            "INSERT INTO classes (user_id, class_name, schedule, trainer) VALUES (?,?,?,?)",
            (uid, class_name, schedule, trainer)
        )
        conn.commit()
        conn.close()
        flash("Class added successfully.")
        return redirect(url_for("classes"))
    return render_template("add_class.html")


@app.route("/classes/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_class(id):
    uid = session["user_id"]
    conn = get_db()
    gym_class = conn.execute("SELECT * FROM classes WHERE id=? AND user_id=?", (id, uid)).fetchone()
    conn.close()
    if not gym_class:
        flash("Class not found.")
        return redirect(url_for("classes"))
    if request.method == "POST":
        class_name = request.form["class_name"].strip()
        schedule = request.form["schedule"].strip()
        trainer = request.form["trainer"].strip()
        if not class_name or not schedule or not trainer:
            flash("Please fill out all required fields.")
            return redirect(url_for("edit_class", id=id))
        conn = get_db()
        conn.execute(
            "UPDATE classes SET class_name=?,schedule=?,trainer=? WHERE id=? AND user_id=?",
            (class_name, schedule, trainer, id, uid)
        )
        conn.commit()
        conn.close()
        flash("Class updated.")
        return redirect(url_for("classes"))
    return render_template("edit_class.html", gym_class=gym_class)


@app.route("/classes/delete/<int:id>", methods=["POST"])
@login_required
def delete_class(id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM classes WHERE id=? AND user_id=?", (id, uid))
    conn.commit()
    conn.close()
    flash("Class deleted.")
    return redirect(url_for("classes"))


# ── Payments ──────────────────────────────────────────────────────────────────

@app.route("/payments")
@login_required
def payments():
    uid = session["user_id"]
    conn = get_db()
    rows = conn.execute("SELECT * FROM payments WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    conn.close()
    return render_template("payments.html", payments=rows)


@app.route("/payments/add", methods=["GET", "POST"])
@login_required
def add_payment():
    uid = session["user_id"]
    if request.method == "POST":
        member_name = request.form["member_name"].strip()
        amount = request.form["amount"].strip()
        payment_date = request.form["payment_date"].strip()
        notes = request.form.get("notes", "").strip()
        if not member_name or not amount or not payment_date:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_payment"))
        conn = get_db()
        conn.execute(
            "INSERT INTO payments (user_id, member_name, amount, payment_date, notes) VALUES (?,?,?,?,?)",
            (uid, member_name, amount, payment_date, notes)
        )
        conn.commit()
        conn.close()
        flash("Payment recorded successfully.")
        return redirect(url_for("payments"))
    return render_template("add_payment.html")


if __name__ == "__main__":
    app.run(debug=True)
