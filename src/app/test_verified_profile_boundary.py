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
