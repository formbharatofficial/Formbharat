import pytest
from pathlib import Path
from flask import Flask

from app import profile as profile_module



@pytest.fixture
def client(monkeypatch, tmp_path):
    from app import profile, document_vault, verified_profile

    db = tmp_path / "formbharat.db"

    monkeypatch.setattr(profile, "DB_PATH", db)
    monkeypatch.setattr(document_vault, "DB_PATH", str(db))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(verified_profile, "DB_PATH", db)

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "formbharat_src_main",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)

    main.app.config["TESTING"] = True
    verified_profile.init_verified_profile_db()

    return main.app.test_client()

def test_analyze_must_not_use_raw_profile_directly(client):
    raw_profile = dict(profile_module.PROFILE_DEFAULTS)
    raw_profile["name"] = "RAW ONLY TEST"

    response = client.post(
        "/analyze",
        json={
            "profile": raw_profile,
            "html": """
            <form>
              <input name="name">
            </form>
            """
        },
    )

    data = response.get_json()
    assert data["success"] is True

    result = data["result"]

    # Bible rule:
    # Raw Profile must NEVER be the Form Filling source.
    # Until a Verified Profile exists, the form must not be
    # filled from the raw profile.
    assert result.get("filled_count", 0) == 0, (
        "RAW PROFILE IS BEING USED DIRECTLY BY /analyze"
    )


def _insert_extracted_document(
    db_path, profile_id, extracted_data, reference="DOC-GATE", verified=0
):
    import json
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO documents (
                profile_id, doc_type, original_filename, storage_path,
                mime_type, file_hash, extracted_text, extracted_data,
                verified, created_at, updated_at, document_version,
                document_reference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id, "aadhaar", "aadhaar.png", "/tmp/aadhaar.png",
                "image/png", "gate-hash-" + reference, "",
                json.dumps(extracted_data), verified,
                "2026-09-22T00:00:00", "2026-09-22T00:00:00",
                1, reference,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_direct_verified_true_cannot_forge_a_verified_profile(client, tmp_path):
    from app import profile

    profile.save_profile({"name": "Forged User"}, profile_id=1)

    response = client.post(
        "/api/profile/1/verified",
        json={
            "verified": True,
            "name": "Forged User",
        },
    )

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["verified"] is False
    assert body["profile"] is None

    stored = client.get("/api/profile/1/verified").get_json()
    assert stored["verified"] is False
    assert stored["profile"] is None


def test_matching_data_requires_user_confirmation_before_promotion(
    client, tmp_path
):
    from app import profile

    profile.save_profile({"name": "Sunil Kumar"}, profile_id=1)
    _insert_extracted_document(
        tmp_path / "formbharat.db",
        1,
        {"name": "Sunil Kumar"},
        verified=1,
    )

    unconfirmed = client.post(
        "/api/profile/1/verified",
        json={"verified": True, "name": "Sunil Kumar"},
    ).get_json()

    assert unconfirmed["success"] is False
    assert unconfirmed["verified"] is False
    assert "confirmation" in unconfirmed["error"].lower()

    stored = client.get("/api/profile/1/verified").get_json()
    assert stored["verified"] is False


def test_matching_verified_data_can_be_promoted_with_confirmation(
    client, tmp_path
):
    from app import profile

    profile.save_profile({"name": "Sunil Kumar"}, profile_id=1)
    _insert_extracted_document(
        tmp_path / "formbharat.db",
        1,
        {"name": "Sunil Kumar"},
        verified=1,
    )

    response = client.post(
        "/api/profile/1/verified",
        json={"confirmed": True, "verified": True},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["verified"] is True
    assert body["profile"]["name"] == "Sunil Kumar"


def test_mismatch_cannot_become_verified_even_with_confirmation(
    client, tmp_path
):
    from app import profile

    profile.save_profile({"name": "Sunil Kumar"}, profile_id=1)
    _insert_extracted_document(
        tmp_path / "formbharat.db",
        1,
        {"name": "Sunil Singh"},
        reference="DOC-MISMATCH",
        verified=1,
    )

    response = client.post(
        "/api/profile/1/verified",
        json={
            "confirmed": True,
            "verified": True,
            "name": "Sunil Kumar",
        },
    )

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["verified"] is False
    assert body["profile"] is None

    stored = client.get("/api/profile/1/verified").get_json()
    assert stored["verified"] is False
    assert stored["profile"] is None


def test_matching_unverified_document_cannot_promote_a_verified_profile(
    client, tmp_path
):
    from app import profile

    profile.save_profile({"name": "Sunil Kumar"}, profile_id=1)
    _insert_extracted_document(
        tmp_path / "formbharat.db",
        1,
        {"name": "Sunil Kumar"},
        verified=0,
    )

    response = client.post(
        "/api/profile/1/verified",
        json={"confirmed": True, "verified": True},
    )

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert body["verified"] is False
    assert body["profile"] is None

    stored = client.get("/api/profile/1/verified").get_json()
    assert stored["verified"] is False
    assert stored["profile"] is None
