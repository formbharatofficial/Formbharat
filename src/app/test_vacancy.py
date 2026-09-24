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
