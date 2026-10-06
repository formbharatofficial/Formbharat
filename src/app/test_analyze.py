import importlib.util
from pathlib import Path

import pytest

from app import profile as profile_module


HTML = "<form><input id='name' name='name' type='text'></form>"


@pytest.fixture
def main(monkeypatch, tmp_path):
    from app import document_vault, verified_profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(profile_module, "DB_PATH", db)
    monkeypatch.setattr(document_vault, "DB_PATH", str(db))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(verified_profile, "DB_PATH", db)

    spec = importlib.util.spec_from_file_location(
        "formbharat_analyze_main",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded.app.config["TESTING"] = True
    verified_profile.init_verified_profile_db()
    return loaded


def _post(main, payload):
    return main.app.test_client().post("/analyze", json=payload)


def test_analyze_rejects_missing_empty_and_non_string_html(main):
    cases = [
        {},
        {"html": ""},
        {"html": "   "},
        {"html": None},
        {"html": ["<form></form>"]},
        {"html": {"form": "<form></form>"}},
        {"html": 1},
    ]

    for payload in cases:
        response = _post(main, payload)
        body = response.get_json()
        assert response.status_code == 400
        assert body == {
            "success": False,
            "error": "html must be a non-empty string",
        }


def test_analyze_rejects_html_over_the_maximum_size(main):
    main.MAX_ANALYZE_HTML_BYTES = 32
    response = _post(main, {"html": "x" * 33})
    body = response.get_json()

    assert response.status_code == 400
    assert body == {
        "success": False,
        "error": "html exceeds the maximum size",
    }


def test_analyze_ignores_request_profile_without_a_verified_profile(main):
    response = _post(main, {
        "profile_id": 1,
        "profile": {"name": "RAW ONLY TEST"},
        "html": HTML,
    })
    body = response.get_json()

    assert response.status_code == 200
    assert body["success"] is True
    result = body["result"]
    assert result["profile"] is None
    assert result["verified_profile"] is False
    assert result["filled_count"] == 0
    assert "RAW ONLY TEST" not in result["filled_html"]


def test_analyze_uses_the_verified_profile_for_profile_id(main):
    from app import verified_profile

    verified_profile.save_verified_profile(
        {"name": "Verified One"},
        profile_id=1,
        verified=True,
    )
    verified_profile.save_verified_profile(
        {"name": "Verified Two"},
        profile_id=2,
        verified=True,
    )

    response = _post(main, {
        "profile_id": 1,
        "profile": {"name": "Attacker"},
        "html": HTML,
    })
    body = response.get_json()

    assert response.status_code == 200
    assert body["success"] is True
    result = body["result"]
    assert set(body.keys()) == {"success", "result"}
    assert result["message"] == "Form received successfully."
    assert result["verified_profile"] is True
    assert result["profile"]["name"] == "Verified One"
    assert result["filled_count"] == 1
    assert result["filled"][0]["value"] == "Verified One"
    assert "Verified One" in result["filled_html"]
    assert "Attacker" not in result["filled_html"]
    assert "Verified Two" not in result["filled_html"]
    for key in (
        "fields_detected",
        "fields",
        "matched_fields",
        "filled_html",
        "filled",
        "skipped",
        "filled_count",
        "skipped_count",
    ):
        assert key in result
