import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[2] / "formbharat.db"


def _connect():
    return sqlite3.connect(DB_PATH)


def init_vacancy_db():
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            category TEXT,
            description TEXT,
            eligibility TEXT,
            application_start TEXT,
            application_end TEXT,
            exam_date TEXT,
            official_link TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_vacancy(
    title,
    organization,
    category="",
    description="",
    eligibility="",
    application_start="",
    application_end="",
    exam_date="",
    official_link="",
):
    if not title or not organization or not official_link:
        raise ValueError("title, organization and official_link are required")

    now = datetime.now(timezone.utc).isoformat()

    conn = _connect()
    cur = conn.execute("""
        INSERT INTO vacancies (
            title, organization, category, description, eligibility,
            application_start, application_end, exam_date, official_link,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title, organization, category, description, eligibility,
        application_start, application_end, exam_date, official_link,
        now, now
    ))
    vacancy_id = cur.lastrowid
    conn.commit()
    conn.close()
    return vacancy_id


def get_vacancy(vacancy_id):
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM vacancies WHERE id = ?",
        (vacancy_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    columns = [
        "id", "title", "organization", "category", "description",
        "eligibility", "application_start", "application_end",
        "exam_date", "official_link", "created_at", "updated_at"
    ]
    return dict(zip(columns, row))


def list_vacancies():
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM vacancies ORDER BY id DESC"
    ).fetchall()
    conn.close()

    columns = [
        "id", "title", "organization", "category", "description",
        "eligibility", "application_start", "application_end",
        "exam_date", "official_link", "created_at", "updated_at"
    ]
    return [dict(zip(columns, row)) for row in rows]
