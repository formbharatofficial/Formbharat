import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.profile import MAX_PROFILES


DB_PATH = Path(__file__).resolve().parents[2] / "formbharat.db"

APPLICATION_STATUSES = (
    "draft",
    "in_progress",
    "submitted",
    "withdrawn",
)


def _connect():
    return sqlite3.connect(DB_PATH)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _validate_profile_id(profile_id):
    if (
        isinstance(profile_id, bool)
        or not isinstance(profile_id, int)
        or not 1 <= profile_id <= MAX_PROFILES
    ):
        raise ValueError(
            f"profile_id must be an integer between 1 and {MAX_PROFILES}"
        )


def _validate_status(status):
    if status not in APPLICATION_STATUSES:
        allowed = ", ".join(APPLICATION_STATUSES)
        raise ValueError(f"status must be one of: {allowed}")


def _validate_vacancy_id(vacancy_id):
    if vacancy_id is None:
        return None
    if isinstance(vacancy_id, bool) or not isinstance(vacancy_id, int) or vacancy_id < 1:
        raise ValueError("vacancy_id must be a positive integer")
    return vacancy_id


def init_application_tracker_db():
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                vacancy_id INTEGER,
                title TEXT NOT NULL,
                organization TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS application_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _row_to_application(row):
    if row is None:
        return None
    return {
        "id": row[0],
        "profile_id": row[1],
        "vacancy_id": row[2],
        "title": row[3],
        "organization": row[4],
        "status": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def _row_to_history(row):
    return {
        "id": row[0],
        "application_id": row[1],
        "status": row[2],
        "note": row[3],
        "created_at": row[4],
    }


def create_application(
    profile_id,
    title,
    organization="",
    vacancy_id=None,
    status="draft",
    note="",
):
    _validate_profile_id(profile_id)
    _validate_status(status)
    vacancy_id = _validate_vacancy_id(vacancy_id)
    clean_title = str(title or "").strip()
    if not clean_title:
        raise ValueError("title is required")

    now = _now()
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO applications (
                profile_id, vacancy_id, title, organization, status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                vacancy_id,
                clean_title,
                str(organization or "").strip(),
                status,
                now,
                now,
            ),
        )
        application_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO application_status_history (
                application_id, status, note, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (application_id, status, str(note or "").strip(), now),
        )
        conn.commit()
    finally:
        conn.close()
    return get_application(application_id)


def get_application(application_id):
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT id, profile_id, vacancy_id, title, organization, status,
                   created_at, updated_at
            FROM applications
            WHERE id = ?
            """,
            (application_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_application(row)


def list_applications(profile_id, status=None):
    _validate_profile_id(profile_id)
    if status is not None:
        _validate_status(status)

    conn = _connect()
    try:
        if status is None:
            rows = conn.execute(
                """
                SELECT id, profile_id, vacancy_id, title, organization, status,
                       created_at, updated_at
                FROM applications
                WHERE profile_id = ?
                ORDER BY id DESC
                """,
                (profile_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, profile_id, vacancy_id, title, organization, status,
                       created_at, updated_at
                FROM applications
                WHERE profile_id = ? AND status = ?
                ORDER BY id DESC
                """,
                (profile_id, status),
            ).fetchall()
    finally:
        conn.close()
    return [_row_to_application(row) for row in rows]


def update_application_status(application_id, status, note=""):
    _validate_status(status)
    current = get_application(application_id)
    if current is None:
        return None
    if current["status"] == status:
        return current

    now = _now()
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE applications
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, now, application_id),
        )
        conn.execute(
            """
            INSERT INTO application_status_history (
                application_id, status, note, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (application_id, status, str(note or "").strip(), now),
        )
        conn.commit()
    finally:
        conn.close()
    return get_application(application_id)


def list_application_history(application_id):
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, application_id, status, note, created_at
            FROM application_status_history
            WHERE application_id = ?
            ORDER BY id ASC
            """,
            (application_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_history(row) for row in rows]
