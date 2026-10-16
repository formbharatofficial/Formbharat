"""Choose a saved document for an ordinary file field.

Password, OTP, CAPTCHA, payment, capture/crop controls, and final submit
stay with the user. The original stored file is not changed.
"""

import os
import re
import sqlite3
from pathlib import Path

from app.document_fit import fit_image_copy


_WORDS = re.compile(r"[^a-z0-9]+")
_DOC_WORDS = {
    "photo": {"photo", "photograph"},
    "signature": {"signature", "sign"},
    "aadhaar": {"aadhaar", "aadhar"},
    "pan": {"pan"},
    "10th": {"10th", "tenth", "matric"},
    "12th": {"12th", "twelfth"},
    "graduation": {"graduation", "degree"},
    "identity": {"identity"},
    "domicile": {"domicile"},
    "income": {"income"},
    "category": {"category", "caste"},
}
_BLOCKED = {"otp", "captcha", "password", "payment", "fee", "fees", "payable", "upi", "cvv"}


def _tokens(*parts):
    tokens = []
    for part in parts:
        tokens.extend(token for token in _WORDS.split(str(part or "").lower()) if token)
    return tokens


def _blocked_text(*parts):
    tokens = set(_tokens(*parts))
    compact = "".join(_tokens(*parts))
    if tokens & _BLOCKED:
        return True
    return "cardnumber" in compact or "debitcard" in compact or "creditcard" in compact


def _accepts(accept, kind):
    text = str(accept or "").strip().lower()
    if not text:
        return True
    tokens = [part.strip() for part in text.split(",") if part.strip()]
    if kind == "jpeg":
        return any(
            token in {".jpg", ".jpeg", "image/jpg", "image/jpeg", "image/*"}
            for token in tokens
        )
    if kind == "pdf":
        return any("pdf" in token for token in tokens)
    return False


def _limit_for(field, default):
    raw = field.get("max_bytes")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return default


def _doc_type_for_field(field):
    tokens = set(_tokens(
        field.get("label"),
        field.get("name"),
        field.get("id"),
        field.get("placeholder"),
    ))
    for doc_type, words in _DOC_WORDS.items():
        if tokens & words:
            return doc_type
    return None


def saved_documents(profile_id):
    """Read one profile slot's saved files. Missing vault data returns nothing."""
    from app import document_vault
    from app.document_encryption import DocumentStorageError, read_bytes

    if not os.path.exists(document_vault.DB_PATH):
        return []
    connection = sqlite3.connect(document_vault.DB_PATH)
    try:
        try:
            rows = connection.execute(
                """
                SELECT id, doc_type, original_filename, storage_path
                FROM documents
                WHERE profile_id = ?
                ORDER BY id
                """,
                (profile_id,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    finally:
        connection.close()

    items = []
    for document_id, doc_type, filename, storage_path in rows:
        stored = document_vault._path_inside_storage(storage_path)
        if stored is None:
            continue
        try:
            data = read_bytes(stored)
        except (DocumentStorageError, OSError):
            continue
        items.append({
            "id": document_id,
            "doc_type": str(doc_type or "").strip().lower(),
            "filename": filename,
            "data": data,
        })
    return items


def plan_attachments(fields, documents, destination_dir, max_bytes=300 * 1024):
    """Prepare copies for ordinary file inputs. Capture controls stay with the user."""
    if not isinstance(fields, list):
        raise ValueError("fields must be a list")
    if not isinstance(documents, list):
        raise ValueError("documents must be a list")
    directory = Path(destination_dir)
    directory.mkdir(parents=True, exist_ok=True)
    planned = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        if str(field.get("type") or "").lower() != "file":
            continue
        label_parts = (
            field.get("label"),
            field.get("name"),
            field.get("id"),
            field.get("placeholder"),
        )
        item = {
            "field": field.get("name") or field.get("id"),
            "id": field.get("id") or "",
            "name": field.get("name") or "",
            "doc_type": None,
            "filename": "",
            "status": "missing",
            "reason": "no saved document matches this file field",
            "bytes": 0,
        }
        if _blocked_text(*label_parts) or str(field.get("capture") or "").strip():
            item["status"] = "needs_user"
            item["reason"] = "site asks the user to choose this file"
            planned.append(item)
            continue
        doc_type = _doc_type_for_field(field)
        item["doc_type"] = doc_type
        if doc_type is None:
            planned.append(item)
            continue
        matches = [doc for doc in documents if doc.get("doc_type") == doc_type]
        if not matches:
            planned.append(item)
            continue
        chosen = matches[-1]
        data = chosen.get("data") or b""
        item["filename"] = chosen.get("filename") or ""
        suffix = Path(str(chosen.get("filename") or "")).suffix.lower()
        target = directory / f"{len(planned)}-{doc_type}"
        limit = _limit_for(field, max_bytes)
        if data[:8].startswith(b"\x89PNG\r\n\x1a\n") or data[:3] == b"\xff\xd8\xff" or suffix in {".png", ".jpg", ".jpeg"}:
            if not _accepts(field.get("accept"), "jpeg"):
                item["status"] = "needs_user"
                item["reason"] = "this field does not accept the prepared file type"
                planned.append(item)
                continue
            output = target.with_suffix(".jpg")
            try:
                item["bytes"] = fit_image_copy(data, output, max_bytes=limit)
            except (OSError, ValueError):
                item["status"] = "needs_user"
                item["reason"] = "saved image could not be resized"
                planned.append(item)
                continue
            if item["bytes"] > limit:
                output.unlink(missing_ok=True)
                item["status"] = "needs_user"
                item["reason"] = "saved image is larger than this field allows"
                planned.append(item)
                continue
            item["status"] = "ready"
            item["reason"] = "resized copy is ready"
            item["path"] = str(output)
            item["filename"] = output.name
            planned.append(item)
            continue
        if data.startswith(b"%PDF") or suffix == ".pdf":
            if not _accepts(field.get("accept"), "pdf"):
                item["status"] = "needs_user"
                item["reason"] = "this field does not accept the prepared file type"
                planned.append(item)
                continue
            if len(data) > limit:
                item["status"] = "needs_user"
                item["reason"] = "saved PDF is larger than the upload limit"
                planned.append(item)
                continue
            output = target.with_suffix(".pdf")
            output.write_bytes(data)
            item["status"] = "ready"
            item["reason"] = "saved PDF copy is ready"
            item["bytes"] = len(data)
            item["path"] = str(output)
            item["filename"] = output.name
            planned.append(item)
            continue
        item["status"] = "needs_user"
        item["reason"] = "saved file is not a PDF or image the form can take"
        planned.append(item)
    return planned


def public_attachments(attachments):
    """Return attachment results without local file paths."""
    visible = []
    for item in attachments:
        if not isinstance(item, dict):
            continue
        visible.append({
            "field": item.get("field"),
            "doc_type": item.get("doc_type"),
            "filename": item.get("filename") or "",
            "status": item.get("status"),
            "reason": item.get("reason") or "",
            "bytes": item.get("bytes") or 0,
        })
    return visible
