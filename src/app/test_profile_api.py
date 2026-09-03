from flask import Flask
import pytest

from app import profile
from app.profile_ui import register_profile_ui


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(profile, "DB_PATH", tmp_path / "formbharat.db")
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_profile_ui(app)
    return app.test_client()


def _profile_data(number):
    return {
        "name": f"API User {number}",
        "email": f"api{number}@example.com",
        "mobile": f"800000000{number}",
        "dob": f"1990-01-0{number}",
        "address": f"API Address {number}",
        "country": "in",
    }


def test_get_profile_returns_requested_profile(client):
    response = client.get("/api/profile/1")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "profile": profile.PROFILE_DEFAULTS,
    }


def test_post_profile_saves_and_returns_parent_fields(client):
    data = _profile_data(1)
    data.update({
        "father_name": "API Father",
        "mother_name": "API Mother",
    })

    response = client.post("/api/profile/1", json=data)

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "Profile saved successfully"
    assert body["profile"]["father_name"] == "API Father"
    assert body["profile"]["mother_name"] == "API Mother"


@pytest.mark.parametrize("request_kwargs", [
    {},
    {"data": "not-json", "content_type": "application/json"},
])
def test_post_profile_rejects_missing_or_invalid_json(client, request_kwargs):
    response = client.post("/api/profile/1", **request_kwargs)

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": "Invalid or missing JSON data",
    }


@pytest.mark.parametrize("profile_id", ["0", "6", "not-an-id"])
def test_profile_api_rejects_invalid_profile_ids(client, profile_id):
    response = client.get(f"/api/profile/{profile_id}")

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "between 1 and 5" in response.get_json()["error"]


def test_profiles_are_independent_through_api(client):
    first = _profile_data(1)
    second = _profile_data(2)
    second["name"] = "Second API Profile"

    assert client.post("/api/profile/1", json=first).status_code == 200
    assert client.post("/api/profile/2", json=second).status_code == 200

    first_result = client.get("/api/profile/1").get_json()
    second_result = client.get("/api/profile/2").get_json()

    assert first_result["profile"]["name"] == "API User 1"
    assert second_result["profile"]["name"] == "Second API Profile"


def test_post_profile_saves_extended_education_fields(client):
    data = _profile_data(1)
    data.update({
        "post_graduation_degree": "M.A.",
        "post_graduation_roll_number": "PG-1",
        "post_graduation_passing_year": "2018",
        "post_graduation_marks": "800",
        "post_graduation_percentage": "80%",
        "diploma_name": "Computer Diploma",
        "diploma_roll_number": "D-1",
        "diploma_passing_year": "2017",
        "diploma_marks": "700",
        "diploma_percentage": "70%",
        "other_qualification": "CCC",
    })

    response = client.post("/api/profile/1", json=data)

    assert response.status_code == 200
    saved = response.get_json()["profile"]

    for key, value in data.items():
        assert saved[key] == value
