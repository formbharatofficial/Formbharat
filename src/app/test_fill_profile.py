import json

from app.fill_profile import saved_identity_numbers, with_saved_identity


def test_saved_document_numbers_are_added_only_for_filling(monkeypatch):
    monkeypatch.setattr(
        "app.fill_profile.saved_identity_numbers",
        lambda profile_id: {"pan_number": "ABCDE1234F", "aadhaar_number": "123412341234"},
    )
    profile = {"name": "Asha"}

    merged = with_saved_identity(profile, 1)

    assert merged["name"] == "Asha"
    assert merged["pan_number"] == "ABCDE1234F"
    assert merged["aadhaar_number"] == "123412341234"
    assert "pan_number" not in profile


def test_missing_document_table_adds_nothing(monkeypatch, tmp_path):
    from app import document_vault

    monkeypatch.setattr(document_vault, "DB_PATH", str(tmp_path / "missing.db"))

    assert saved_identity_numbers(1) == {}
    assert with_saved_identity({"name": "Asha"}, 1) == {"name": "Asha"}


def test_extracted_document_json_supplies_the_numbers(monkeypatch, tmp_path):
    import sqlite3

    from app import document_vault

    db = tmp_path / "docs.db"
    connection = sqlite3.connect(db)
    connection.execute(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER,
            extracted_data TEXT
        )
        """
    )
    connection.execute(
        "INSERT INTO documents (profile_id, extracted_data) VALUES (?, ?)",
        (1, json.dumps({"pan_number": "ABCDE1234F", "aadhaar_number": ""})),
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(document_vault, "DB_PATH", str(db))

    assert saved_identity_numbers(1) == {"pan_number": "ABCDE1234F"}
