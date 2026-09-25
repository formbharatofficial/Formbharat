import sqlite3
from pathlib import Path
from datetime import date, datetime, timezone

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
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(vacancies)")
    }
    if "source_name" not in columns:
        conn.execute(
            "ALTER TABLE vacancies ADD COLUMN source_name TEXT NOT NULL DEFAULT ''"
        )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vacancy_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            vacancy_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(profile_id, vacancy_id, alert_type)
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
    source_name="",
):
    if not title or not organization or not official_link:
        raise ValueError("title, organization and official_link are required")

    _require_official_link(official_link)
    _status_for(application_start, application_end)

    now = datetime.now(timezone.utc).isoformat()

    conn = _connect()
    cur = conn.execute("""
        INSERT INTO vacancies (
            title, organization, category, description, eligibility,
            application_start, application_end, exam_date, official_link,
            created_at, updated_at, source_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title, organization, category, description, eligibility,
        application_start, application_end, exam_date, official_link,
        now, now, source_name or ""
    ))
    vacancy_id = cur.lastrowid
    conn.commit()
    conn.close()
    return vacancy_id


def _require_official_link(official_link):
    lowered = official_link.lower()
    if not (lowered.startswith("https://") or lowered.startswith("http://")):
        raise ValueError("official_link must be an http or https URL")
    host = official_link.split("://", 1)[1].strip().split("/", 1)[0]
    if not host:
        raise ValueError("official_link must include a host")


def _status_for(application_start, application_end, today=None):
    today = today or datetime.now(timezone.utc).date()

    def _parse(value):
        if not value:
            return None
        return date.fromisoformat(str(value)[:10])

    start = _parse(application_start)
    end = _parse(application_end)
    if start and end and end < start:
        raise ValueError("application_end cannot be before application_start")
    if start and start > today:
        return "upcoming"
    if end and end < today:
        return "closed"
    if start or end:
        return "open"
    return "listed"


def _with_status(item):
    item["status"] = _status_for(
        item.get("application_start", ""),
        item.get("application_end", ""),
    )
    return item


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
        "exam_date", "official_link", "created_at", "updated_at",
        "source_name",
    ]
    return _with_status(dict(zip(columns, row)))


def list_vacancies(category=None, status=None):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM vacancies ORDER BY id DESC"
    ).fetchall()
    conn.close()

    columns = [
        "id", "title", "organization", "category", "description",
        "eligibility", "application_start", "application_end",
        "exam_date", "official_link", "created_at", "updated_at",
        "source_name",
    ]
    items = [_with_status(dict(zip(columns, row))) for row in rows]
    if category:
        wanted = category.strip().lower()
        items = [
            item for item in items
            if str(item.get("category", "")).strip().lower() == wanted
        ]
    if status:
        wanted_status = status.strip().lower()
        items = [
            item for item in items
            if item.get("status") == wanted_status
        ]
    return items


def update_vacancy(vacancy_id, **fields):
    current = get_vacancy(vacancy_id)
    if current is None:
        return None

    allowed = {
        "title", "organization", "category", "description", "eligibility",
        "application_start", "application_end", "exam_date", "official_link",
        "source_name",
    }
    changes = {
        key: str(value).strip()
        for key, value in fields.items()
        if key in allowed and value is not None
    }
    if not changes:
        return current

    merged = dict(current)
    merged.update(changes)
    if not merged["title"] or not merged["organization"] or not merged["official_link"]:
        raise ValueError("title, organization and official_link are required")
    _require_official_link(merged["official_link"])
    _status_for(merged["application_start"], merged["application_end"])

    assignments = ", ".join(f"{key} = ?" for key in changes)
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    conn.execute(
        f"UPDATE vacancies SET {assignments}, updated_at = ? WHERE id = ?",
        [*(changes[key] for key in changes), now, vacancy_id],
    )
    conn.commit()
    conn.close()
    return get_vacancy(vacancy_id)


def delete_vacancy(vacancy_id):
    conn = _connect()
    try:
        cursor = conn.execute(
            "DELETE FROM vacancies WHERE id = ?",
            (vacancy_id,),
        )
        conn.execute(
            "DELETE FROM vacancy_alerts WHERE vacancy_id = ?",
            (vacancy_id,),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def discover_vacancies(source):
    """Collect vacancy records from a caller-supplied source adapter.

    The adapter's discover() method returns records the caller already has.
    This function does not fetch websites or invent official notices.
    """
    discover = getattr(source, "discover", None)
    if not callable(discover):
        raise ValueError("vacancy source must provide discover()")
    found = discover()
    if not isinstance(found, list):
        raise ValueError("discover() must return a list")
    return [import_vacancy_record(record) for record in found]


def import_vacancy_record(record):
    """Import one locally supplied vacancy record.

    This does not fetch or verify an official website.
    """
    if not isinstance(record, dict):
        raise ValueError("vacancy record must be a dictionary")

    return create_vacancy(
        title=str(record.get("title", "")).strip(),
        organization=str(record.get("organization", "")).strip(),
        category=str(record.get("category", "")).strip(),
        description=str(record.get("description", "")).strip(),
        eligibility=str(record.get("eligibility", "")).strip(),
        application_start=str(record.get("application_start", "")).strip(),
        application_end=str(record.get("application_end", "")).strip(),
        exam_date=str(record.get("exam_date", "")).strip(),
        official_link=str(record.get("official_link", "")).strip(),
        source_name=str(record.get("source_name", "")).strip(),
    )


def create_vacancy_alert(profile_id, vacancy_id, alert_type="deadline"):
    if get_vacancy(vacancy_id) is None:
        raise ValueError("Vacancy not found")
    if alert_type != "deadline":
        raise ValueError("alert_type must be deadline")

    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO vacancy_alerts
                (profile_id, vacancy_id, alert_type, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(profile_id, vacancy_id, alert_type) DO NOTHING
            """,
            (profile_id, vacancy_id, alert_type, now),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id, profile_id, vacancy_id, alert_type, created_at
            FROM vacancy_alerts
            WHERE profile_id = ? AND vacancy_id = ? AND alert_type = ?
            """,
            (profile_id, vacancy_id, alert_type),
        ).fetchone()
    finally:
        conn.close()
    return {
        "id": row[0],
        "profile_id": row[1],
        "vacancy_id": row[2],
        "alert_type": row[3],
        "created_at": row[4],
    }


def list_vacancy_alerts(profile_id):
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, profile_id, vacancy_id, alert_type, created_at
            FROM vacancy_alerts
            WHERE profile_id = ?
            ORDER BY id DESC
            """,
            (profile_id,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": row[0],
            "profile_id": row[1],
            "vacancy_id": row[2],
            "alert_type": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]
