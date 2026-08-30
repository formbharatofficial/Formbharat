import os
import sqlite3
import hashlib
import json
import re
import uuid
from datetime import datetime
from flask import request, jsonify, send_file
from app.document_ocr import extract_text
from app.profile import profile_exists

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(BASE_DIR, "formbharat.db")
STORAGE_DIR = os.path.join(BASE_DIR, "documents")

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _documents_table_sql():
    return """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER,
            doc_type TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            mime_type TEXT,
            file_hash TEXT,
            extracted_text TEXT,
            extracted_data TEXT,
            verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            document_version INTEGER NOT NULL DEFAULT 1,
            document_reference TEXT NOT NULL
        )
    """


def _generate_document_reference(conn):
    while True:
        reference = f"DOC-{uuid.uuid4().hex.upper()}"
        existing = conn.execute(
            "SELECT 1 FROM documents WHERE document_reference = ?",
            (reference,)
        ).fetchone()
        if existing is None:
            return reference


def init_db():
    """Create the existing Document Vault schema when it is not present."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(_documents_table_sql())
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(documents)")
        }
        if "document_version" not in columns:
            conn.execute(
                "ALTER TABLE documents "
                "ADD COLUMN document_version INTEGER NOT NULL DEFAULT 1"
            )
        if "document_reference" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN document_reference TEXT"
            )

        rows = conn.execute(
            "SELECT id, document_reference FROM documents ORDER BY id"
        ).fetchall()
        seen_references = set()
        for document_id, document_reference in rows:
            if document_reference and document_reference not in seen_references:
                seen_references.add(document_reference)
                continue

            document_reference = _generate_document_reference(conn)
            conn.execute(
                "UPDATE documents SET document_reference = ? WHERE id = ?",
                (document_reference, document_id)
            )
            seen_references.add(document_reference)

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_documents_document_reference
            ON documents(document_reference)
            """
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )



