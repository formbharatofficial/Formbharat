"""Profile-slot ownership.

A new account never receives an existing slot automatically. An unowned
slot remains available only while nobody is logged in. A logged-in account
can claim a slot only when that slot has no profile, document, or
application data, the claim is explicitly confirmed, and the server claim
code matches. The code is not stored in the repository.
"""

import os
import secrets
import sqlite3

from app.profile import (
    PROFILE_FIELDS,
    _validate_profile_id,
    init_db,
)


def _db_path():
    from app import profile
    return profile.DB_PATH


class SlotAccessError(PermissionError):
    """The current session cannot use this profile slot."""


def current_user_id():
    try:
        from flask import has_request_context, session
    except ImportError:
        return None
    if not has_request_context():
        return None
    user_id = session.get("user_id")
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        return None
    return user_id


def profile_owner(profile_id):
    _validate_profile_id(profile_id)
    init_db()
    connection = sqlite3.connect(_db_path())
    try:
        row = connection.execute(
            "SELECT owner_user_id FROM profile WHERE id = ?",
            (profile_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None or row[0] is None:
        return None
    return int(row[0])


def assert_slot_access(profile_id):
    _validate_profile_id(profile_id)
    owner = profile_owner(profile_id)
    user_id = current_user_id()
    if user_id is None:
        if owner is not None:
            raise SlotAccessError("This profile slot belongs to an account.")
        return
    if owner != user_id:
        raise SlotAccessError(
            "This profile slot is not available to this account."
        )


def guard_response(profile_id):
    from flask import jsonify

    try:
        assert_slot_access(profile_id)
    except SlotAccessError as error:
        return jsonify({"success": False, "error": str(error)}), 403
    return None


def _rows_for_profile(db_path, table, profile_id):
    if not db_path or not os.path.exists(db_path):
        return False
    connection = sqlite3.connect(db_path)
    try:
        found = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        if found is None:
            return False
        columns = {
            row[1] for row in connection.execute(f"PRAGMA table_info({table})")
        }
        if "profile_id" not in columns:
            return False
        row = connection.execute(
            f"SELECT 1 FROM {table} WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        return row is not None
    finally:
        connection.close()


def slot_has_private_data(profile_id):
    """True when a slot already holds profile, document, or application data."""
    _validate_profile_id(profile_id)
    init_db()
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            f"SELECT {', '.join(PROFILE_FIELDS)} FROM profile WHERE id = ?",
            (profile_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is not None:
        for field in PROFILE_FIELDS:
            value = str(row[field] or "").strip()
            if field == "country" and value in {"", "in"}:
                continue
            if value:
                return True
    from app.application_tracker import DB_PATH as application_db
    from app.document_vault import DB_PATH as document_db

    return (
        _rows_for_profile(document_db, "documents", profile_id)
        or _rows_for_profile(application_db, "applications", profile_id)
    )


def claim_status(profile_id):
    """Return a status word only. Slot contents are not included."""
    _validate_profile_id(profile_id)
    if profile_owner(profile_id) is not None:
        return "owned"
    if slot_has_private_data(profile_id):
        return "legacy_locked"
    return "empty"


def claim_empty_slot(profile_id, claim_code, confirm):
    _validate_profile_id(profile_id)
    user_id = current_user_id()
    if user_id is None:
        raise SlotAccessError("Login is required before a slot can be claimed.")
    if confirm is not True:
        raise SlotAccessError("Claim must be explicitly confirmed.")
    expected = os.environ.get("FORMBHARAT_SLOT_CLAIM_CODE", "").strip()
    supplied = "" if claim_code is None else str(claim_code)
    if not expected:
        raise SlotAccessError("Slot claim is not available.")
    if len(supplied) != len(expected) or not secrets.compare_digest(supplied, expected):
        raise SlotAccessError("Slot claim was rejected.")
    if profile_owner(profile_id) is not None:
        raise SlotAccessError("This profile slot is not available to this account.")
    if slot_has_private_data(profile_id):
        raise SlotAccessError("Legacy profile data cannot be claimed.")

    init_db()
    connection = sqlite3.connect(_db_path())
    try:
        connection.execute(
            """
            INSERT INTO profile (id, owner_user_id)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET owner_user_id = excluded.owner_user_id
            """,
            (profile_id, user_id),
        )
        connection.commit()
    finally:
        connection.close()
    return {"profile_id": profile_id, "claimed": True}
