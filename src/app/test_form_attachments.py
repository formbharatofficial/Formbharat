import io
import sqlite3
from pathlib import Path

from PIL import Image

from app.browser import BrowserSession
from app.document_fit import fit_image_copy
from app.fill_engine import fill_form
from app.form_attachments import plan_attachments


def _png(width, height):
    image = Image.effect_noise((width, height), 80).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _field(**values):
    field = {
        "name": "",
        "id": "",
        "type": "text",
        "label": "",
        "placeholder": "",
        "capture": "",
        "matched": True,
        "profile_value": "filled",
    }
    field.update(values)
    return field


def test_resized_copy_leaves_the_saved_file_unchanged(tmp_path):
    source = tmp_path / "photo.png"
    source.write_bytes(_png(1400, 1400))
    before = source.read_bytes()
    stamp = source.stat().st_mtime_ns
    output = tmp_path / "copy.jpg"

    size = fit_image_copy(before, output, max_width=400, max_height=400, max_bytes=80_000)

    assert source.read_bytes() == before
    assert source.stat().st_mtime_ns == stamp
    assert output.read_bytes().startswith(b"\xff\xd8\xff")
    assert size <= 80_000
    assert size < len(before)


def test_ordinary_photo_is_prepared_and_capture_or_payment_is_not(tmp_path):
    photo = _png(1000, 800)
    documents = [
        {"id": 1, "doc_type": "aadhaar", "filename": "aadhaar.png", "data": photo},
        {"id": 2, "doc_type": "photo", "filename": "face.png", "data": photo},
    ]
    planned = plan_attachments(
        [
            _field(id="photo", name="photo", type="file", label="Photograph"),
            _field(id="camera", name="camera", type="file", label="Photo", capture="environment"),
            _field(id="otp_file", name="otp_file", type="file", label="OTP upload"),
        ],
        documents,
        tmp_path / "copies",
        max_bytes=80_000,
    )

    ready = planned[0]
    assert ready["status"] == "ready"
    assert ready["doc_type"] == "photo"
    assert ready["bytes"] <= 80_000
    assert Path(ready["path"]).read_bytes().startswith(b"\xff\xd8\xff")
    assert planned[1]["status"] == "needs_user"
    assert planned[2]["status"] == "needs_user"
    assert "path" not in planned[1]


def test_payment_password_and_submit_are_not_filled():
    html = """
    <form>
      <input id="fee" name="fee" type="text">
      <input id="pwd" name="pwd" type="password">
      <input id="go" name="go" type="submit" value="Submit">
    </form>
    """
    result = fill_form(html, [
        _field(id="fee", name="fee", label="Payment", profile_value="500"),
        _field(id="pwd", name="pwd", type="password", profile_value="secret"),
        _field(id="go", name="go", type="submit", profile_value="Submit"),
    ])

    assert result["filled"] == []
    assert "500" not in result["html"]
    assert "secret" not in result["html"]


def test_capture_control_does_not_receive_the_prepared_file(tmp_path):
    session = BrowserSession()
    prepared = tmp_path / "copy.jpg"
    prepared.write_bytes(b"\xff\xd8\xff")

    class Page:
        def evaluate(self, script, arg):
            return {"index": 0, "capture": "environment", "type": "file"}

        def locator(self, selector):
            raise AssertionError("capture control must not receive a file")

    session._page = Page()
    item = {
        "status": "ready",
        "id": "camera",
        "name": "camera",
        "field": "camera",
        "path": str(prepared),
    }
    assert session.attach_files([item]) == []
    assert item["status"] == "needs_user"


def test_ordinary_file_input_receives_the_prepared_copy(tmp_path):
    session = BrowserSession()
    prepared = tmp_path / "copy.jpg"
    prepared.write_bytes(b"\xff\xd8\xff")

    class Page:
        def __init__(self):
            self.paths = []

        def evaluate(self, script, arg):
            return {"index": 0, "capture": "", "type": "file"}

        def locator(self, selector):
            assert selector == 'input[type="file"]'
            return self

        def nth(self, index):
            assert index == 0
            return self

        def set_input_files(self, path):
            self.paths.append(path)

    page = Page()
    session._page = page
    item = {
        "status": "ready",
        "id": "photo",
        "name": "photo",
        "field": "photo",
        "path": str(prepared),
    }

    assert session.attach_files([item]) == ["photo"]
    assert item["status"] == "attached"
    assert page.paths == [str(prepared)]


def test_saved_profile_photo_is_prepared_without_changing_the_vault(tmp_path, monkeypatch):
    from app import document_vault, profile, verified_profile
    from app.rendered_assist import assist_verified_profile

    database = tmp_path / "formbharat.db"
    storage = tmp_path / "documents"
    storage.mkdir()
    monkeypatch.setattr(profile, "DB_PATH", database)
    monkeypatch.setattr(verified_profile, "DB_PATH", database)
    monkeypatch.setattr(document_vault, "DB_PATH", str(database))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(storage))
    verified_profile.save_verified_profile(
        {"name": "Sunil Kumar"},
        profile_id=1,
        verified=True,
    )
    original = _png(1200, 1200)
    stored = storage / "face.png"
    stored.write_bytes(original)
    stamp = stored.stat().st_mtime_ns
    document_vault.init_db()
    connection = sqlite3.connect(database)
    connection.execute(
        """
        INSERT INTO documents (
            profile_id, doc_type, original_filename, storage_path,
            created_at, updated_at, document_reference
        ) VALUES (1, 'photo', 'face.png', ?, 't', 't', 'DOC-TESTPHOTO')
        """,
        (str(stored),),
    )
    connection.commit()
    connection.close()

    class Opener:
        def open(self, url):
            return """
            <form>
              <label for="full_name">Full Name</label>
              <input id="full_name" name="full_name" type="text">
              <label for="photo">Photograph</label>
              <input id="photo" name="photo" type="file">
              <label for="pwd">Password</label>
              <input id="pwd" name="pwd" type="password">
              <button type="submit">Submit</button>
            </form>
            """

    result = assist_verified_profile(Opener(), "file:///C:/form.html", 1)

    assert result["submitted"] is False
    assert result["filled"][0]["value"] == "Sunil Kumar"
    assert result["attachments"][0]["status"] == "ready"
    assert result["attachments"][0]["bytes"] < len(original)
    assert "path" not in result["attachments"][0]
    assert stored.read_bytes() == original
    assert stored.stat().st_mtime_ns == stamp
    assert "secret" not in result["filled_html"]
