from app.eligibility import assess_eligibility
from app.access_boundary import slot_access
from app.document_encryption import encryption_status


def test_free_text_eligibility_stays_unknown():
    result = assess_eligibility(
        {"eligibility": "Graduate", "title": "Clerk"},
        {"category": "OBC"},
    )

    assert result["status"] == "unknown"
    assert result["checks"] == []
    assert "free-text" in result["reason"]


def test_explicit_criteria_compare_only_supplied_fields():
    vacancy = {
        "criteria": [
            {"field": "category", "equals": "OBC"},
            {"field": "state", "equals": "UP"},
        ]
    }

    met = assess_eligibility(
        vacancy,
        {"category": "obc", "state": "UP"},
    )
    missing = assess_eligibility(vacancy, {"category": "OBC"})
    unmet = assess_eligibility(
        vacancy,
        {"category": "SC", "state": "UP"},
    )

    assert met["status"] == "met"
    assert missing["status"] == "unknown"
    assert unmet["status"] == "not_met"
    assert unmet["checks"][0] == {"field": "category", "status": "not_met"}


def test_unclear_criterion_is_unknown():
    result = assess_eligibility(
        {"criteria": [{"field": "category"}]},
        {"category": "OBC"},
    )

    assert result["status"] == "unknown"
    assert result["reason"] == "a criterion is not explicit"


def test_slots_are_not_accounts_and_files_are_not_encrypted():
    access = slot_access()
    storage = encryption_status()

    assert access["authenticated_account"] is False
    assert access["access"] == "profile_slot"
    assert storage["enabled"] is False
    assert storage["existing_files"] == "unchanged"


def test_eligibility_and_access_routes_do_not_invent_a_decision(
    monkeypatch, tmp_path
):
    import importlib.util
    from pathlib import Path

    from app import application_tracker, document_vault, profile, vacancy, verified_profile

    db = tmp_path / "formbharat.db"
    storage = tmp_path / "documents"
    monkeypatch.setenv("FORMBHARAT_DATABASE_PATH", str(db))
    monkeypatch.setenv("FORMBHARAT_STORAGE_DIR", str(storage))
    monkeypatch.setattr(vacancy, "DB_PATH", db)
    monkeypatch.setattr(application_tracker, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)
    monkeypatch.setattr(verified_profile, "DB_PATH", db)
    monkeypatch.setattr(document_vault, "DB_PATH", str(db))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(storage))
    vacancy.init_vacancy_db()
    vacancy_id = vacancy.create_vacancy(
        title="Clerk",
        organization="Board",
        eligibility="Graduate",
        official_link="https://example.gov.in/clerk",
    )

    spec = importlib.util.spec_from_file_location(
        "formbharat_eligibility_main",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    client = loaded.app.test_client()

    access = client.get("/api/access")
    decision = client.get(f"/api/vacancies/{vacancy_id}/eligibility?profile_id=1")

    assert access.status_code == 200
    assert access.get_json()["authenticated_account"] is False
    assert access.get_json()["documents"]["enabled"] is False
    assert decision.status_code == 200
    assert decision.get_json()["status"] == "unknown"
    assert decision.get_json()["authenticated_account"] is False
