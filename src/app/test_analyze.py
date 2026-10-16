import importlib.util
from pathlib import Path

import pytest

from app import profile as profile_module


HTML = "<form><input id='name' name='name' type='text'></form>"


@pytest.fixture
def main(monkeypatch, tmp_path):
    from app import application_tracker, document_vault, vacancy, verified_profile

    db = tmp_path / "formbharat.db"
    storage = tmp_path / "documents"
    monkeypatch.setenv("FORMBHARAT_DATABASE_PATH", str(db))
    monkeypatch.setenv("FORMBHARAT_STORAGE_DIR", str(storage))
    monkeypatch.setattr(vacancy, "DB_PATH", db)
    monkeypatch.setattr(application_tracker, "DB_PATH", db)
    monkeypatch.setattr(profile_module, "DB_PATH", db)
    monkeypatch.setattr(verified_profile, "DB_PATH", db)
    monkeypatch.setattr(document_vault, "DB_PATH", str(db))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(storage))

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


def test_analyze_review_withholds_invalid_verified_values(main):
    from app import verified_profile

    verified_profile.save_verified_profile(
        {
            "name": "Verified One",
            "email": "not-an-email",
            "dob": "31-02-1991",
            "pincode": "12345",
        },
        profile_id=1,
        verified=True,
    )

    response = _post(main, {
        "profile_id": 1,
        "html": """
        <form>
          <input id="name" name="name" type="text">
          <input id="email" name="email" type="email">
          <input id="dob" name="dob" type="date">
          <input id="pincode" name="pincode" type="text">
          <input id="otp" name="otp" type="text">
          <button type="submit">Submit</button>
        </form>
        """,
    })
    result = response.get_json()["result"]

    assert response.status_code == 200
    assert result["submitted"] is False
    assert result["filled"] == [
        {"field": "name", "profile_key": "name", "value": "Verified One"}
    ]
    assert result["review"]["submitted"] is False
    assert result["review"]["proposed"] == result["filled"]
    reasons = {
        item["field"]: item["reason"] for item in result["review"]["withheld"]
    }
    assert reasons["email"] == "invalid"
    assert reasons["dob"] == "invalid"
    assert reasons["pincode"] == "invalid"
    assert reasons["otp"] == "blocked"
    assert "not-an-email" not in result["filled_html"]


def test_analyze_does_not_fill_an_unverified_saved_profile(main):
    from app import verified_profile

    verified_profile.save_verified_profile(
        {"name": "Not Verified"},
        profile_id=1,
        verified=False,
    )

    response = _post(main, {"profile_id": 1, "html": HTML})
    result = response.get_json()["result"]

    assert response.status_code == 200
    assert result["verified_profile"] is False
    assert result["filled"] == []
    assert result["review"]["proposed"] == []
    assert result["submitted"] is False
    assert "Not Verified" not in result["filled_html"]
