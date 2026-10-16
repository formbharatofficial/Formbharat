import hashlib
import os
import sqlite3
from pathlib import Path

from flask import Flask

from app import accounts, application_tracker, document_encryption, document_vault, profile
from app.ownership import claim_status, profile_owner
from app.rendered_assist import assist_rendered_page, assist_verified_profile


PNG = b"\x89PNG\r\n\x1a\n"
PASSWORD = "correct-horse1"


def _key():
    return "11" * 32


def _isolate(monkeypatch, tmp_path):
    database = tmp_path / "formbharat.db"
    monkeypatch.setattr(profile, "DB_PATH", database)
    monkeypatch.setattr(document_vault, "DB_PATH", str(database))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(application_tracker, "DB_PATH", database)
    return database


def _account_client(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret-key"
    accounts.register_account_routes(app)
    from app.profile_ui import register_profile_ui
    register_profile_ui(app)
    return app.test_client()


def _file_url(tmp_path):
    page = tmp_path / "form.html"
    page.write_text("<html></html>", encoding="utf-8")
    return page.resolve().as_uri()


class _Opener:
    def __init__(self, html):
        self.html = html

    def open(self, _url):
        return self.html


def test_register_does_not_claim_a_legacy_slot(monkeypatch, tmp_path):
    client = _account_client(monkeypatch, tmp_path)
    profile.save_profile({"name": "Existing User", "email": "old@example.com"}, 1)

    response = client.post("/api/account/register", json={
        "email": "new@example.com",
        "password": PASSWORD,
    })
    hidden = client.get("/api/profile/1")

    assert response.status_code == 200
    assert response.get_json()["claimed_slots"] == []
    assert profile_owner(1) is None
    assert hidden.status_code == 403
    assert "Existing User" not in hidden.get_data(as_text=True)


def test_empty_slot_claim_requires_code_and_stays_private(monkeypatch, tmp_path):
    client = _account_client(monkeypatch, tmp_path)
    client.post("/api/account/register", json={
        "email": "owner@example.com",
        "password": PASSWORD,
    })
    monkeypatch.delenv("FORMBHARAT_SLOT_CLAIM_CODE", raising=False)

    unavailable = client.post("/api/profile/2/claim", json={
        "confirm_claim": True,
        "claim_code": "secret-code",
    })
    assert unavailable.status_code == 403
    assert claim_status(2) == "empty"

    monkeypatch.setenv("FORMBHARAT_SLOT_CLAIM_CODE", "secret-code")
    rejected = client.post("/api/profile/2/claim", json={
        "confirm_claim": False,
        "claim_code": "secret-code",
    })
    assert rejected.status_code == 403
    assert claim_status(2) == "empty"

    claimed = client.post("/api/profile/2/claim", json={
        "confirm_claim": True,
        "claim_code": "secret-code",
    })
    assert claimed.status_code == 200
    assert claim_status(2) == "owned"

    other = _account_client(monkeypatch, tmp_path)
    other.post("/api/account/register", json={
        "email": "other@example.com",
        "password": PASSWORD,
    })
    denied = other.get("/api/profile/2")
    assert denied.status_code == 403
    assert "owner@example.com" not in denied.get_data(as_text=True)


def test_legacy_data_cannot_be_claimed(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    profile.save_profile({"name": "Existing User"}, 1)
    app = Flask(__name__)
    app.secret_key = "test-secret"
    accounts.register_account_routes(app)
    client = app.test_client()
    client.post("/api/account/register", json={
        "email": "owner@example.com",
        "password": PASSWORD,
    })
    monkeypatch.setenv("FORMBHARAT_SLOT_CLAIM_CODE", "secret-code")

    response = client.post("/api/profile/1/claim", json={
        "confirm_claim": True,
        "claim_code": "secret-code",
    })

    assert response.status_code == 403
    assert response.get_json()["error"] == "Legacy profile data cannot be claimed."
    from app.ownership import profile_owner
    assert profile_owner(1) is None


def test_missing_key_blocks_required_upload_and_legacy_file_stays(monkeypatch, tmp_path):
    storage = tmp_path / "documents"
    storage.mkdir()
    legacy = storage / "legacy.png"
    legacy.write_bytes(PNG + b"old")
    before = legacy.read_bytes()
    monkeypatch.delenv("FORMBHARAT_DOCUMENT_KEY", raising=False)
    monkeypatch.setenv("FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION", "1")

    try:
        document_encryption.store_bytes(PNG + b"new")
        assert False, "upload should be rejected"
    except document_encryption.DocumentStorageError as error:
        assert "not available" in str(error)
        assert "KEY" not in str(error)

    assert legacy.read_bytes() == before
    assert document_encryption.read_bytes(legacy) == before


def test_new_file_is_encrypted_and_ocr_temp_is_removed(monkeypatch, tmp_path):
    monkeypatch.setenv("FORMBHARAT_DOCUMENT_KEY", _key())
    stored = document_encryption.store_bytes(PNG + b"secret")
    path = tmp_path / "new.png"
    path.write_bytes(stored)
    seen = []

    def reader(ocr_path):
        seen.append(ocr_path)
        assert os.path.exists(ocr_path)
        assert Path(ocr_path).read_bytes() == PNG + b"secret"
        return "Name: Asha"

    assert stored.startswith(document_encryption.MAGIC)
    assert PNG not in stored
    assert document_encryption.read_for_ocr(path, reader) == "Name: Asha"
    assert seen and not os.path.exists(seen[0])
    protected = document_encryption.protect_text("Name: Asha")
    assert protected.startswith(document_encryption.TEXT_PREFIX)
    assert "Asha" not in protected
    assert document_encryption.reveal_text(protected) == "Name: Asha"
    assert document_encryption.reveal_text('{"name": "Asha"}') == '{"name": "Asha"}'


def test_guardian_is_filled_only_from_a_verified_separate_value(monkeypatch, tmp_path):
    html = """
    <form>
      <label for="guardian_name">Guardian Name</label>
      <input id="guardian_name" name="guardian_name" type="text">
    </form>
    """
    same = assist_rendered_page(
        _Opener(html),
        _file_url(tmp_path),
        {"name": "Sunil Kumar", "guardian_name": "Sunil Kumar"},
    )
    separate = assist_rendered_page(
        _Opener(html),
        _file_url(tmp_path),
        {"name": "Sunil Kumar", "guardian_name": "Test Guardian"},
    )

    assert same["filled"] == []
    assert "Sunil Kumar" not in same["filled_html"]
    assert separate["filled"][0]["value"] == "Test Guardian"

    from app import verified_profile
    database = tmp_path / "verified.db"
    monkeypatch.setattr(profile, "DB_PATH", database)
    monkeypatch.setattr(verified_profile, "DB_PATH", database)
    from app import document_vault
    monkeypatch.setattr(document_vault, "DB_PATH", str(database))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    verified_profile.save_verified_profile(
        {"name": "Sunil Kumar", "guardian_name": "Test Guardian"},
        profile_id=1,
        verified=False,
    )
    unverified = assist_verified_profile(_Opener(html), _file_url(tmp_path), 1)
    verified_profile.save_verified_profile(
        {"name": "Sunil Kumar", "guardian_name": "Test Guardian"},
        profile_id=1,
        verified=True,
    )
    verified = assist_verified_profile(_Opener(html), _file_url(tmp_path), 1)

    assert unverified["filled"] == []
    assert verified["filled"][0]["value"] == "Test Guardian"


def test_repository_database_copy_migrates_without_changing_original(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / "formbharat.db"
    documents = source.parent / "documents"
    original = source.read_bytes()
    original_hash = hashlib.sha256(original).hexdigest()
    documents_mtime = documents.stat().st_mtime_ns
    copy_path = tmp_path / "formbharat.db"
    copy_path.write_bytes(original)
    connection = sqlite3.connect(copy_path)
    before = connection.execute(
        "SELECT id, name, father_name, mother_name FROM profile"
    ).fetchall()
    connection.close()

    monkeypatch.setattr(profile, "DB_PATH", copy_path)
    profile.init_db()

    connection = sqlite3.connect(copy_path)
    after = connection.execute(
        """
        SELECT id, name, father_name, mother_name, guardian_name, owner_user_id
        FROM profile
        """
    ).fetchall()
    connection.close()

    assert [(row[0], row[1], row[2], row[3]) for row in after] == before
    assert all(row[4] == "" and row[5] is None for row in after)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    assert documents.stat().st_mtime_ns == documents_mtime
