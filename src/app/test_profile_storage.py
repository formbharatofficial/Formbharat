import sqlite3

import pytest

from app import profile


def _use_test_database(monkeypatch, tmp_path):
    db_path = tmp_path / "formbharat.db"
    monkeypatch.setattr(profile, "DB_PATH", db_path)
    return db_path


def _profile_data(number):
    return {
        "name": f"User {number}",
        "email": f"user{number}@example.com",
        "mobile": f"900000000{number}",
        "dob": f"1990-01-0{number}",
        "address": f"Address {number}",
        "country": "in",
    }


def _create_legacy_database(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            mobile TEXT NOT NULL DEFAULT '',
            dob TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT 'in',
            father_name TEXT NOT NULL DEFAULT '',
            mother_name TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        INSERT INTO profile
        (id, name, email, mobile, dob, address, country, father_name, mother_name)
        VALUES (1, 'Existing User', 'existing@example.com', '9000000000',
                '1990-01-01', 'Existing Address', 'in',
                'Existing Father', 'Existing Mother')
    """)
    conn.commit()
    conn.close()


def test_profiles_one_through_five_are_saved_and_retrieved(monkeypatch, tmp_path):
    _use_test_database(monkeypatch, tmp_path)

    for profile_id in range(1, profile.MAX_PROFILES + 1):
        profile.save_profile(_profile_data(profile_id), profile_id)

    for profile_id in range(1, profile.MAX_PROFILES + 1):
        saved = profile.get_profile(profile_id)
        assert saved["name"] == f"User {profile_id}"
        assert saved["email"] == f"user{profile_id}@example.com"


def test_profile_six_is_rejected(monkeypatch, tmp_path):
    _use_test_database(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="between 1 and 5"):
        profile.save_profile(_profile_data(6), 6)

    with pytest.raises(ValueError, match="between 1 and 5"):
        profile.get_profile(6)


def test_saving_one_profile_does_not_overwrite_another(monkeypatch, tmp_path):
    _use_test_database(monkeypatch, tmp_path)
    profile.save_profile(_profile_data(1), 1)
    profile.save_profile(_profile_data(2), 2)

    updated_profile_one = _profile_data(1)
    updated_profile_one["name"] = "Updated User 1"
    profile.save_profile(updated_profile_one, 1)

    assert profile.get_profile(1)["name"] == "Updated User 1"
    assert profile.get_profile(2)["name"] == "User 2"


def test_default_save_and_get_use_profile_one(monkeypatch, tmp_path):
    _use_test_database(monkeypatch, tmp_path)
    profile.save_profile(_profile_data(1))

    assert profile.get_profile()["name"] == "User 1"
    assert profile.get_profile(1)["name"] == "User 1"


def test_migration_preserves_existing_profile_one_data(monkeypatch, tmp_path):
    db_path = _use_test_database(monkeypatch, tmp_path)
    _create_legacy_database(db_path)

    profile.init_db()

    saved = profile.get_profile(1)
    assert saved["name"] == "Existing User"
    assert saved["email"] == "existing@example.com"

    conn = sqlite3.connect(db_path)
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'profile'"
    ).fetchone()[0]
    conn.close()
    assert "CHECK (id BETWEEN 1 AND 5)" in schema


def test_migration_preserves_father_and_mother_data(monkeypatch, tmp_path):
    db_path = _use_test_database(monkeypatch, tmp_path)
    _create_legacy_database(db_path)

    profile.init_db()

    saved = profile.get_profile(1)
    assert saved["father_name"] == "Existing Father"
    assert saved["mother_name"] == "Existing Mother"
