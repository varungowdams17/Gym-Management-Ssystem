# Gym Management System

This sample gym management system is built with Python Flask for the backend and SQLite for the database. The frontend uses HTML, CSS, and basic Flask templates.

## Features
- Member management (add, edit, delete)
- Trainer management (add, edit, delete)
- Class management (add, edit, delete)
- Payment tracking

## Setup
1. Install Python 3.10+.
2. Open a terminal in `c:\Users\varun\Desktop\project\DBMS`.
3. Create and activate a virtual environment:
   - `python -m venv venv`
   - `venv\Scripts\activate`
4. Install dependencies:
   - `pip install -r requirements.txt`
5. Run the application:
   - `python app.py`
6. Open your browser at `http://127.0.0.1:5000`.

## Database
The SQLite database file `gym.db` is created automatically when the app first runs using `schema.sql`.

## Project Structure
- `app.py` — Flask backend and route handlers
- `schema.sql` — SQLite schema definitions
- `templates/` — HTML views
- `static/css/style.css` — styling
- `static/js/main.js` — optional frontend JS
