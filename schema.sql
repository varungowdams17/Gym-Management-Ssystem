DROP TABLE IF EXISTS members;
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    membership_type TEXT NOT NULL,
    trainer_id INTEGER,
    join_date TEXT NOT NULL DEFAULT (date('now'))
);

DROP TABLE IF EXISTS trainers;
CREATE TABLE trainers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialty TEXT NOT NULL,
    phone TEXT NOT NULL,
    hire_date TEXT NOT NULL DEFAULT (date('now'))
);

DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    phone TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (date('now'))
);

DROP TABLE IF EXISTS classes;
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name TEXT NOT NULL,
    schedule TEXT NOT NULL,
    trainer TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (date('now'))
);

DROP TABLE IF EXISTS payments;
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_name TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_date TEXT NOT NULL,
    notes TEXT
);
