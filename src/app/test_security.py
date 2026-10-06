import importlib.util
import sqlite3
from io import BytesIO
from pathlib import Path

from app import document_vault
from app import profile


HTML = "<form><input id='name' name='name' type='text'></form>"


def _load_main(module_name):
    spec = importlib.util.spec_from_file_location(
        module_name,
        Path(__file__).resolve().parents[1] / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded.app.config["TESTING"] = True
    return loaded


def _document_client(monkeypatch, tmp_path, saved_profile_ids=(1,)):
    db_path = tmp_path / "formbharat.db"
    monkeypatch.setattr(document_vault, "DB_PATH", str(db_path))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(profile, "DB_PATH", db_path)
    monkeypatch.setattr(document_vault, "extract_text", lambda _path: "")
    for profile_id in saved_profile_ids:
        profile.save_profile({"name": f"User {profile_id}"}, profile_id)
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True
    document_vault.register_document_vault(app)
    document_vault.register_document_vault_ui(app)
    return app.test_client()


_SIGNATURES = {
    "pdf": b"%PDF-",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
}


def _signed(filename, content):
    extension = filename.rsplit(".", 1)[-1].lower()
    signature = _SIGNATURES.get(extension, b"")
    if signature and not content.startswith(signature):
        return signature + content
    return content


def _upload(client, filename, content=b"document content", profile_id="1"):
    payload = _signed(filename, content)
    response = client.post(
        "/api/documents/upload",
        data={
            "profile_id": profile_id,
            "doc_type": "identity",
            "file": (BytesIO(payload), filename),
        },
        content_type="multipart/form-data",
    )
    response.payload = payload
    return response


def test_analyze_rejects_bool_and_float_profile_ids(monkeypatch, tmp_path):
    from app import document_vault as vault
    from app import verified_profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(profile, "DB_PATH", db)
    monkeypatch.setattr(vault, "DB_PATH", str(db))
    monkeypatch.setattr(vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(verified_profile, "DB_PATH", db)
    main = _load_main("formbharat_security_analyze")
    client = main.app.test_client()

    for profile_id in (True, False, 1.9):
        response = client.post(
            "/analyze",
            json={"html": HTML, "profile_id": profile_id},
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == (
            "profile_id must be an integer between 1 and 5"
        )

    accepted = client.post("/analyze", json={"html": HTML, "profile_id": 1})
    assert accepted.status_code == 200
    assert accepted.get_json()["success"] is True


def test_vacancy_alert_rejects_non_integer_profile_ids(monkeypatch, tmp_path):
    import app.vacancy as vacancy

    db = tmp_path / "vacancy.db"
    monkeypatch.setattr(vacancy, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)
    profile.save_profile({"name": "Alert User"}, 1)
    vacancy.init_vacancy_db()
    vacancy_id = vacancy.create_vacancy(
        title="Secure Post",
        organization="Org",
        official_link="https://example.gov.in/secure",
    )
    client = _load_main("formbharat_security_vacancy").app.test_client()

    for profile_id in (True, False, 1.9, "1"):
        response = client.post(
            f"/api/vacancies/{vacancy_id}/alerts",
            json={"profile_id": profile_id},
        )
        assert response.status_code == 400
        assert "profile_id" in response.get_json()["error"]

    created = client.post(
        f"/api/vacancies/{vacancy_id}/alerts",
        json={"profile_id": 1},
    )
    assert created.status_code == 201

    malformed = client.get("/api/vacancy-alerts/9")
    assert malformed.status_code == 400
    assert "profile_id" in malformed.get_json()["error"]
    isolated = client.get("/api/vacancy-alerts/2")
    assert isolated.status_code == 200
    assert isolated.get_json()["alerts"] == []


def test_application_api_rejects_non_integer_vacancy_ids(monkeypatch, tmp_path):
    import app.application_tracker as tracker
    import app.vacancy as vacancy

    db = tmp_path / "applications.db"
    monkeypatch.setattr(tracker, "DB_PATH", db)
    monkeypatch.setattr(vacancy, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)
    profile.save_profile({"name": "User One"}, 1)
    vacancy.init_vacancy_db()
    client = _load_main("formbharat_security_applications").app.test_client()

    for vacancy_id in (True, False, 1.9, 0, -1):
        response = client.post(
            "/api/applications",
            json={"profile_id": 1, "title": "Exam", "vacancy_id": vacancy_id},
        )
        assert response.status_code == 400
        assert "vacancy_id" in response.get_json()["error"]

    missing = client.get("/api/applications/1/0")
    assert missing.status_code == 404
    history = client.get("/api/applications/1/0/history")
    assert history.status_code == 404


def test_document_upload_rejects_unsafe_names_and_types(monkeypatch, tmp_path):
    client = _document_client(monkeypatch, tmp_path)

    for filename in (
        "../secret.png",
        "..\\secret.png",
        "file.exe",
        "file.pdf.exe",
        "file.png.txt",
    ):
        response = _upload(client, filename)
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    assert client.get("/api/documents/1").get_json()["count"] == 0
    accepted = _upload(client, "identity.png")
    assert accepted.status_code == 200

    malformed = client.get("/api/documents/9")
    assert malformed.status_code == 400
    assert "profile_id" in malformed.get_json()["error"]


def test_document_file_access_is_profile_scoped_and_confined(monkeypatch, tmp_path):
    client = _document_client(monkeypatch, tmp_path, saved_profile_ids=(1, 2))
    uploaded_response = _upload(client, "identity.png", b"profile-one-file")
    uploaded = uploaded_response.get_json()
    document_id = uploaded["document_id"]
    stored_bytes = uploaded_response.payload

    missing_profile = client.get(f"/api/documents/file/{document_id}")
    assert missing_profile.status_code == 400

    other_profile = client.get(
        f"/api/documents/file/{document_id}?profile_id=2"
    )
    assert other_profile.status_code == 404
    assert stored_bytes not in other_profile.data

    owned = client.get(f"/api/documents/file/{document_id}?profile_id=1")
    assert owned.status_code == 200
    assert owned.data == stored_bytes

    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"SECRET-OUTSIDE")
    conn = sqlite3.connect(document_vault.DB_PATH)
    conn.execute(
        "UPDATE documents SET storage_path = ? WHERE id = ?",
        (str(secret), document_id),
    )
    conn.commit()
    conn.close()

    escaped = client.get(f"/api/documents/file/{document_id}?profile_id=1")
    assert escaped.status_code == 404
    assert b"SECRET-OUTSIDE" not in escaped.data
    assert secret.read_bytes() == b"SECRET-OUTSIDE"

    wrong_delete = client.delete(
        f"/api/documents/{document_id}?profile_id=2"
    )
    assert wrong_delete.status_code == 404
    assert client.get("/api/documents/1").get_json()["count"] == 1

    deleted = client.delete(f"/api/documents/{document_id}?profile_id=1")
    assert deleted.status_code == 200
    assert secret.exists()
    assert client.get("/api/documents/1").get_json()["count"] == 0


def test_renamed_file_contents_are_rejected(monkeypatch, tmp_path):
    client = _document_client(monkeypatch, tmp_path)
    cases = (
        ("notes.png", b"%PDF-1.7\nrenamed"),
        ("scan.pdf", b"\xff\xd8\xff" + b"jpeg-bytes"),
        ("photo.jpg", b"\x89PNG\r\n\x1a\n" + b"png-bytes"),
        ("plain.pdf", b"this is not a pdf"),
        ("photo.jpg", b"not-a-jpeg", "image/jpeg"),
    )

    for filename, content, *mime in cases:
        file_type = mime[0] if mime else "application/octet-stream"
        response = client.post(
            "/api/documents/upload",
            data={
                "profile_id": "1",
                "doc_type": "identity",
                "file": (BytesIO(content), filename, file_type),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == (
            "File contents do not match a PDF, JPEG, or PNG"
        )

    accepted = _upload(client, "statement.pdf", b"real pdf body")
    assert accepted.status_code == 200
    assert client.get("/api/documents/1").get_json()["count"] == 1


def test_document_page_renders_names_as_text(monkeypatch, tmp_path):
    page = _document_client(monkeypatch, tmp_path).get("/documents").get_data(
        as_text=True
    )
    assert "innerHTML" not in page
    assert "textContent" in page
    assert "profile_id=" in page
