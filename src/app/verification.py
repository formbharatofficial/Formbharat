"""
FormBharat field-level verification foundation.

Compares saved Profile data with extracted Document data.
Does not guess, overwrite Profile data, or mark data verified globally.
"""

from app.profile import DB_PATH, PROFILE_FIELDS


def _normalize(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def verify_fields(profile_data, document_data):
    """
    Compare every Profile field that is explicitly present in extracted
    Document data.

    Status:
      verified      -> both values exist and match
      needs_review  -> both values exist but do not match
      unavailable   -> Document does not provide the field

    The document is treated as a data source; this function never guesses.
    """
    if not isinstance(profile_data, dict):
        raise ValueError("profile_data must be a dictionary")

    if not isinstance(document_data, dict):
        raise ValueError("document_data must be a dictionary")

    results = {}

    for field in PROFILE_FIELDS:
        profile_value = profile_data.get(field, "")
        document_value = document_data.get(field, "")

        normalized_profile = _normalize(profile_value)
        normalized_document = _normalize(document_value)

        if not normalized_document:
            status = "unavailable"
        elif normalized_profile and normalized_profile == normalized_document:
            status = "verified"
        elif normalized_profile and normalized_document:
            status = "needs_review"
        else:
            status = "needs_review"

        results[field] = {
            "profile_value": profile_value,
            "document_value": document_value,
            "source": "document",
            "status": status,
        }

    return results


def verify_profile_documents(profile_data, profile_id, db_path):
    """
    Verify a selected Profile against its own Document Vault data.

    Returns document-level and field-level verification results.
    Documents from other profiles are never considered.
    """
    import json
    import sqlite3

    if not isinstance(profile_data, dict):
        raise ValueError("profile_data must be a dictionary")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT id, doc_type, document_reference, extracted_data, verified
            FROM documents
            WHERE profile_id = ?
            ORDER BY id DESC
            """,
            (profile_id,),
        ).fetchall()
    finally:
        conn.close()

    documents = []

    for row in rows:
        try:
            extracted_data = json.loads(row["extracted_data"] or "{}")
        except (TypeError, json.JSONDecodeError):
            extracted_data = {}

        documents.append({
            "document_id": row["id"],
            "doc_type": row["doc_type"],
            "document_reference": row["document_reference"],
            "document_verified": bool(row["verified"]),
            "fields": verify_fields(profile_data, extracted_data),
        })

    return {
        "profile_id": profile_id,
        "document_count": len(documents),
        "documents": documents,
    }


def verified_data_from_results(results):
    """
    Select only field values that have been explicitly verified.

    Fields needing review or unavailable fields are never promoted.
    """
    if not isinstance(results, dict):
        raise ValueError("verification results must be a dictionary")

    verified = {}

    for field, result in results.items():
        if not isinstance(result, dict):
            continue

        if result.get("status") != "verified":
            continue

        value = result.get("document_value", "")
        if _normalize(value):
            verified[field] = str(value).strip()

    return verified


def can_promote_verified_profile(results):
    """
    Return True only when there are no unresolved field mismatches.

    Unavailable fields are not treated as mismatches.
    Any needs_review field blocks promotion.
    Unknown statuses also block promotion.
    """
    if not isinstance(results, dict):
        raise ValueError("verification results must be a dictionary")

    allowed_statuses = {"verified", "unavailable"}
    has_verified_field = False

    for result in results.values():
        if not isinstance(result, dict):
            return False

        status = result.get("status")

        if status not in allowed_statuses:
            return False

        if status == "verified":
            has_verified_field = True

    return has_verified_field


def combined_field_results(documents):
    """
    Merge per-document field results for promotion.

    Documents with document_verified == False never contribute field data.
    Any needs_review status for a field blocks that field.
    A field is verified only when at least one verified document verified it
    and no contributing document marked it needs_review.
    """
    if not isinstance(documents, list):
        raise ValueError("documents must be a list")

    combined = {}

    for document in documents:
        if not isinstance(document, dict):
            continue

        if "document_verified" in document and not document["document_verified"]:
            continue

        fields = document.get("fields")
        if not isinstance(fields, dict):
            continue

        for field, result in fields.items():
            if not isinstance(result, dict):
                combined[field] = {"status": "needs_review"}
                continue

            existing = combined.get(field)
            if existing is None:
                combined[field] = dict(result)
                continue

            existing_status = existing.get("status")
            new_status = result.get("status")

            if existing_status == "needs_review":
                continue

            if new_status == "needs_review":
                combined[field] = dict(result)
            elif existing_status != "verified" and new_status == "verified":
                combined[field] = dict(result)

    return combined
