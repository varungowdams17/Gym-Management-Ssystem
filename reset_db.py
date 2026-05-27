"""
Run this once to reset the database with the correct schema.
Usage: python reset_db.py
"""
import os
import sqlite3

DB = os.path.join(os.path.dirname(__file__), "gym.db")
SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")

# Delete old DB
if os.path.exists(DB):
    os.remove(DB)
    print("Old gym.db deleted.")

# Create fresh DB from schema
conn = sqlite3.connect(DB)
with open(SCHEMA, "r", encoding="utf-8") as f:
    conn.executescript(f.read())
conn.commit()

# Verify
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables created:", tables)

for t in tables:
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
    print(f"  {t}: {cols}")

conn.close()
print("\nDone! Now run: python app.py")