def build_extracted_data(extracted_text):
    """
    Convert OCR text into basic structured JSON.
    Keep raw OCR text so no information is lost.
    """
    data = {
        "name": "",
        "father_name": "",
        "dob": "",
        "class": "",
        "raw_text": extracted_text or ""
    }

    text = extracted_text or ""

    patterns = {
        "name": r"(?im)^\s*(?:name|kame)\s*[:\-]\s*(.+)$",
        "father_name": r"(?im)^\s*(?:father\s*name|father)\s*[:\-]\s*(.+)$",
        "dob": r"(?im)^\s*(?:dob|date\s*of\s*birth)\s*[:\-]\s*(.+)$",
        "class": r"(?im)^\s*class\s*[:\-]\s*(.+)$"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            data[key] = match.group(1).strip()

    return data


def register_document_vault(app):

    init_db()
    os.makedirs(STORAGE_DIR, exist_ok=True)

    @app.route("/api/documents/upload", methods=["POST"])
    def upload_document():
        try:
            profile_id = request.form.get("profile_id")
            doc_type = request.form.get("doc_type", "").strip()

            if not profile_id:
                return jsonify({
                    "success": False,
                    "error": "profile_id is required"
                }), 400

            try:
                profile_id = int(profile_id)
                if not profile_exists(profile_id):
                    raise ValueError
            except (TypeError, ValueError):
                return jsonify({
                    "success": False,
                    "error": "profile_id must refer to an existing valid profile"
                }), 400

            if not doc_type:
                return jsonify({
                    "success": False,
                    "error": "doc_type is required"
                }), 400

            if "file" not in request.files:
                return jsonify({
                    "success": False,
                    "error": "file is required"
                }), 400

            file = request.files["file"]

            if not file.filename:
                return jsonify({
                    "success": False,
                    "error": "filename is required"
                }), 400

            if not allowed_file(file.filename):
                return jsonify({
                    "success": False,
                    "error": "Only PDF, JPG, JPEG and PNG are allowed"
                }), 400

            data = file.read()

            if len(data) > MAX_FILE_SIZE:
                return jsonify({
                    "success": False,
                    "error": "Maximum file size is 10 MB"
                }), 400

            file_hash = hashlib.sha256(data).hexdigest()

            ext = file.filename.rsplit(".", 1)[1].lower()
            safe_name = f"{file_hash}.{ext}"

            profile_dir = os.path.join(STORAGE_DIR, str(profile_id))
            os.makedirs(profile_dir, exist_ok=True)

            storage_path = os.path.join(profile_dir, safe_name)

            with open(storage_path, "wb") as f:
                f.write(data)

            # OCR / text extraction
            extracted_text = ""
            try:
                extracted_text = extract_text(storage_path)
            except Exception as ocr_error:
                print("OCR WARNING:", ocr_error)
                extracted_text = ""

            now = datetime.utcnow().isoformat()

            conn = get_db()

            existing = conn.execute(
                """
                SELECT id, document_reference FROM documents
                WHERE profile_id = ? AND file_hash = ?
                """,
                (profile_id, file_hash)
            ).fetchone()

            if existing:
                conn.close()
                os.remove(storage_path)

                return jsonify({
                    "success": True,
                    "message": "Document already exists",
                    "document_id": existing["id"],
                    "document_reference": existing["document_reference"]
                })

            version_row = conn.execute(
                """
                SELECT COALESCE(MAX(document_version), 0) AS latest_version
                FROM documents
                WHERE profile_id = ? AND doc_type = ?
                """,
                (profile_id, doc_type)
            ).fetchone()
            document_version = version_row["latest_version"] + 1
            document_reference = _generate_document_reference(conn)

            cursor = conn.execute(
                """
                INSERT INTO documents
                (
                    profile_id,
                    doc_type,
                    original_filename,
                    storage_path,
                    mime_type,
                    file_hash,
                    extracted_text,
                    extracted_data,
                    verified,
                    created_at,
                    updated_at,
                    document_version,
                    document_reference
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    doc_type,
                    file.filename,
                    storage_path,
                    file.mimetype or "",
                    file_hash,
                    extracted_text,
                    json.dumps(build_extracted_data(extracted_text), ensure_ascii=False),
                    0,
                    now,
                    now,
                    document_version,
                    document_reference
                )
            )

            conn.commit()
            document_id = cursor.lastrowid
            conn.close()

            return jsonify({
                "success": True,
                "message": "Document uploaded successfully",
                "document_id": document_id,
                "filename": file.filename,
                "doc_type": doc_type,
                "document_version": document_version,
                "document_reference": document_reference
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500


    @app.route("/api/documents/<int:profile_id>", methods=["GET"])
    def list_documents(profile_id):
        try:
            conn = get_db()

            rows = conn.execute(
                """
                SELECT
                    id,
                    profile_id,
                    doc_type,
                    original_filename,
                    mime_type,
                    file_hash,
                    extracted_text,
                    extracted_data,
                    verified,
                    created_at,
                    updated_at,
                    document_version,
                    document_reference
                FROM documents
                WHERE profile_id = ?
                ORDER BY id DESC
                """,
                (profile_id,)
            ).fetchall()

            conn.close()

            return jsonify({
                "success": True,
                "count": len(rows),
                "documents": [dict(row) for row in rows]
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500


    @app.route("/api/documents/file/<int:document_id>", methods=["GET"])
    def download_document(document_id):
        try:
            conn = get_db()

            row = conn.execute(
                """
                SELECT storage_path, original_filename
                FROM documents
                WHERE id = ?
                """,
                (document_id,)
            ).fetchone()

            conn.close()

            if not row:
                return jsonify({
                    "success": False,
                    "error": "Document not found"
                }), 404

            if not os.path.exists(row["storage_path"]):
                return jsonify({
                    "success": False,
                    "error": "Stored file not found"
                }), 404

            return send_file(
                row["storage_path"],
                as_attachment=False,
                download_name=row["original_filename"]
            )

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500


    @app.route("/api/documents/<int:document_id>", methods=["DELETE"])
    def delete_document(document_id):
        try:
            conn = get_db()

            row = conn.execute(
                """
                SELECT storage_path
                FROM documents
                WHERE id = ?
                """,
                (document_id,)
            ).fetchone()

            if not row:
                conn.close()
                return jsonify({
                    "success": False,
                    "error": "Document not found"
                }), 404

            if os.path.exists(row["storage_path"]):
                os.remove(row["storage_path"])

            conn.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,)
            )

            conn.commit()
            conn.close()

            return jsonify({
                "success": True,
                "message": "Document deleted successfully"
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500


    print("Document Vault registered successfully.")
