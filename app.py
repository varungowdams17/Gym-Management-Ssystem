import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gym-secret-change-in-prod")

# ── Database config ───────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")  # Set on Vercel
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "gym.db")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

# ── DB connection ─────────────────────────────────────────────────────────────

def get_db():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(SQLITE_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn


def query(sql, params=(), one=False, commit=False):
    """Run a query and return results. Handles both SQLite and PostgreSQL."""
    # Postgres uses %s placeholders, SQLite uses ?
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params)
    result = None
    if commit:
        conn.commit()
        if USE_POSTGRES:
            # Return lastrowid equivalent for INSERT
            try:
                result = cur.fetchone()
            except Exception:
                result = None
    else:
        result = cur.fetchone() if one else cur.fetchall()
    cur.close()
    conn.close()
    return result


def execute(sql, params=(), returning=None):
    """Execute INSERT/UPDATE/DELETE. Returns last inserted row if returning set."""
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")
        if returning:
            sql = sql + f" RETURNING {returning}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params)
    result = None
    if returning:
        result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return result


# ── Schema init ───────────────────────────────────────────────────────────────

def init_db():
    if USE_POSTGRES:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE,
                phone TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                created_at DATE NOT NULL DEFAULT CURRENT_DATE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trainers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                specialty TEXT NOT NULL,
                phone TEXT NOT NULL,
                hire_date DATE NOT NULL DEFAULT CURRENT_DATE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                membership_type TEXT NOT NULL,
                trainer_id INTEGER REFERENCES trainers(id),
                join_date DATE NOT NULL DEFAULT CURRENT_DATE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                class_name TEXT NOT NULL,
                schedule TEXT NOT NULL,
                trainer TEXT NOT NULL,
                created_at DATE NOT NULL DEFAULT CURRENT_DATE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                member_name TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_date DATE NOT NULL,
                notes TEXT
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    else:
        # SQLite
        if not os.path.exists(SQLITE_PATH):
            schema = os.path.join(os.path.dirname(__file__), "schema.sql")
            conn = sqlite3.connect(SQLITE_PATH)
            with open(schema, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()
        else:
            # Migration: add user_id if missing
            conn = sqlite3.connect(SQLITE_PATH)
            for table in ("members", "trainers", "classes", "payments"):
                cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                if "user_id" not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
            cols = [c[1] for c in conn.execute("PRAGMA table_info(members)").fetchall()]
            if "trainer_id" not in cols:
                conn.execute("ALTER TABLE members ADD COLUMN trainer_id INTEGER")
            conn.commit()
            conn.close()


init_db()


# ── Auth decorator ────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/register", methods=("GET", "POST"))
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not password or not confirm:
            flash("Password is required.")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for("register"))
        if not email and not phone:
            flash("Provide at least an email or phone number.")
            return redirect(url_for("register"))

        try:
            if USE_POSTGRES:
                row = execute(
                    "INSERT INTO users (email, phone, password_hash) VALUES (?, ?, ?)",
                    (email or None, phone or None, generate_password_hash(password)),
                    returning="id"
                )
                user_id = row["id"]
            else:
                conn = sqlite3.connect(SQLITE_PATH)
                cur = conn.execute(
                    "INSERT INTO users (email, phone, password_hash) VALUES (?, ?, ?)",
                    (email or None, phone or None, generate_password_hash(password)),
                )
                conn.commit()
                user_id = cur.lastrowid
                conn.close()
        except Exception:
            flash("An account with that email or phone already exists.")
            return redirect(url_for("register"))

        session.clear()
        session["user_id"] = user_id
        session["user_name"] = email or phone
        flash("Account created. Welcome!")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=("GET", "POST"))
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        email_or_phone = request.form.get("email_or_phone", "").strip()
        password = request.form.get("password", "")

        if "@" in email_or_phone:
            user = query("SELECT * FROM users WHERE email = ?", (email_or_phone,), one=True)
        else:
            user = query("SELECT * FROM users WHERE phone = ?", (email_or_phone,), one=True)

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
    member_count  = query("SELECT COUNT(*) as c FROM members  WHERE user_id = ?", (uid,), one=True)["c"]
    trainer_count = query("SELECT COUNT(*) as c FROM trainers WHERE user_id = ?", (uid,), one=True)["c"]
    class_count   = query("SELECT COUNT(*) as c FROM classes  WHERE user_id = ?", (uid,), one=True)["c"]
    payment_count = query("SELECT COUNT(*) as c FROM payments WHERE user_id = ?", (uid,), one=True)["c"]
    return render_template(
        "index.html",
        member_count=member_count,
        trainer_count=trainer_count,
        class_count=class_count,
        payment_count=payment_count,
    )


@app.route("/offers")
@login_required
def offers():
    return render_template("offers.html")


# ── Members ───────────────────────────────────────────────────────────────────

@app.route("/members")
@login_required
def members():
    uid = session["user_id"]
    rows = query(
        "SELECT members.*, trainers.name AS trainer_name "
        "FROM members LEFT JOIN trainers "
        "ON members.trainer_id = trainers.id AND trainers.user_id = ? "
        "WHERE members.user_id = ? ORDER BY members.id DESC",
        (uid, uid),
    )
    return render_template("members.html", members=rows)


