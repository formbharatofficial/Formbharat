import io
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from app.browser import Browser

PAGE_ONE = """<!DOCTYPE html>
<html><body>
<form onsubmit="window.__submitted = true; return false;">
  <label for="full_name">Full Name</label>
  <input id="full_name" name="full_name" type="text">
  <label for="email">Email</label>
  <input id="email" name="email" type="email">
  <label for="dob">Date of Birth</label>
  <input id="dob" name="dob" type="date">
  <label for="address">Address</label>
  <textarea id="address" name="address"></textarea>
  <label for="pincode">Pincode</label>
  <input id="pincode" name="pincode" type="text">
  <label for="father_name">Father Name</label>
  <input id="father_name" name="father_name" type="text">
  <label for="mother_name">Mother Name</label>
  <input id="mother_name" name="mother_name" type="text">
  <label for="guardian_name">Guardian Name</label>
  <input id="guardian_name" name="guardian_name" type="text">
  <label for="mobile">Mobile</label>
  <input id="mobile" name="mobile" type="tel">
  <label for="photo">Photograph</label>
  <input id="photo" name="photo" type="file" accept=".jpg,.jpeg,image/jpeg" data-max-bytes="350000">
  <label for="signature">Signature</label>
  <input id="signature" name="signature" type="file" accept=".jpg,.jpeg,image/jpeg" data-max-bytes="350000">
  <label for="identity">Identity document</label>
  <input id="identity" name="identity" type="file" accept=".pdf,application/pdf" data-max-bytes="200000">
  <label for="png_only">Photograph scan</label>
  <input id="png_only" name="png_only" type="file" accept=".png">
  <label for="tiny_photo">Photograph extra</label>
  <input id="tiny_photo" name="tiny_photo" type="file" accept=".jpg,.jpeg,image/jpeg" data-max-bytes="50">
  <label for="crop_photo">Photo</label>
  <input id="crop_photo" name="crop_photo" type="file" accept="image/*" capture="environment">
  <label for="pwd">Password</label>
  <input id="pwd" name="pwd" type="password">
  <label for="otp">OTP</label>
  <input id="otp" name="otp" type="text">
  <label for="captcha">Captcha</label>
  <input id="captcha" name="captcha" type="text">
  <label for="fee">Payment</label>
  <input id="fee" name="fee" type="text">
  <button type="submit" id="submit_application" name="submit_application">Submit</button>
</form>
</body></html>
"""

PAGE_TWO = """<!DOCTYPE html>
<html><body>
<form onsubmit="window.__submitted = true; return false;">
  <label for="state">State</label>
  <input id="state" name="state" type="text">
  <label for="district">District</label>
  <input id="district" name="district" type="text">
  <label for="notes">Random Unknown Field</label>
  <input id="notes" name="notes" type="text">
  <label for="otp">OTP</label>
  <input id="otp" name="otp" type="text">
  <button type="submit" id="submit_application">Submit</button>
</form>
</body></html>
"""

PROFILE = {
    "name": "Sunil Kumar",
    "email": "sunil@example.com",
    "dob": "1990-01-15",
    "address": "12 Civil Lines",
    "pincode": "211001",
    "father_name": "Ajit Kumar",
    "mother_name": "Sita Devi",
    "guardian_name": "",
    "mobile": "12345",
    "state": "Uttar Pradesh",
    "district": "Prayagraj",
}


def _png(width, height):
    image = Image.effect_noise((width, height), 80).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _store(connection, storage, doc_type, filename, data):
    path = storage / filename
    path.write_bytes(data)
    connection.execute(
        """
        INSERT INTO documents (
            profile_id, doc_type, original_filename, storage_path,
            created_at, updated_at, document_reference
        ) VALUES (1, ?, ?, ?, 't', 't', ?)
        """,
        (doc_type, filename, str(path), f"DOC-{doc_type.upper()}"),
    )
    return path


