import sqlite3

import pytest

import app.application_tracker as tracker


def _use_db(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "applications.db")
    tracker.init_application_tracker_db()


def test_application_tables_can_be_created(tmp_path, monkeypatch):
    db = tmp_path / "applications.db"
    monkeypatch.setattr(tracker, "DB_PATH", db)

    tracker.init_application_tracker_db()

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()

    assert ("application_status_history",) in rows
    assert ("applications",) in rows


def test_create_and_get_application(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)

    item = tracker.create_application(
        profile_id=1,
        title="SSC CGL",
        organization="SSC",
        vacancy_id=4,
        note="Saved from vacancy list",
    )

    assert item["profile_id"] == 1
    assert item["vacancy_id"] == 4
    assert item["title"] == "SSC CGL"
    assert item["organization"] == "SSC"
    assert item["status"] == "draft"
    assert tracker.get_application(item["id"]) == item

    history = tracker.list_application_history(item["id"])
    assert len(history) == 1
    assert history[0]["status"] == "draft"
    assert history[0]["note"] == "Saved from vacancy list"


def test_invalid_application_is_rejected(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="profile_id"):
        tracker.create_application(profile_id=True, title="Exam")
    with pytest.raises(ValueError, match="profile_id"):
        tracker.create_application(profile_id=6, title="Exam")
    with pytest.raises(ValueError, match="title"):
        tracker.create_application(profile_id=1, title="  ")
    with pytest.raises(ValueError, match="status"):
        tracker.create_application(profile_id=1, title="Exam", status="notified")
    with pytest.raises(ValueError, match="vacancy_id"):
        tracker.create_application(profile_id=1, title="Exam", vacancy_id=0)


def test_list_applications_by_profile_and_status(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)

    first = tracker.create_application(1, "First Exam")
    tracker.create_application(1, "Second Exam", status="submitted")
    tracker.create_application(2, "Other Profile")

    listed = tracker.list_applications(1)
    assert [item["id"] for item in listed] == [
        listed[0]["id"],
        first["id"],
    ]
    assert [item["title"] for item in listed] == ["Second Exam", "First Exam"]
    assert tracker.list_applications(1, status="submitted")[0]["title"] == "Second Exam"
    assert tracker.list_applications(2)[0]["title"] == "Other Profile"


def test_status_change_is_stored_in_history(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)

    item = tracker.create_application(1, "Railway Exam")
    updated = tracker.update_application_status(
        item["id"],
        "in_progress",
        note="Started filling",
    )
    submitted = tracker.update_application_status(item["id"], "submitted")
    unchanged = tracker.update_application_status(item["id"], "submitted")

    assert updated["status"] == "in_progress"
    assert submitted["status"] == "submitted"
    assert unchanged == submitted
    assert tracker.update_application_status(999999, "draft") is None

    history = tracker.list_application_history(item["id"])
    assert [entry["status"] for entry in history] == [
        "draft",
        "in_progress",
        "submitted",
    ]
    assert history[1]["note"] == "Started filling"
    assert history[2]["note"] == ""
