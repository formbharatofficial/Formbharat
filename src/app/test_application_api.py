import importlib.util
from pathlib import Path

import app.application_tracker as tracker
import app.vacancy as vacancy
from app import profile


def _load_app():
    spec = importlib.util.spec_from_file_location(
        "formbharat_main_for_application_api_test",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)
    return main.app.test_client()


def _client(tmp_path, monkeypatch):
    db = tmp_path / "applications.db"
    monkeypatch.setattr(tracker, "DB_PATH", db)
    monkeypatch.setattr(vacancy, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)
    profile.save_profile({"name": "User One"}, 1)
    profile.save_profile({"name": "User Two"}, 2)
    vacancy.init_vacancy_db()
    vacancy_id = vacancy.create_vacancy(
        title="Tracked Vacancy",
        organization="Org",
        official_link="https://example.gov.in/tracked",
    )
    return _load_app(), vacancy_id


def test_application_api_rejects_coerced_profile_ids(tmp_path, monkeypatch):
    client, _vacancy_id = _client(tmp_path, monkeypatch)

    for profile_id in (True, False, 1.9):
        response = client.post(
            "/api/applications",
            json={"profile_id": profile_id, "title": "Exam"},
        )
        assert response.status_code == 400
        body = response.get_json()
        assert body["success"] is False
        assert "profile_id" in body["error"]
        assert "integer" in body["error"]

    created = client.post(
        "/api/applications",
        json={"profile_id": 1, "title": "Valid Integer Profile"},
    )
    assert created.status_code == 201
    assert created.get_json()["application"]["profile_id"] == 1
    assert created.get_json()["application"]["title"] == "Valid Integer Profile"


def test_application_api_rejects_missing_json_invalid_profile_and_unknown_records(
    tmp_path, monkeypatch
):
    client, vacancy_id = _client(tmp_path, monkeypatch)

    missing = client.post(
        "/api/applications",
        data="not-json",
        content_type="application/json",
    )
    assert missing.status_code == 400
    assert missing.get_json()["success"] is False
    assert missing.get_json()["error"] == "Invalid or missing JSON data"

    invalid_profile = client.post(
        "/api/applications",
        json={"profile_id": 4, "title": "Exam"},
    )
    assert invalid_profile.status_code == 400
    assert invalid_profile.get_json()["success"] is False
    assert "profile_id" in invalid_profile.get_json()["error"]

    unknown_vacancy = client.post(
        "/api/applications",
        json={"profile_id": 1, "title": "Exam", "vacancy_id": 999999999},
    )
    assert unknown_vacancy.status_code == 404
    assert unknown_vacancy.get_json() == {
        "success": False,
        "error": "Vacancy not found",
    }

    unknown = client.get("/api/applications/1/999999999")
    assert unknown.status_code == 404
    assert unknown.get_json() == {
        "success": False,
        "error": "Application not found",
    }
    assert vacancy_id


def test_application_api_creates_lists_filters_and_isolates_profiles(
    tmp_path, monkeypatch
):
    client, vacancy_id = _client(tmp_path, monkeypatch)

    created = client.post(
        "/api/applications",
        json={
            "profile_id": 1,
            "title": "SSC CGL",
            "organization": "SSC",
            "vacancy_id": vacancy_id,
        },
    )
    assert created.status_code == 201
    body = created.get_json()
    assert body["success"] is True
    application = body["application"]
    assert application["profile_id"] == 1
    assert application["title"] == "SSC CGL"
    assert application["vacancy_id"] == vacancy_id
    assert application["status"] == "draft"
    application_id = application["id"]

    client.post(
        "/api/applications",
        json={"profile_id": 1, "title": "Submitted Exam", "status": "submitted"},
    )
    client.post(
        "/api/applications",
        json={"profile_id": 2, "title": "Other Profile Exam"},
    )

    listed = client.get("/api/applications/1")
    assert listed.status_code == 200
    titles = [item["title"] for item in listed.get_json()["applications"]]
    assert titles == ["Submitted Exam", "SSC CGL"]
    assert all(item["profile_id"] == 1 for item in listed.get_json()["applications"])

    filtered = client.get("/api/applications/1?status=submitted")
    assert filtered.status_code == 200
    filtered_items = filtered.get_json()["applications"]
    assert [item["title"] for item in filtered_items] == ["Submitted Exam"]

    other = client.get(f"/api/applications/2/{application_id}")
    assert other.status_code == 404
    assert other.get_json()["error"] == "Application not found"

    other_history = client.get(f"/api/applications/2/{application_id}/history")
    assert other_history.status_code == 404

    other_update = client.put(
        f"/api/applications/2/{application_id}",
        json={"status": "withdrawn"},
    )
    assert other_update.status_code == 404
    assert client.get(
        f"/api/applications/1/{application_id}"
    ).get_json()["application"]["status"] == "draft"


def test_application_api_status_update_is_stored_in_history(tmp_path, monkeypatch):
    client, _vacancy_id = _client(tmp_path, monkeypatch)

    created = client.post(
        "/api/applications",
        json={"profile_id": 1, "title": "Railway Exam"},
    )
    application_id = created.get_json()["application"]["id"]

    invalid = client.put(
        f"/api/applications/1/{application_id}",
        json={"status": "notified"},
    )
    assert invalid.status_code == 400
    assert invalid.get_json()["success"] is False

    updated = client.put(
        f"/api/applications/1/{application_id}",
        json={"status": "in_progress", "note": "Started filling"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["application"]["status"] == "in_progress"

    history = client.get(f"/api/applications/1/{application_id}/history")
    assert history.status_code == 200
    entries = history.get_json()["history"]
    assert [entry["status"] for entry in entries] == ["draft", "in_progress"]
    assert entries[1]["note"] == "Started filling"
