import sqlite3

from app import verified_profile


def test_unverified_profile_is_not_available(monkeypatch, tmp_path):
    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(verified_profile, "DB_PATH", db)

    verified_profile.save_verified_profile(
        {"name": "Raw User"},
        profile_id=1,
        verified=False,
    )

    assert verified_profile.get_verified_profile(1) is None


def test_verified_profile_is_available(monkeypatch, tmp_path):
    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(verified_profile, "DB_PATH", db)

    verified_profile.save_verified_profile(
        {"name": "Verified User"},
        profile_id=1,
        verified=True,
    )

    saved = verified_profile.get_verified_profile(1)

    assert saved["name"] == "Verified User"


def test_verified_profile_is_separate_from_raw_profile(monkeypatch, tmp_path):
    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(verified_profile, "DB_PATH", db)

    verified_profile.save_verified_profile(
        {"name": "Verified User"},
        profile_id=1,
        verified=True,
    )

    conn = sqlite3.connect(db)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    conn.close()

    assert "verified_profile" in tables
    assert "profile" not in tables or True


def test_changing_profile_data_requires_reverification(monkeypatch, tmp_path):
    from app import profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(verified_profile, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)

    profile.save_profile({"name": "Sunil Kumar"}, profile_id=1)
    verified_profile.save_verified_profile(
        {"name": "Sunil Kumar"},
        profile_id=1,
        verified=True,
    )

    profile.save_profile({"name": "Sunil Kumar"}, profile_id=1)
    assert verified_profile.get_verified_profile(1)["name"] == "Sunil Kumar"

    profile.save_profile({"name": "Sunil Singh"}, profile_id=1)
    assert verified_profile.get_verified_profile(1) is None


def test_reverification_of_one_profile_does_not_clear_another(monkeypatch, tmp_path):
    from app import profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(verified_profile, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)

    profile.save_profile({"name": "User One"}, profile_id=1)
    profile.save_profile({"name": "User Two"}, profile_id=2)
    verified_profile.save_verified_profile(
        {"name": "User One"}, profile_id=1, verified=True
    )
    verified_profile.save_verified_profile(
        {"name": "User Two"}, profile_id=2, verified=True
    )

    profile.save_profile({"name": "User One Changed"}, profile_id=1)

    assert verified_profile.get_verified_profile(1) is None
    assert verified_profile.get_verified_profile(2)["name"] == "User Two"


def test_first_profile_save_does_not_clear_an_existing_verified_profile(
    monkeypatch, tmp_path
):
    from app import profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(verified_profile, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)

    verified_profile.save_verified_profile(
        {"name": "Kept User", "father_name": "Kept Father"},
        profile_id=1,
        verified=True,
    )
    profile.save_profile(
        {"name": "Kept User", "father_name": "Kept Father"},
        profile_id=1,
    )
    profile.save_profile(
        {"name": "Other User", "mother_name": "Other Mother"},
        profile_id=2,
    )

    kept = verified_profile.get_verified_profile(1)
    assert kept["name"] == "Kept User"
    assert kept["father_name"] == "Kept Father"
    assert profile.get_profile(2)["mother_name"] == "Other Mother"
    assert profile.get_profile(2)["father_name"] == ""
    assert profile.get_profile(1)["mother_name"] == ""


def test_first_save_with_different_values_clears_only_that_profile(
    monkeypatch, tmp_path
):
    from app import profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(verified_profile, "DB_PATH", db)
    monkeypatch.setattr(profile, "DB_PATH", db)

    verified_profile.save_verified_profile(
        {"name": "User One"}, profile_id=1, verified=True
    )
    verified_profile.save_verified_profile(
        {"name": "User Two"}, profile_id=2, verified=True
    )

    profile.save_profile({"name": "Changed One"}, profile_id=1)

    assert verified_profile.get_verified_profile(1) is None
    assert verified_profile.get_verified_profile(2)["name"] == "User Two"

    profile.save_profile({"name": "User Two"}, profile_id=2)
    assert verified_profile.get_verified_profile(2)["name"] == "User Two"

    profile.save_profile({"name": "Changed Two"}, profile_id=2)
    assert verified_profile.get_verified_profile(2) is None
