"""PAN and Aadhaar already read on this laptop, for filling only.

The verified profile row is not changed.
"""

import json
import os
import sqlite3


def saved_identity_numbers(profile_id):
    """Return pan_number and aadhaar_number when a saved document already has them."""
    from app import document_vault
    from app.document_encryption import reveal_text

    if isinstance(profile_id, bool) or not isinstance(profile_id, int):
        return {}
    if not os.path.exists(document_vault.DB_PATH):
        return {}
    try:
        connection = sqlite3.connect(document_vault.DB_PATH)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                SELECT extracted_data
                FROM documents
                WHERE profile_id = ?
                ORDER BY id
                """,
                (profile_id,),
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error:
        return {}

    found = {}
    for row in rows:
        raw = reveal_text(row["extracted_data"])
        try:
            data = json.loads(raw) if str(raw or "").strip() else {}
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        for key in ("pan_number", "aadhaar_number"):
            value = str(data.get(key) or "").strip()
            if value:
                found[key] = value
    return found


def with_saved_identity(profile, profile_id):
    """Copy profile and add saved PAN or Aadhaar numbers when the copy has none."""
    merged = dict(profile) if isinstance(profile, dict) else {}
    for key, value in saved_identity_numbers(profile_id).items():
        if not str(merged.get(key) or "").strip():
            merged[key] = value
    return merged
