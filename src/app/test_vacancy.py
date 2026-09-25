import importlib.util
import sqlite3
from pathlib import Path

import app.vacancy as vacancy


def _load_app():
    spec = importlib.util.spec_from_file_location(
        "formbharat_main_for_vacancy_test",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)
    return main.app


def test_vacancy_table_can_be_created(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(vacancy, "DB_PATH", db)

    vacancy.init_vacancy_db()

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='vacancies'"
    ).fetchone()
    conn.close()

    assert row == ("vacancies",)


def test_create_and_get_vacancy(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(vacancy, "DB_PATH", db)

    vacancy.init_vacancy_db()

    vacancy_id = vacancy.create_vacancy(
        title="Test Government Vacancy",
        organization="Test Organization",
        category="Government",
        eligibility="Graduate",
        application_start="2026-09-01",
        application_end="2026-09-30",
        official_link="https://example.gov.in/notice"
    )

    item = vacancy.get_vacancy(vacancy_id)

    assert item["title"] == "Test Government Vacancy"
    assert item["organization"] == "Test Organization"
    assert item["eligibility"] == "Graduate"
    assert item["official_link"] == "https://example.gov.in/notice"


def test_list_vacancies(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(vacancy, "DB_PATH", db)

    vacancy.init_vacancy_db()

    vacancy.create_vacancy(
        "Vacancy One", "Org One", official_link="https://example.gov.in/one"
    )
    vacancy.create_vacancy(
        "Vacancy Two", "Org Two", official_link="https://example.gov.in/two"
    )

    items = vacancy.list_vacancies()

    assert len(items) == 2
    assert items[0]["title"] == "Vacancy Two"

def test_vacancy_api_create_list_and_get():
    client = _load_app().test_client()

    response = client.post(
        "/api/vacancies",
        json={
            "title": "API Test Vacancy",
            "organization": "Test Organization",
            "category": "Government",
            "eligibility": "Graduate",
            "application_start": "2026-09-01",
            "application_end": "2026-09-30",
            "official_link": "https://example.gov.in/api-test"
        }
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    vacancy_id = data["vacancy"]["id"]

    response = client.get("/api/vacancies")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert any(v["id"] == vacancy_id for v in data["vacancies"])

    response = client.get(f"/api/vacancies/{vacancy_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["vacancy"]["title"] == "API Test Vacancy"


def test_vacancy_api_validation_and_not_found():
    client = _load_app().test_client()

    response = client.post(
        "/api/vacancies",
        json={"title": "Missing Required Fields"}
    )
    assert response.status_code == 400
    assert response.get_json()["success"] is False

    response = client.get("/api/vacancies/999999999")
    assert response.status_code == 404
    assert response.get_json()["success"] is False

    malformed = client.put(
        "/api/vacancies/1",
        data="not-json",
        content_type="application/json",
    )
    assert malformed.status_code == 400

    missing_link = client.post(
        "/api/vacancies",
        json={
            "title": "No Host",
            "organization": "Org",
            "official_link": "https://",
        },
    )
    assert missing_link.status_code == 400


def test_vacancy_api_update_delete_filter_and_alert(tmp_path, monkeypatch):
    from app import profile

    db = tmp_path / "vacancy-api.db"
    monkeypatch.setattr(vacancy, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)
    vacancy.init_vacancy_db()
    profile.save_profile({"name": "Alert User"}, 1)

    client = _load_app().test_client()
    created = client.post(
        "/api/vacancies",
        json={
            "title": "API Open",
            "organization": "Org",
            "category": "Government",
            "application_start": "2020-01-01",
            "application_end": "2099-01-01",
            "official_link": "https://example.gov.in/api-open",
            "source_name": "Example Board",
        },
    )
    assert created.status_code == 201
    vacancy_id = created.get_json()["vacancy"]["id"]
    assert created.get_json()["vacancy"]["source_name"] == "Example Board"
    assert created.get_json()["vacancy"]["status"] == "open"

    updated = client.put(
        f"/api/vacancies/{vacancy_id}",
        json={"eligibility": "Graduate"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["vacancy"]["eligibility"] == "Graduate"

    listed = client.get("/api/vacancies?category=Government&status=open")
    assert listed.status_code == 200
    assert any(item["id"] == vacancy_id for item in listed.get_json()["vacancies"])

    missing_alert = client.post(
        "/api/vacancies/999999999/alerts",
        json={"profile_id": 1},
    )
    assert missing_alert.status_code == 404

    invalid_profile = client.post(
        f"/api/vacancies/{vacancy_id}/alerts",
        json={"profile_id": 4},
    )
    assert invalid_profile.status_code == 400

    alert = client.post(
        f"/api/vacancies/{vacancy_id}/alerts",
        json={"profile_id": 1},
    )
    assert alert.status_code == 201
    duplicate = client.post(
        f"/api/vacancies/{vacancy_id}/alerts",
        json={"profile_id": 1},
    )
    assert duplicate.status_code == 201
    assert duplicate.get_json()["alert"]["id"] == alert.get_json()["alert"]["id"]

    alerts = client.get("/api/vacancy-alerts/1")
    assert alerts.status_code == 200
    assert len(alerts.get_json()["alerts"]) == 1

    deleted = client.delete(f"/api/vacancies/{vacancy_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/vacancies/{vacancy_id}").status_code == 404


def test_vacancy_update_filter_and_deadline_alert(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(vacancy, "DB_PATH", db)
    vacancy.init_vacancy_db()

    open_id = vacancy.create_vacancy(
        title="Open Post",
        organization="Org",
        category="Government",
        application_start="2020-01-01",
        application_end="2099-01-01",
        official_link="https://example.gov.in/open",
    )
    closed_id = vacancy.create_vacancy(
        title="Closed Post",
        organization="Org",
        category="Private",
        application_start="2020-01-01",
        application_end="2020-02-01",
        official_link="https://example.gov.in/closed",
    )

    updated = vacancy.update_vacancy(open_id, eligibility="Graduate")
    assert updated["eligibility"] == "Graduate"
    assert updated["status"] == "open"
    assert vacancy.get_vacancy(closed_id)["status"] == "closed"

    government = vacancy.list_vacancies(category="Government")
    assert [item["id"] for item in government] == [open_id]

    alert = vacancy.create_vacancy_alert(1, open_id)
    assert alert["alert_type"] == "deadline"
    assert vacancy.list_vacancy_alerts(1)[0]["vacancy_id"] == open_id

    assert vacancy.delete_vacancy(closed_id) is True
    assert vacancy.get_vacancy(closed_id) is None

    again = vacancy.create_vacancy_alert(1, open_id)
    assert again["id"] == alert["id"]
    assert len(vacancy.list_vacancy_alerts(1)) == 1

    imported = vacancy.import_vacancy_record({
        "title": "Imported Post",
        "organization": "Org",
        "official_link": "https://example.gov.in/imported",
        "source_name": "Example Notice",
        "application_start": "2099-01-01",
        "application_end": "2099-02-01",
    })
    imported_item = vacancy.get_vacancy(imported)
    assert imported_item["source_name"] == "Example Notice"
    assert imported_item["status"] == "upcoming"

    class FixedSource:
        def discover(self):
            return [{
                "title": "Discovered Post",
                "organization": "Org",
                "official_link": "https://example.gov.in/discovered",
                "source_name": "Supplied List",
            }]

    try:
        vacancy.discover_vacancies(object())
        assert False
    except ValueError:
        pass

    discovered_ids = vacancy.discover_vacancies(FixedSource())
    discovered = vacancy.get_vacancy(discovered_ids[0])
    assert discovered["title"] == "Discovered Post"
    assert discovered["source_name"] == "Supplied List"
    assert discovered.get("officially_verified", False) is False

    try:
        vacancy.create_vacancy(
            "Bad Link", "Org", official_link="notaurl"
        )
        assert False
    except ValueError:
        pass
