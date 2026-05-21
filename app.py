import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "gym-management-secret"
DATABASE = os.path.join(os.path.dirname(__file__), "gym.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
    else:
        conn = get_db_connection()
        columns = conn.execute("PRAGMA table_info(members)").fetchall()
        if not any(col[1] == "trainer_id" for col in columns):
            conn.execute("ALTER TABLE members ADD COLUMN trainer_id INTEGER")
            conn.commit()
        # Ensure users table exists for authentication (migration for older DBs)
        user_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if not user_table:
            conn.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE,
                    phone TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (date('now'))
                )
                """
            )
            conn.commit()
        conn.close()


# Initialize the database when the app module loads.
init_db()


@app.route("/")
def index():
    conn = get_db_connection()
    member_count = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    trainer_count = conn.execute("SELECT COUNT(*) FROM trainers").fetchone()[0]
    class_count = conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
    payment_count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    conn.close()
    return render_template(
        "index.html",
        member_count=member_count,
        trainer_count=trainer_count,
        class_count=class_count,
        payment_count=payment_count,
    )


@app.route("/offers")
def offers():
    return render_template("offers.html")


@app.route('/login', methods=("GET", "POST"))
def login():
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone', '').strip()
        password = request.form.get('password', '')
        conn = get_db_connection()
        user = None
        if '@' in email_or_phone:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email_or_phone,)).fetchone()
        else:
            user = conn.execute('SELECT * FROM users WHERE phone = ?', (email_or_phone,)).fetchone()

        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid credentials.')
            conn.close()
            return redirect(url_for('login'))

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['email'] or user['phone']
        conn.close()
        flash('Logged in successfully.')
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.')
    return redirect(url_for('index'))


@app.route("/members")
def members():
    conn = get_db_connection()
    members = conn.execute(
        "SELECT members.*, trainers.name AS trainer_name "
        "FROM members "
        "LEFT JOIN trainers ON members.trainer_id = trainers.id "
        "ORDER BY members.id DESC"
    ).fetchall()
    conn.close()
    return render_template("members.html", members=members)


@app.route("/members/add", methods=("GET", "POST"))
def add_member():
    membership_type = request.args.get("membership_type", "Monthly")
    conn = get_db_connection()
    trainers = conn.execute("SELECT id, name FROM trainers ORDER BY name").fetchall()

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        membership_type = request.form["membership_type"].strip()
        trainer_id = request.form.get("trainer_id")
        trainer_id = int(trainer_id) if trainer_id else None

        if not name or not email or not phone:
            flash("Please fill out all required fields.")
            conn.close()
            return redirect(url_for("add_member", membership_type=membership_type))

        conn.execute(
            "INSERT INTO members (name, email, phone, membership_type, trainer_id) VALUES (?, ?, ?, ?, ?)",
            (name, email, phone, membership_type, trainer_id),
        )
        conn.commit()
        conn.close()
        flash("Member added successfully.")
        return redirect(url_for("members"))

    conn.close()
    return render_template(
        "add_member.html",
        membership_type=membership_type,
        trainers=trainers,
    )


@app.route("/members/edit/<int:id>", methods=("GET", "POST"))
def edit_member(id):
    conn = get_db_connection()
    member = conn.execute("SELECT * FROM members WHERE id = ?", (id,)).fetchone()
    if not member:
        conn.close()
        flash("Member not found.")
        return redirect(url_for("members"))

    trainers = conn.execute("SELECT id, name FROM trainers ORDER BY name").fetchall()

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        membership_type = request.form["membership_type"].strip()
        trainer_id = request.form.get("trainer_id")
        trainer_id = int(trainer_id) if trainer_id else None

        if not name or not email or not phone:
            flash("Please fill out all required fields.")
            conn.close()
            return redirect(url_for("edit_member", id=id))

        conn.execute(
            "UPDATE members SET name = ?, email = ?, phone = ?, membership_type = ?, trainer_id = ? WHERE id = ?",
            (name, email, phone, membership_type, trainer_id, id),
        )
        conn.commit()
        conn.close()
        flash("Member updated successfully.")
        return redirect(url_for("members"))

    conn.close()
    return render_template("edit_member.html", member=member, trainers=trainers)


@app.route("/members/delete/<int:id>", methods=("POST",))
def delete_member(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM members WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Member deleted.")
    return redirect(url_for("members"))


@app.route("/trainers")
def trainers():
    conn = get_db_connection()
    trainers = conn.execute("SELECT * FROM trainers ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("trainers.html", trainers=trainers)


@app.route("/trainers/add", methods=("GET", "POST"))
def add_trainer():
    if request.method == "POST":
        name = request.form["name"].strip()
        specialty = request.form["specialty"].strip()
        phone = request.form["phone"].strip()

        if not name or not specialty or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_trainer"))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO trainers (name, specialty, phone) VALUES (?, ?, ?)",
            (name, specialty, phone),
        )
        conn.commit()
        conn.close()
        flash("Trainer added successfully.")
        return redirect(url_for("trainers"))

    return render_template("add_trainer.html")


@app.route("/trainers/edit/<int:id>", methods=("GET", "POST"))
def edit_trainer(id):
    conn = get_db_connection()
    trainer = conn.execute("SELECT * FROM trainers WHERE id = ?", (id,)).fetchone()
    if not trainer:
        conn.close()
        flash("Trainer not found.")
        return redirect(url_for("trainers"))

    if request.method == "POST":
        name = request.form["name"].strip()
        specialty = request.form["specialty"].strip()
        phone = request.form["phone"].strip()

        if not name or not specialty or not phone:
            flash("Please fill out all required fields.")
            return redirect(url_for("edit_trainer", id=id))

        conn.execute(
            "UPDATE trainers SET name = ?, specialty = ?, phone = ? WHERE id = ?",
            (name, specialty, phone, id),
        )
        conn.commit()
        conn.close()
        flash("Trainer updated successfully.")
        return redirect(url_for("trainers"))

    conn.close()
    return render_template("edit_trainer.html", trainer=trainer)


@app.route("/trainers/delete/<int:id>", methods=("POST",))
def delete_trainer(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM trainers WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Trainer deleted.")
    return redirect(url_for("trainers"))


@app.route("/classes")
def classes():
    conn = get_db_connection()
    classes = conn.execute("SELECT * FROM classes ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("classes.html", classes=classes)


@app.route("/classes/add", methods=("GET", "POST"))
def add_class():
    if request.method == "POST":
        class_name = request.form["class_name"].strip()
        schedule = request.form["schedule"].strip()
        trainer = request.form["trainer"].strip()

        if not class_name or not schedule or not trainer:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_class"))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO classes (class_name, schedule, trainer) VALUES (?, ?, ?)",
            (class_name, schedule, trainer),
        )
        conn.commit()
        conn.close()
        flash("Class added successfully.")
        return redirect(url_for("classes"))

    return render_template("add_class.html")


@app.route("/classes/edit/<int:id>", methods=("GET", "POST"))
def edit_class(id):
    conn = get_db_connection()
    gym_class = conn.execute("SELECT * FROM classes WHERE id = ?", (id,)).fetchone()
    if not gym_class:
        conn.close()
        flash("Class not found.")
        return redirect(url_for("classes"))

    if request.method == "POST":
        class_name = request.form["class_name"].strip()
        schedule = request.form["schedule"].strip()
        trainer = request.form["trainer"].strip()

        if not class_name or not schedule or not trainer:
            flash("Please fill out all required fields.")
            return redirect(url_for("edit_class", id=id))

        conn.execute(
            "UPDATE classes SET class_name = ?, schedule = ?, trainer = ? WHERE id = ?",
            (class_name, schedule, trainer, id),
        )
        conn.commit()
        conn.close()
        flash("Class updated successfully.")
        return redirect(url_for("classes"))

    conn.close()
    return render_template("edit_class.html", gym_class=gym_class)


@app.route("/classes/delete/<int:id>", methods=("POST",))
def delete_class(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM classes WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Class deleted.")
    return redirect(url_for("classes"))


@app.route("/payments")
def payments():
    conn = get_db_connection()
    payments = conn.execute("SELECT * FROM payments ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("payments.html", payments=payments)


@app.route("/payments/add", methods=("GET", "POST"))
def add_payment():
    if request.method == "POST":
        member_name = request.form["member_name"].strip()
        amount = request.form["amount"].strip()
        payment_date = request.form["payment_date"].strip()
        notes = request.form.get("notes", "").strip()

        if not member_name or not amount or not payment_date:
            flash("Please fill out all required fields.")
            return redirect(url_for("add_payment"))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO payments (member_name, amount, payment_date, notes) VALUES (?, ?, ?, ?)",
            (member_name, amount, payment_date, notes),
        )
        conn.commit()
        conn.close()
        flash("Payment recorded successfully.")
        return redirect(url_for("payments"))

    return render_template("add_payment.html")


if __name__ == "__main__":
    app.run(debug=True)
