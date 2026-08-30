import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "formbharat.db"
MAX_PROFILES = 5

PROFILE_FIELDS = (
    "name", "email", "mobile", "dob", "address", "country",
    "father_name", "mother_name",
)
BASE_PROFILE_FIELDS = PROFILE_FIELDS[:6]
OPTIONAL_PROFILE_FIELDS = PROFILE_FIELDS[6:]
PROFILE_DEFAULTS = {
    "name": "", "email": "", "mobile": "", "dob": "", "address": "",
    "country": "in", "father_name": "", "mother_name": "",
}


def _validate_profile_id(profile_id):
    if (
        isinstance(profile_id, bool)
        or not isinstance(profile_id, int)
        or not 1 <= profile_id <= MAX_PROFILES
    ):
        raise ValueError(
            f"profile_id must be an integer between 1 and {MAX_PROFILES}"
        )


def _profile_table_sql(table_name="profile"):
    return f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY CHECK (id BETWEEN 1 AND {MAX_PROFILES}),
            name TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            mobile TEXT NOT NULL DEFAULT '',
            dob TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT 'in',
            father_name TEXT NOT NULL DEFAULT '',
            mother_name TEXT NOT NULL DEFAULT ''
        )
    """


def _needs_migration(table_sql, columns):
    normalized_sql = " ".join((table_sql or "").lower().split())
    has_profile_limit = (
        f"check (id between 1 and {MAX_PROFILES})" in normalized_sql
    )
    return not has_profile_limit or not set(PROFILE_FIELDS).issubset(columns)


def _migrate_profile_table(conn, existing_columns):
    conn.execute(_profile_table_sql("profile_new"))

    copied_fields = [
        field for field in PROFILE_FIELDS if field in existing_columns
    ]
    columns = ["id", *copied_fields]
    column_list = ", ".join(columns)

    conn.execute(
        f"INSERT INTO profile_new ({column_list}) SELECT {column_list} FROM profile"
    )
    conn.execute("DROP TABLE profile")
    conn.execute("ALTER TABLE profile_new RENAME TO profile")


def init_db():
    conn = sqlite3.connect(DB_PATH)

    try:
        table = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'profile'"
        ).fetchone()

        if table is None:
            conn.execute(_profile_table_sql())
        else:
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(profile)")
            }
            if _needs_migration(table[0], columns):
                _migrate_profile_table(conn, columns)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_profile(data, profile_id=1):
    _validate_profile_id(profile_id)
    init_db()

    if not isinstance(data, dict):
        raise ValueError("profile data must be a dictionary")

    values = {
        field: str(data.get(field, PROFILE_DEFAULTS[field])).strip()
        for field in BASE_PROFILE_FIELDS
    }
    optional_fields = [
        field for field in OPTIONAL_PROFILE_FIELDS if field in data
    ]
    for field in optional_fields:
        values[field] = str(data[field] or "").strip()

    columns = ["id", *BASE_PROFILE_FIELDS, *optional_fields]
    column_list = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{field}=excluded.{field}" for field in columns if field != "id"
    )

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            f"""
            INSERT INTO profile ({column_list})
            VALUES ({placeholders})
            ON CONFLICT(id) DO UPDATE SET {updates}
            """,
            [profile_id, *(values[field] for field in columns[1:])],
        )
        conn.commit()
    finally:
        conn.close()


def get_profile(profile_id=1):
    _validate_profile_id(profile_id)
    init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    field_list = ", ".join(PROFILE_FIELDS)
    row = conn.execute(
        f"SELECT {field_list} FROM profile WHERE id = ?", (profile_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return dict(PROFILE_DEFAULTS)

    return dict(row)


def profile_exists(profile_id):
    """Return whether a valid profile has been saved."""
    _validate_profile_id(profile_id)
    init_db()

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT 1 FROM profile WHERE id = ?", (profile_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()
