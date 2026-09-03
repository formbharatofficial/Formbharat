from pathlib import Path

from io import BytesIO
from flask import Flask

from app import profile
from app.document_vault import register_document_vault
from app.profile_ui import register_profile_ui


def _client(monkeypatch, tmp_path):
    db = tmp_path / "formbharat.db"

    import app.profile as profile
    import app.document_vault as dv

    monkeypatch.setattr(profile, "DB_PATH", db)
    monkeypatch.setattr(dv, "DB_PATH", str(db))
    monkeypatch.setattr(dv, "STORAGE_DIR", str(tmp_path / "documents"))

    profile.save_profile({"name": "Media User"}, 1)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "formbharat_main_for_media_test",
        str(Path(__file__).resolve().parents[1] / "main.py")
    )
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
    return main_module.app.test_client()


def test_photo_and_signature_are_separate_media_types(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    for media_type, filename in [
        ("photo", "photo.jpg"),
        ("signature", "signature.png"),
    ]:
        response = client.post(
            f"/api/profile/1/media/{media_type}",
            data={
                "file": (
                    BytesIO(b"test-media"),
                    filename,
                    "image/jpeg" if filename.endswith(".jpg")
                    else "image/png",
                )
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert body["media_type"] == media_type
        assert body["profile_id"] == 1


def test_media_type_is_restricted(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    response = client.post(
        "/api/profile/1/media/video",
        data={"file": (BytesIO(b"x"), "x.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["success"] is False