def _snapshot(page):
    return page.evaluate(
        """() => {
            const value = (id) => {
                const node = document.getElementById(id);
                return node ? node.value : null;
            };
            const file = (id) => {
                const node = document.getElementById(id);
                if (!node || !node.files) return null;
                const first = node.files[0];
                return {
                    count: node.files.length,
                    name: first ? first.name : "",
                    size: first ? first.size : 0,
                    type: first ? first.type : ""
                };
            };
            return {
                href: location.href,
                submitted: window.__submitted === true,
                full_name: value("full_name"),
                email: value("email"),
                dob: value("dob"),
                address: value("address"),
                pincode: value("pincode"),
                father_name: value("father_name"),
                mother_name: value("mother_name"),
                guardian_name: value("guardian_name"),
                mobile: value("mobile"),
                pwd: value("pwd"),
                otp: value("otp"),
                captcha: value("captcha"),
                fee: value("fee"),
                state: value("state"),
                district: value("district"),
                notes: value("notes"),
                photo: file("photo"),
                signature: file("signature"),
                identity: file("identity"),
                png_only: file("png_only"),
                tiny_photo: file("tiny_photo"),
                crop_photo: file("crop_photo")
            };
        }"""
    )


def test_edge_fills_one_local_page_and_only_opens_the_next_page_when_asked(tmp_path, monkeypatch):
    pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
    if not Path(Browser._EDGE_EXECUTABLE).exists():
        pytest.skip("Microsoft Edge is not installed")

    from app import document_vault, profile, verified_profile
    from app.browser import BrowserSession
    from app.rendered_assist import assist_verified_profile

    database = tmp_path / "formbharat.db"
    storage = tmp_path / "documents"
    storage.mkdir()
    monkeypatch.setattr(profile, "DB_PATH", database)
    monkeypatch.setattr(verified_profile, "DB_PATH", database)
    monkeypatch.setattr(document_vault, "DB_PATH", str(database))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(storage))
    verified_profile.save_verified_profile(PROFILE, profile_id=1, verified=False)
    photo = _png(1100, 900)
    signature = _png(900, 300)
    identity = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    document_vault.init_db()
    connection = sqlite3.connect(database)
    photo_path = _store(connection, storage, "photo", "face.png", photo)
    signature_path = _store(connection, storage, "signature", "sign.png", signature)
    identity_path = _store(connection, storage, "identity", "proof.pdf", identity)
    _store(connection, storage, "aadhaar", "aadhaar.png", _png(400, 400))
    connection.commit()
    connection.close()
    photo_stamp = photo_path.stat().st_mtime_ns
    signature_stamp = signature_path.stat().st_mtime_ns
    identity_stamp = identity_path.stat().st_mtime_ns

    page_one = tmp_path / "page-one.html"
    page_two = tmp_path / "page-two.html"
    page_one.write_text(PAGE_ONE, encoding="utf-8")
    page_two.write_text(PAGE_TWO, encoding="utf-8")
    session = BrowserSession()
    try:
        unverified = assist_verified_profile(session, page_one.as_uri(), 1)
        blank = _snapshot(session._page)
        assert unverified["verified_profile"] is False
        assert unverified["filled"] == []
        assert unverified["attachments"] == []
        assert blank["full_name"] == ""
        assert blank["photo"]["count"] == 0
        assert blank["submitted"] is False

        verified_profile.save_verified_profile(PROFILE, profile_id=1, verified=True)
        assisted = assist_verified_profile(session, page_one.as_uri(), 1)
        live = _snapshot(session._page)
        by_field = {item["field"]: item for item in assisted["attachments"]}

        assert assisted["submitted"] is False
        assert assisted["verified_profile"] is True
        filled = {item["field"]: item["value"] for item in assisted["filled"]}
        assert filled["full_name"] == "Sunil Kumar"
        assert filled["email"] == "sunil@example.com"
        assert filled["dob"] == "1990-01-15"
        assert filled["address"] == "12 Civil Lines"
        assert filled["pincode"] == "211001"
        assert filled["father_name"] == "Ajit Kumar"
        assert filled["mother_name"] == "Sita Devi"
        assert "guardian_name" not in filled
        assert "mobile" not in filled
        assert "pwd" not in filled
        assert "otp" not in filled
        assert "captcha" not in filled
        assert "fee" not in filled
        assert "submit_application" not in filled

        assert live["full_name"] == "Sunil Kumar"
        assert live["email"] == "sunil@example.com"
        assert live["dob"] == "1990-01-15"
        assert live["address"] == "12 Civil Lines"
        assert live["pincode"] == "211001"
        assert live["father_name"] == "Ajit Kumar"
        assert live["mother_name"] == "Sita Devi"
        assert live["guardian_name"] == ""
        assert live["mobile"] == ""
        assert live["pwd"] == ""
        assert live["otp"] == ""
        assert live["captcha"] == ""
        assert live["fee"] == ""
        assert live["submitted"] is False
        assert live["href"] == page_one.as_uri()

        assert by_field["photo"]["status"] == "attached"
        assert by_field["photo"]["doc_type"] == "photo"
        assert by_field["photo"]["bytes"] <= 350000
        assert live["photo"]["count"] == 1
        assert live["photo"]["name"].endswith(".jpg")
        assert 0 < live["photo"]["size"] <= 350000
        assert live["photo"]["size"] < len(photo)
        assert by_field["signature"]["doc_type"] == "signature"
        assert by_field["signature"]["status"] == "attached"
        assert live["signature"]["count"] == 1
        assert 0 < live["signature"]["size"] <= 350000
        assert live["signature"]["size"] < len(signature)
        assert by_field["identity"]["doc_type"] == "identity"
        assert by_field["identity"]["status"] == "attached"
        assert live["identity"]["name"].endswith(".pdf"), live["identity"]
        assert live["identity"]["size"] == len(identity), live["identity"]
        assert by_field["png_only"]["status"] == "needs_user"
        assert "prepared file type" in by_field["png_only"]["reason"]
        assert live["png_only"]["count"] == 0
        assert by_field["tiny_photo"]["status"] == "needs_user"
        assert "larger than this field allows" in by_field["tiny_photo"]["reason"]
        assert live["tiny_photo"]["count"] == 0
        assert by_field["crop_photo"]["status"] == "needs_user"
        assert live["crop_photo"]["count"] == 0

        assert photo_path.read_bytes() == photo
        assert signature_path.read_bytes() == signature
        assert identity_path.read_bytes() == identity
        assert photo_path.stat().st_mtime_ns == photo_stamp
        assert signature_path.stat().st_mtime_ns == signature_stamp
        assert identity_path.stat().st_mtime_ns == identity_stamp

        reread = assist_verified_profile(session, page_two.as_uri(), 1, reread=True)
        stayed = _snapshot(session._page)
        reread_filled = {item["field"] for item in reread["filled"]}
        assert session.url == page_one.as_uri()
        assert stayed["href"] == page_one.as_uri()
        assert stayed["state"] is None
        assert stayed["full_name"] == "Sunil Kumar"
        assert "state" not in reread_filled
        assert "full_name" in reread_filled

        second = assist_verified_profile(session, page_two.as_uri(), 1)
        page_two_live = _snapshot(session._page)
        second_filled = {item["field"]: item["value"] for item in second["filled"]}
        assert second["submitted"] is False
        assert second_filled == {"state": "Uttar Pradesh", "district": "Prayagraj"}
        assert page_two_live["href"] == page_two.as_uri()
        assert page_two_live["state"] == "Uttar Pradesh"
        assert page_two_live["district"] == "Prayagraj"
        assert page_two_live["notes"] == ""
        assert page_two_live["otp"] == ""
        assert page_two_live["submitted"] is False
    finally:
        session.close()
