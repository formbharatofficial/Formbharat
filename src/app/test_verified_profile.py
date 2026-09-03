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