@app.route("/members/add", methods=("GET", "POST"))
@login_required
def add_member():
    uid = session["user_id"]
    membership_type = request.args.get("membership_type", "Monthly")
    trainers = query("SELECT id, name FROM trainers WHERE user_id = ? ORDER BY name", (uid,))

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        membership_type = request.form["membership_type"].strip()
        trainer_id = request.form.get("trainer_id")
        trainer_id = int(trainer_id) if trainer_id else None

        if not name or not email or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_member", membership_type=membership_type))

        execute(
            "INSERT INTO members (user_id, name, email, phone, membership_type, trainer_id) VALUES (?, ?, ?, ?, ?, ?)",
            (uid, name, email, phone, membership_type, trainer_id),
        )
        flash("Member added successfully.")
        return redirect(url_for("members"))

    return render_template("add_member.html", membership_type=membership_type, trainers=trainers)


@app.route("/members/edit/<int:id>", methods=("GET", "POST"))
@login_required
def edit_member(id):
    uid = session["user_id"]
    member = query("SELECT * FROM members WHERE id = ? AND user_id = ?", (id, uid), one=True)
    if not member:
        flash("Member not found.")
        return redirect(url_for("members"))

    trainers = query("SELECT id, name FROM trainers WHERE user_id = ? ORDER BY name", (uid,))

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        membership_type = request.form["membership_type"].strip()
        trainer_id = request.form.get("trainer_id")
        trainer_id = int(trainer_id) if trainer_id else None

        if not name or not email or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("edit_member", id=id))

        execute(
            "UPDATE members SET name=?, email=?, phone=?, membership_type=?, trainer_id=? WHERE id=? AND user_id=?",
            (name, email, phone, membership_type, trainer_id, id, uid),
        )
        flash("Member updated successfully.")
        return redirect(url_for("members"))

    return render_template("edit_member.html", member=member, trainers=trainers)


@app.route("/members/delete/<int:id>", methods=("POST",))
@login_required
def delete_member(id):
    uid = session["user_id"]
    execute("DELETE FROM members WHERE id = ? AND user_id = ?", (id, uid))
    flash("Member deleted.")
    return redirect(url_for("members"))


# ── Trainers ──────────────────────────────────────────────────────────────────

@app.route("/trainers")
@login_required
def trainers():
    uid = session["user_id"]
    rows = query("SELECT * FROM trainers WHERE user_id = ? ORDER BY id DESC", (uid,))
    return render_template("trainers.html", trainers=rows)


@app.route("/trainers/add", methods=("GET", "POST"))
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

        execute(
            "INSERT INTO trainers (user_id, name, specialty, phone) VALUES (?, ?, ?, ?)",
            (uid, name, specialty, phone),
        )
        flash("Trainer added successfully.")
        return redirect(url_for("trainers"))

    return render_template("add_trainer.html")


@app.route("/trainers/edit/<int:id>", methods=("GET", "POST"))
@login_required
def edit_trainer(id):
    uid = session["user_id"]
    trainer = query("SELECT * FROM trainers WHERE id = ? AND user_id = ?", (id, uid), one=True)
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

        execute(
            "UPDATE trainers SET name=?, specialty=?, phone=? WHERE id=? AND user_id=?",
            (name, specialty, phone, id, uid),
        )
        flash("Trainer updated successfully.")
        return redirect(url_for("trainers"))

    return render_template("edit_trainer.html", trainer=trainer)


@app.route("/trainers/delete/<int:id>", methods=("POST",))
@login_required
def delete_trainer(id):
    uid = session["user_id"]
    execute("DELETE FROM trainers WHERE id = ? AND user_id = ?", (id, uid))
    flash("Trainer deleted.")
    return redirect(url_for("trainers"))


# ── Classes ───────────────────────────────────────────────────────────────────

@app.route("/classes")
@login_required
def classes():
    uid = session["user_id"]
    rows = query("SELECT * FROM classes WHERE user_id = ? ORDER BY id DESC", (uid,))
    return render_template("classes.html", classes=rows)


@app.route("/classes/add", methods=("GET", "POST"))
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

        execute(
            "INSERT INTO classes (user_id, class_name, schedule, trainer) VALUES (?, ?, ?, ?)",
            (uid, class_name, schedule, trainer),
        )
        flash("Class added successfully.")
        return redirect(url_for("classes"))

    return render_template("add_class.html")


@app.route("/classes/edit/<int:id>", methods=("GET", "POST"))
@login_required
def edit_class(id):
    uid = session["user_id"]
    gym_class = query("SELECT * FROM classes WHERE id = ? AND user_id = ?", (id, uid), one=True)
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

        execute(
            "UPDATE classes SET class_name=?, schedule=?, trainer=? WHERE id=? AND user_id=?",
            (class_name, schedule, trainer, id, uid),
        )
        flash("Class updated successfully.")
        return redirect(url_for("classes"))

    return render_template("edit_class.html", gym_class=gym_class)


@app.route("/classes/delete/<int:id>", methods=("POST",))
@login_required
def delete_class(id):
    uid = session["user_id"]
    execute("DELETE FROM classes WHERE id = ? AND user_id = ?", (id, uid))
    flash("Class deleted.")
    return redirect(url_for("classes"))


# ── Payments ──────────────────────────────────────────────────────────────────

@app.route("/payments")
@login_required
def payments():
    uid = session["user_id"]
    rows = query("SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC", (uid,))
    return render_template("payments.html", payments=rows)


@app.route("/payments/add", methods=("GET", "POST"))
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

        execute(
            "INSERT INTO payments (user_id, member_name, amount, payment_date, notes) VALUES (?, ?, ?, ?, ?)",
            (uid, member_name, amount, payment_date, notes),
        )
        flash("Payment recorded successfully.")
        return redirect(url_for("payments"))

    return render_template("add_payment.html")


if __name__ == "__main__":
    app.run(debug=True)
