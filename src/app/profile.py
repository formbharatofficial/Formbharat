import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "formbharat.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            mobile TEXT NOT NULL DEFAULT '',
            dob TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT 'in'
        )
    """)
    conn.commit()
    conn.close()


def save_profile(data):
    init_db()

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        INSERT INTO profile
        (id, name, email, mobile, dob, address, country)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            mobile=excluded.mobile,
            dob=excluded.dob,
            address=excluded.address,
            country=excluded.country
    """, (
        data.get("name", "").strip(),
        data.get("email", "").strip(),
        data.get("mobile", "").strip(),
        data.get("dob", "").strip(),
        data.get("address", "").strip(),
        data.get("country", "in").strip()
    ))

    conn.commit()
    conn.close()


def get_profile():
    init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        "SELECT name, email, mobile, dob, address, country FROM profile WHERE id=1"
    ).fetchone()

    conn.close()

    if row is None:
        return {
            "name": "",
            "email": "",
            "mobile": "",
            "dob": "",
            "address": "",
            "country": "in"
        }

    return dict(row)
