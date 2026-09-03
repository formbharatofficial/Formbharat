import json
import sqlite3
from pathlib import Path

from app.profile import DB_PATH, MAX_PROFILES, PROFILE_FIELDS, PROFILE_DEFAULTS


def _validate_profile_id(profile_id):
    if (
        isinstance(profile_id, bool)
        or not isinstance(profile_id, int)
        or not 1 <= profile_id <= MAX_PROFILES
    ):
        raise ValueError(
            f"profile_id must be an integer between 1 and {MAX_PROFILES}"
        )


def init_verified_profile_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verified_profile (
                profile_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL DEFAULT '{}',
                verified INTEGER NOT NULL DEFAULT 0,
                verified_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_verified_profile(data, profile_id=1, verified=False):
    _validate_profile_id(profile_id)

    if not isinstance(data, dict):
        raise ValueError("verified profile data must be a dictionary")

    init_verified_profile_db()

    clean = dict(PROFILE_DEFAULTS)
    for field in PROFILE_FIELDS:
        if field in data and data[field] not in (None, ""):
            clean[field] = str(data[field]).strip()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO verified_profile
                (profile_id, data, verified, verified_at)
            VALUES (?, ?, ?, CASE WHEN ? = 1
                THEN CURRENT_TIMESTAMP ELSE NULL END)
            ON CONFLICT(profile_id) DO UPDATE SET
                data=excluded.data,
                verified=excluded.verified,
                verified_at=excluded.verified_at
        """, (
            profile_id,
            json.dumps(clean, ensure_ascii=False),
            1 if verified else 0,
            1 if verified else 0,
        ))
        conn.commit()
    finally:
        conn.close()


def get_verified_profile(profile_id=1):
    _validate_profile_id(profile_id)
    init_verified_profile_db()

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("""
            SELECT data, verified
            FROM verified_profile
            WHERE profile_id = ?
        """, (profile_id,)).fetchone()
    finally:
        conn.close()

    if row is None or row[1] != 1:
        return None

    try:
        data = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None
