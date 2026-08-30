import sqlite3
from io import BytesIO

from flask import Flask

from app import document_vault
from app import profile


def _table_columns(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {
            row[1] for row in conn.execute("PRAGMA table_info(documents)")
        }
    finally:
        conn.close()


def _document_client(monkeypatch, tmp_path, saved_profile_ids=()):
    db_path = tmp_path / "formbharat.db"
    monkeypatch.setattr(document_vault, "DB_PATH", str(db_path))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(profile, "DB_PATH", db_path)
    monkeypatch.setattr(document_vault, "extract_text", lambda _path: "")

    for profile_id in saved_profile_ids:
        profile.save_profile({"name": f"User {profile_id}"}, profile_id)

    app = Flask(__name__)
    app.config["TESTING"] = True
    document_vault.register_document_vault(app)
    return app.test_client()


def test_vault_registration_creates_documents_table_for_a_fresh_database(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "formbharat.db"
    monkeypatch.setattr(document_vault, "DB_PATH", str(db_path))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))

    document_vault.register_document_vault(Flask(__name__))

    assert _table_columns(db_path) == {
        "id",
        "profile_id",
        "doc_type",
        "original_filename",
        "storage_path",
        "mime_type",
        "file_hash",
        "extracted_text",
        "extracted_data",
        "verified",
        "created_at",
        "updated_at",
        "document_version",
        "document_reference",
    }


def test_init_db_preserves_a_compatible_existing_database(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "formbharat.db"
    monkeypatch.setattr(document_vault, "DB_PATH", str(db_path))
    document_vault.init_db()

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO documents (
            profile_id, doc_type, original_filename, storage_path,
            mime_type, file_hash, extracted_text, extracted_data,
            verified, created_at, updated_at, document_reference
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1, "identity", "aadhaar.png", "/tmp/aadhaar.png",
            "image/png", "hash", "OCR text", '{"name": "Asha"}',
            1, "2026-08-29T00:00:00", "2026-08-29T00:00:00",
            "DOC-COMPATIBLE",
        ),
    )
    conn.commit()
    conn.close()

    document_vault.init_db()

    conn = document_vault.get_db()
    try:
        row = conn.execute("SELECT * FROM documents").fetchone()
    finally:
        conn.close()

    assert row["profile_id"] == 1
    assert row["doc_type"] == "identity"
    assert row["original_filename"] == "aadhaar.png"
    assert row["extracted_data"] == '{"name": "Asha"}'
    assert row["verified"] == 1
    assert row["document_version"] == 1
    assert row["document_reference"] == "DOC-COMPATIBLE"


def test_init_db_adds_a_default_version_to_existing_documents(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "formbharat.db"
    monkeypatch.setattr(document_vault, "DB_PATH", str(db_path))

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE documents (
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
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO documents (
            profile_id, doc_type, original_filename, storage_path,
            created_at, updated_at
        ) VALUES (1, 'identity', 'existing.png', '/tmp/existing.png', 'then', 'now')
        """
    )
    conn.commit()
    conn.close()

    document_vault.init_db()

    conn = document_vault.get_db()
    try:
        row = conn.execute("SELECT * FROM documents").fetchone()
    finally:
        conn.close()

    assert row["original_filename"] == "existing.png"
    assert row["document_version"] == 1
    assert row["document_reference"].startswith("DOC-")


def test_document_metadata_can_be_stored_and_read(monkeypatch, tmp_path):
    db_path = tmp_path / "formbharat.db"
    monkeypatch.setattr(document_vault, "DB_PATH", str(db_path))
    document_vault.init_db()

    conn = document_vault.get_db()
    try:
        conn.execute(
            """
            INSERT INTO documents (
                profile_id, doc_type, original_filename, storage_path,
                mime_type, file_hash, extracted_text, extracted_data,
                verified, created_at, updated_at, document_reference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2, "education", "marksheet.pdf", "/tmp/marksheet.pdf",
                "application/pdf", "metadata-hash", "Extracted marks",
                '{"class": "10"}', 0,
                "2026-08-29T00:00:00", "2026-08-29T01:00:00",
                "DOC-METADATA",
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT profile_id, doc_type, original_filename, mime_type,
                   file_hash, extracted_text, extracted_data, verified,
                   created_at, updated_at, document_reference
            FROM documents WHERE file_hash = ?
            """,
            ("metadata-hash",),
        ).fetchone()
    finally:
        conn.close()

    assert dict(row) == {
        "profile_id": 2,
        "doc_type": "education",
        "original_filename": "marksheet.pdf",
        "mime_type": "application/pdf",
        "file_hash": "metadata-hash",
        "extracted_text": "Extracted marks",
        "extracted_data": '{"class": "10"}',
        "verified": 0,
        "created_at": "2026-08-29T00:00:00",
        "updated_at": "2026-08-29T01:00:00",
        "document_reference": "DOC-METADATA",
    }


def test_upload_links_document_to_an_existing_profile(monkeypatch, tmp_path):
    client = _document_client(monkeypatch, tmp_path, saved_profile_ids=(1,))

    response = client.post(
        "/api/documents/upload",
        data={
            "profile_id": "1",
            "doc_type": "identity",
            "file": (BytesIO(b"document content"), "identity.png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    uploaded = response.get_json()
    document_id = uploaded["document_id"]
    assert uploaded["document_version"] == 1
    assert uploaded["document_reference"].startswith("DOC-")
    assert uploaded["document_reference"] != str(document_id)
    listed = client.get("/api/documents/1").get_json()
    assert listed["count"] == 1
    assert listed["documents"][0]["id"] == document_id
    assert listed["documents"][0]["profile_id"] == 1
    assert listed["documents"][0]["document_version"] == 1
    assert listed["documents"][0]["document_reference"] == uploaded["document_reference"]


def test_uploading_a_replacement_preserves_the_previous_version(
    monkeypatch, tmp_path
):
    client = _document_client(monkeypatch, tmp_path, saved_profile_ids=(1,))

    first = client.post(
        "/api/documents/upload",
        data={
            "profile_id": "1",
            "doc_type": "identity",
            "file": (BytesIO(b"first document"), "identity-v1.png"),
        },
        content_type="multipart/form-data",
    ).get_json()
    second_response = client.post(
        "/api/documents/upload",
        data={
            "profile_id": "1",
            "doc_type": "identity",
            "file": (BytesIO(b"replacement document"), "identity-v2.png"),
        },
        content_type="multipart/form-data",
    )

    assert second_response.status_code == 200
    second = second_response.get_json()
    assert first["document_version"] == 1
    assert second["document_version"] == 2
    assert second["document_id"] != first["document_id"]
    assert first["document_reference"] != second["document_reference"]

    documents = client.get("/api/documents/1").get_json()["documents"]
    assert [document["document_version"] for document in documents] == [2, 1]
    assert documents[0]["original_filename"] == "identity-v2.png"
    assert documents[1]["original_filename"] == "identity-v1.png"
    assert documents[0]["file_hash"] != documents[1]["file_hash"]
    assert [document["document_reference"] for document in documents] == [
        second["document_reference"], first["document_reference"]
    ]


def test_upload_rejects_invalid_or_non_existing_profile_id(monkeypatch, tmp_path):
    client = _document_client(monkeypatch, tmp_path, saved_profile_ids=(1,))

    for profile_id in ("2", "6", "not-a-profile"):
        response = client.post(
            "/api/documents/upload",
            data={
                "profile_id": profile_id,
                "doc_type": "identity",
                "file": (BytesIO(b"document content"), "identity.png"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert response.get_json() == {
            "success": False,
            "error": "profile_id must refer to an existing valid profile",
        }
