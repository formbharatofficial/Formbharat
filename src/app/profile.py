import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "formbharat.db"
MAX_PROFILES = 5

PROFILE_FIELDS = (
    "name", "email", "mobile", "dob", "address", "country",
    "father_name", "mother_name",
    "gender", "nationality", "category", "state", "district", "pincode",
    "tenth_roll_number", "tenth_passing_year", "tenth_marks", "tenth_percentage",
    "twelfth_roll_number", "twelfth_passing_year", "twelfth_marks", "twelfth_percentage",
    "graduation_degree", "graduation_roll_number", "graduation_passing_year",
    "graduation_marks", "graduation_percentage",
    "post_graduation_degree", "post_graduation_roll_number", "post_graduation_passing_year", "post_graduation_marks", "post_graduation_percentage",
    "diploma_name", "diploma_roll_number", "diploma_passing_year", "diploma_marks", "diploma_percentage",
    "other_qualification",
)
BASE_PROFILE_FIELDS = PROFILE_FIELDS[:6]
OPTIONAL_PROFILE_FIELDS = PROFILE_FIELDS[6:]
PROFILE_DEFAULTS = {
    "name": "", "email": "", "mobile": "", "dob": "", "address": "",
    "country": "in", "father_name": "", "mother_name": "",
    "gender": "", "nationality": "", "category": "", "state": "",
    "district": "", "pincode": "",
    "tenth_roll_number": "", "tenth_passing_year": "", "tenth_marks": "",
    "tenth_percentage": "",
    "twelfth_roll_number": "", "twelfth_passing_year": "", "twelfth_marks": "",
    "twelfth_percentage": "",
    "graduation_degree": "", "graduation_roll_number": "",
    "graduation_passing_year": "", "graduation_marks": "",
    "graduation_percentage": "",
    "post_graduation_degree": "", "post_graduation_roll_number": "",
    "post_graduation_passing_year": "", "post_graduation_marks": "",
    "post_graduation_percentage": "",
    "diploma_name": "", "diploma_roll_number": "",
    "diploma_passing_year": "", "diploma_marks": "",
    "diploma_percentage": "", "other_qualification": "",
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
            mother_name TEXT NOT NULL DEFAULT '',
            gender TEXT NOT NULL DEFAULT '',
            nationality TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT '',
            district TEXT NOT NULL DEFAULT '',
            pincode TEXT NOT NULL DEFAULT '',
            tenth_roll_number TEXT NOT NULL DEFAULT '',
            tenth_passing_year TEXT NOT NULL DEFAULT '',
            tenth_marks TEXT NOT NULL DEFAULT '',
            tenth_percentage TEXT NOT NULL DEFAULT '',
            twelfth_roll_number TEXT NOT NULL DEFAULT '',
            twelfth_passing_year TEXT NOT NULL DEFAULT '',
            twelfth_marks TEXT NOT NULL DEFAULT '',
            twelfth_percentage TEXT NOT NULL DEFAULT '',
            graduation_degree TEXT NOT NULL DEFAULT '',
            graduation_roll_number TEXT NOT NULL DEFAULT '',
            graduation_passing_year TEXT NOT NULL DEFAULT '',
            graduation_marks TEXT NOT NULL DEFAULT '',
            graduation_percentage TEXT NOT NULL DEFAULT '',
            post_graduation_degree TEXT NOT NULL DEFAULT '',
            post_graduation_roll_number TEXT NOT NULL DEFAULT '',
            post_graduation_passing_year TEXT NOT NULL DEFAULT '',
            post_graduation_marks TEXT NOT NULL DEFAULT '',
            post_graduation_percentage TEXT NOT NULL DEFAULT '',
            diploma_name TEXT NOT NULL DEFAULT '',
            diploma_roll_number TEXT NOT NULL DEFAULT '',
            diploma_passing_year TEXT NOT NULL DEFAULT '',
            diploma_marks TEXT NOT NULL DEFAULT '',
            diploma_percentage TEXT NOT NULL DEFAULT '',
            other_qualification TEXT NOT NULL DEFAULT ''
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
        existing = conn.execute(
            f"SELECT {', '.join(columns[1:])} FROM profile WHERE id = ?",
            (profile_id,),
        ).fetchone()
        if existing is None:
            changed = _first_save_disagrees_with_verified(
                conn, profile_id, values
            )
        else:
            changed = any(
                str(existing[index] or "") != values[field]
                for index, field in enumerate(columns[1:])
            )

        conn.execute(
            f"""
            INSERT INTO profile ({column_list})
            VALUES ({placeholders})
            ON CONFLICT(id) DO UPDATE SET {updates}
            """,
            [profile_id, *(values[field] for field in columns[1:])],
        )
        if changed and _verified_profile_table_exists(conn):
            conn.execute(
                "UPDATE verified_profile SET verified = 0 WHERE profile_id = ?",
                (profile_id,),
            )
        conn.commit()
    finally:
        conn.close()


def _first_save_disagrees_with_verified(conn, profile_id, values):
    if not _verified_profile_table_exists(conn):
        return False
    row = conn.execute(
        "SELECT data, verified FROM verified_profile WHERE profile_id = ?",
        (profile_id,),
    ).fetchone()
    if row is None or row[1] != 1:
        return False
    try:
        stored = json.loads(row[0] or "{}")
    except (TypeError, json.JSONDecodeError):
        return True
    if not isinstance(stored, dict):
        return True
    return any(
        str(stored.get(field, "") or "").strip() != new_value
        for field, new_value in values.items()
    )


def _verified_profile_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='verified_profile'"
    ).fetchone()
    return row is not None


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
