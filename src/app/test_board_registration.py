import base64
import importlib.util
import sqlite3
from pathlib import Path

import pytest

from app.rendered_assist import assist_page_url


def _client(monkeypatch, tmp_path):
    import app.board_registration as registration
    import app.document_vault as document_vault
    import app.vacancy as vacancy
    from app import profile, verified_profile

    database = tmp_path / "board.db"
    storage = tmp_path / "documents"
    monkeypatch.setenv("FORMBHARAT_DATABASE_PATH", str(database))
    monkeypatch.setenv("FORMBHARAT_STORAGE_DIR", str(storage))
    monkeypatch.delenv("FORMBHARAT_DOCUMENT_KEY", raising=False)
    monkeypatch.delenv("FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION", raising=False)
    monkeypatch.setattr(vacancy, "DB_PATH", database)
    monkeypatch.setattr(profile, "DB_PATH", database)
    monkeypatch.setattr(verified_profile, "DB_PATH", database)
    monkeypatch.setattr(document_vault, "DB_PATH", str(database))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(storage))
    registration.init_board_registration_db()

    spec = importlib.util.spec_from_file_location(
        "formbharat_main_for_board_registration",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded.app.config["TESTING"] = True
    return loaded.app.test_client(), database


def _count(database):
    connection = sqlite3.connect(database)
    try:
        return connection.execute(
            "SELECT COUNT(*) FROM board_registration_records"
        ).fetchone()[0]
    finally:
        connection.close()


def _stored_number(database):
    connection = sqlite3.connect(database)
    try:
        row = connection.execute(
            "SELECT registration_number FROM board_registration_records"
        ).fetchone()
    finally:
        connection.close()
    return "" if row is None else row[0]


def _vacancy(client, board, title="Notice"):
    created = client.post("/api/vacancies", json={
        "title": title,
        "organization": "Board",
        "official_link": "https://example.gov.in/notice",
        "registration_board": board,
    })
    assert created.status_code == 201
    return created.get_json()["vacancy"]["id"]


def _save(client, profile_id=1, **extra):
    payload = {
        "board": "ssc",
        "account_path": "existing",
        "registration_number": "SSCUSER1001",
        "consent": True,
        "consent_language": "en",
    }
    payload.update(extra)
    return client.post(
        f"/api/board-registration/records/{profile_id}",
        json=payload,
    )


def test_ssc_and_rrb_configurations_stay_distinct(monkeypatch, tmp_path):
    client, _database = _client(monkeypatch, tmp_path)
    body = client.get("/api/board-registration/boards").get_json()
    boards = {item["board"]: item for item in body["boards"]}

    assert boards["ssc"]["record_type"] == "ssc_otr"
    assert boards["rrb"]["record_type"] == "rrb_candidate_account"
    assert boards["ssc"]["record_type"] != boards["rrb"]["record_type"]
    assert "One Time Registration" in boards["ssc"]["account_name_en"]
    assert boards["rrb"]["account_name_en"] == "Candidate Account"
    assert boards["ssc"]["portal_url"] != boards["rrb"]["portal_url"]
    assert boards["ssc"]["live_portal_assist"] == "unavailable"
    assert boards["rrb"]["live_portal_assist"] == "unavailable"
    assert [field["key"] for field in boards["ssc"]["fields"]] != [
        field["key"] for field in boards["rrb"]["fields"]
    ]


def test_requirement_uses_metadata_and_skips_when_none(monkeypatch, tmp_path):
    client, _database = _client(monkeypatch, tmp_path)
    skipped = _vacancy(client, "none", title="SSC CGL 2026")
    required = _vacancy(client, "ssc", title="Clerk")
    railway = _vacancy(client, "rrb", title="NTPC")
    unknown = _vacancy(client, "", title="SSC CGL without metadata")

    skip = client.get(f"/api/board-registration/requirement?vacancy_id={skipped}").get_json()
    ssc = client.get(f"/api/board-registration/requirement?vacancy_id={required}").get_json()
    rrb = client.get(f"/api/board-registration/requirement?vacancy_id={railway}").get_json()
    ask = client.get(f"/api/board-registration/requirement?vacancy_id={unknown}").get_json()

    assert skip["requirement"] == {"state": "skip", "board": "", "record_type": ""}
    assert ssc["requirement"]["state"] == "required"
    assert ssc["requirement"]["record_type"] == "ssc_otr"
    assert rrb["requirement"]["record_type"] == "rrb_candidate_account"
    assert ask["requirement"]["state"] == "ask"
    assert ask["requirement"]["board"] == ""


def test_review_shows_missing_and_conflicting_profile_data(monkeypatch, tmp_path):
    from app import profile, verified_profile

    client, _database = _client(monkeypatch, tmp_path)
    profile.save_profile({
        "name": "Raw Name",
        "father_name": "Father",
        "mother_name": "Mother",
        "dob": "1991-01-01",
        "mobile": "9876543210",
        "email": "user@example.com",
    }, 1)
    verified_profile.save_verified_profile({
        "name": "Verified Name",
        "father_name": "Father",
        "mother_name": "Mother",
        "dob": "1991-01-01",
        "mobile": "9876543210",
        "email": "user@example.com",
    }, 1, verified=True)

    review = client.get("/api/board-registration/review?profile_id=1&board=ssc").get_json()
    conflict_keys = [item["key"] for item in review["conflicts"]]
    copy_keys = [item["key"] for item in review["copy_fields"]]
    missing_keys = [item["key"] for item in review["missing"]]

    assert review["profile_state"] == "incomplete"
    assert "name" in conflict_keys
    assert "name" not in copy_keys
    assert "category" in missing_keys
    assert "aadhaar" not in copy_keys

    profile.save_profile({"name": "Second"}, 2)
    unverified = client.get("/api/board-registration/review?profile_id=2&board=rrb").get_json()
    assert unverified["profile_state"] == "unverified"
    assert unverified["copy_fields"] == []
    assert unverified["record_type"] == "rrb_candidate_account"


def test_declining_consent_does_not_persist_a_record(monkeypatch, tmp_path):
    client, database = _client(monkeypatch, tmp_path)
    declined = client.post("/api/board-registration/records/1", json={
        "board": "ssc",
        "consent": False,
        "registration_number": "SHOULDNOTSAVE1",
        "password": "hidden-secret",
    })
    assert declined.status_code == 400
    assert "hidden-secret" not in declined.get_data(as_text=True)
    assert _count(database) == 0

    clean_decline = client.post("/api/board-registration/records/1", json={
        "board": "rrb",
        "consent": False,
        "registration_number": "SHOULDNOTSAVE1",
    })
    assert clean_decline.status_code == 200
    assert clean_decline.get_json()["saved"] is False
    assert _count(database) == 0
    assert "SHOULDNOTSAVE1" not in _stored_number(database)


def test_consent_saves_only_intended_fields_and_rejects_secrets(monkeypatch, tmp_path):
    client, database = _client(monkeypatch, tmp_path)
    rejected = _save(client, otp="123456", captcha="ab12", cookie="sid", token="auth", aadhaar="9999")
    assert rejected.status_code == 400
    assert _count(database) == 0
    assert "123456" not in rejected.get_data(as_text=True)

    saved = _save(client, board="rrb", account_path="new", registration_number="RRBUSER2002")
    assert saved.status_code == 201
    record = saved.get_json()["record"]
    assert record["board"] == "rrb"
    assert record["record_type"] == "rrb_candidate_account"
    assert record["status"] == "user_confirmed"
    assert record["confirmation"] == "user_confirmed_not_independently_verified"
    assert record["registration_number"] == "RRBUSER2002"
    assert record["number_storage"] == "plaintext"
    assert "password" not in record
    connection = sqlite3.connect(database)
    try:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(board_registration_records)")]
    finally:
        connection.close()
    assert "password" not in columns
    assert "otp" not in columns


def test_other_user_cannot_read_or_delete_a_record(monkeypatch, tmp_path):
    client, database = _client(monkeypatch, tmp_path)
    saved = _save(client)
    record_id = saved.get_json()["record"]["id"]

    with client.session_transaction() as session:
        session["user_id"] = 2
    hidden = client.get("/api/board-registration/records/1")
    assert hidden.status_code == 403
    denied = client.delete(f"/api/board-registration/records/1/{record_id}")
    assert denied.status_code == 403
    assert _count(database) == 1

    with client.session_transaction() as session:
        session.clear()
    visible = client.get("/api/board-registration/records/1")
    assert visible.status_code == 200
    assert visible.get_json()["records"][0]["registration_number"] == "SSCUSER1001"


def test_invalid_board_and_number_are_rejected_without_echoing_the_number(monkeypatch, tmp_path):
    client, database = _client(monkeypatch, tmp_path)
    bad_board = _save(client, board="upsssc")
    assert bad_board.status_code == 400
    bad_number = _save(client, registration_number="this number is not an identifier")
    assert bad_number.status_code == 400
    assert "this number is not an identifier" not in bad_number.get_data(as_text=True)
    assert _count(database) == 0

    vacancy = client.post("/api/vacancies", json={
        "title": "Bad board",
        "organization": "Board",
        "official_link": "https://example.gov.in/notice",
        "registration_board": "upsssc",
    })
    assert vacancy.status_code == 400


def test_duplicate_replace_and_delete(monkeypatch, tmp_path):
    client, database = _client(monkeypatch, tmp_path)
    first = _save(client)
    assert first.status_code == 201
    record_id = first.get_json()["record"]["id"]
    duplicate = _save(client, registration_number="SSCUSER1002")
    assert duplicate.status_code == 409
    assert _count(database) == 1

    replaced = _save(client, registration_number="SSCUSER1002", replace=True)
    assert replaced.status_code == 201
    assert _count(database) == 1
    assert replaced.get_json()["record"]["id"] == record_id
    assert replaced.get_json()["record"]["registration_number"] == "SSCUSER1002"

    other_board = _save(client, board="rrb", registration_number="RRBUSER3003")
    assert other_board.status_code == 201
    assert _count(database) == 2

    removed = client.delete(f"/api/board-registration/records/1/{record_id}")
    assert removed.status_code == 200
    assert _count(database) == 1
    missing = client.delete(f"/api/board-registration/records/1/{record_id}")
    assert missing.status_code == 404


def test_encryption_is_claimed_only_when_the_number_is_protected(monkeypatch, tmp_path):
    client, database = _client(monkeypatch, tmp_path)
    monkeypatch.setenv("FORMBHARAT_DOCUMENT_KEY", "11" * 32)
    saved = _save(client)
    assert saved.status_code == 201
    assert saved.get_json()["record"]["number_storage"] == "encrypted"
    assert saved.get_json()["record"]["registration_number"] == "SSCUSER1001"
    stored = _stored_number(database)
    assert stored.startswith("FBTEXT1:")
    assert "SSCUSER1001" not in stored

    monkeypatch.setenv("FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION", "1")
    monkeypatch.delenv("FORMBHARAT_DOCUMENT_KEY", raising=False)
    blocked = _save(client, board="rrb", registration_number="RRBUSER4004")
    assert blocked.status_code == 503
    assert _count(database) == 1


def test_otr_sits_inside_the_job_that_needs_it(monkeypatch, tmp_path):
    client, _database = _client(monkeypatch, tmp_path)
    ssc_id = _vacancy(client, "ssc", title="SSC CGL 2026")
    rrb_id = _vacancy(client, "rrb", title="RRB NTPC 2026")
    skip_id = _vacancy(client, "none", title="Local Clerk")
    ssc = client.get(f"/job/{ssc_id}").get_data(as_text=True)
    rrb = client.get(f"/job/{rrb_id}").get_data(as_text=True)
    skip = client.get(f"/job/{skip_id}").get_data(as_text=True)
    other = client.get("/other-forms").get_data(as_text=True)
    island = client.get("/board-registration?lang=hi")
    ssc_old = client.get(f"/board-registration?vacancy_id={ssc_id}")
    skip_old = client.get(f"/board-registration?vacancy_id={skip_id}")
    skip_account = client.get(f"/apply/{skip_id}/account")

    assert island.status_code in (301, 302)
    assert "/vacancies" in (island.headers.get("Location") or "")
    assert ssc_old.status_code in (301, 302)
    assert f"/apply/{ssc_id}/account" in (ssc_old.headers.get("Location") or "")
    assert skip_old.status_code in (301, 302)
    assert f"/apply/{skip_id}/check" in (skip_old.headers.get("Location") or "")
    assert skip_account.status_code in (301, 302)
    assert f"/apply/{skip_id}/check" in (skip_account.headers.get("Location") or "")

    assert ssc.startswith("<!DOCTYPE html>") or '<html lang="hi">' in ssc
    assert "ऑटो-फिल से भरना चाहते हैं" in ssc
    assert "ऐप भरे" not in ssc
    assert "One Time Registration" not in ssc
    assert "Candidate Account" not in ssc
    assert "innerHTML" not in ssc
    assert "window.open" not in ssc
    assert "सरकारी साइट अभी नहीं खुलेगी" in ssc
    assert f"/apply/{ssc_id}/account" in ssc
    assert f"/apply/{ssc_id}/check" not in ssc

    assert "ऐप भरे" not in rrb
    assert "One Time Registration" not in rrb
    assert "Candidate Account" not in rrb
    assert f"/apply/{rrb_id}/account" in rrb

    assert "One Time Registration" not in skip
    assert "Candidate Account" not in skip
    assert f"/apply/{skip_id}/check" in skip
    assert f"/apply/{skip_id}/account" not in skip

    from app.accounts import register_user

    user_id = register_user("flow@example.com", "preview12", "Flow User", "9876543210")
    with client.session_transaction() as session:
        session["user_id"] = user_id
    ssc_ask = client.get(f"/apply/{ssc_id}/account?path=ask").get_data(as_text=True)
    rrb_ask = client.get(f"/apply/{rrb_id}/account?path=ask").get_data(as_text=True)
    assert "One Time Registration (OTR)" in ssc_ask
    assert "ssc.gov.in" in ssc_ask
    assert "क्या आपके पास" in ssc_ask
    assert "Candidate Account" in rrb_ask
    assert "rrbapply.gov.in" in rrb_ask
    assert "SSC One Time Registration नहीं" in rrb_ask

    assert "One Time Registration" not in other
    assert "Candidate Account" not in other
    assert "OTR" not in other
    assert "/board-registration" not in other
    assert "rrbapply.gov.in" not in other
    assert assist_page_url("https://ssc.gov.in/") == "https://ssc.gov.in/"
    assert assist_page_url("https://www.rrbapply.gov.in/") == "https://www.rrbapply.gov.in/"
    with pytest.raises(ValueError, match="form page"):
        assist_page_url("javascript:alert(1)")


def test_missing_otr_uses_profile_then_asks_before_save(monkeypatch, tmp_path):
    from app.accounts import register_user
    from app import profile

    client, database = _client(monkeypatch, tmp_path)
    ssc_id = _vacancy(client, "ssc", title="SSC CGL 2026")
    user_id = register_user("otr@example.com", "preview12", "Preview User", "9876543210")
    with client.session_transaction() as session:
        session["user_id"] = user_id
    client.get(f"/apply/{ssc_id}/account")
    profile.save_profile({"name": "Preview User", "mobile": "9876543210"}, 1)

    ask = client.get(f"/apply/{ssc_id}/account").get_data(as_text=True)
    prepare = client.get(f"/apply/{ssc_id}/account?path=new").get_data(as_text=True)
    handoff = client.get(f"/apply/{ssc_id}/account?path=handoff").get_data(as_text=True)
    save = client.get(f"/apply/{ssc_id}/account?path=save")
    page = save.get_data(as_text=True)

    assert "क्या आपके पास" in ask
    assert "प्रोफाइल से नया बनाओ" in ask
    assert "Preview User" in prepare
    assert "OTP और CAPTCHA आप डालोगे" in prepare
    assert "Aap hi CAPTCHA daloge" in handoff
    assert "OTP nahi bhejta" in handoff
    assert "ban chuka hai" in handoff
    assert "सेव की अनुमति" in handoff
    assert "क्या नंबर सेव करें?" in page
    assert "नहीं, सेव मत करो" in page
    assert "innerHTML" not in page

    token = page.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    declined = client.post(f"/apply/{ssc_id}/account", data={
        "csrf_token": token,
        "account_path": "new",
        "registration_number": "SSCUSER1001",
    })
    assert declined.status_code == 200
    assert _count(database) == 0

    kept = client.post(f"/apply/{ssc_id}/account", data={
        "csrf_token": token,
        "account_path": "new",
        "registration_number": "SSCUSER1001",
        "consent": "yes",
    }, follow_redirects=False)
    assert kept.status_code in (301, 302)
    assert _count(database) == 1


def _login(client, email):
    from app.accounts import register_user

    user_id = register_user(email, "preview12", "Flow User", "9876543210")
    with client.session_transaction() as session:
        session["user_id"] = user_id
    return user_id


def _csrf(page):
    return page.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]


def test_official_page_is_filled_and_not_submitted(monkeypatch, tmp_path):
    from app import profile
    from app.fill_fee import has_paid_fee
    import app.rendered_assist as rendered_assist
    from app.browser import BrowserSession

    client, _database = _client(monkeypatch, tmp_path)
    job_id = _vacancy(client, "rrb", title="RRB NTPC 2026")
    pdf = client.post("/api/vacancies", json={
        "title": "SSC notice pdf",
        "organization": "SSC",
        "official_link": "https://ssc.gov.in/notice.pdf",
        "registration_board": "ssc",
    })
    assert pdf.status_code == 201
    pdf_id = pdf.get_json()["vacancy"]["id"]
    _login(client, "fill@example.com")
    client.get(f"/apply/{job_id}/account")
    profile.save_profile({"name": "Flow User", "mobile": "9876543210"}, 1)

    before = client.get(f"/apply/{job_id}/pay").get_data(as_text=True)
    assert "सरकारी साइट पर भरो" in before
    assert "पुराना शुरू पन्ना" in before
    opened = client.post(f"/apply/{job_id}/pay", data={
        "csrf_token": _csrf(before),
        "method": "upi",
    })
    pay = opened.get_data(as_text=True)
    assert "सरकारी साइट पर भरो" in pay
    assert "Submit नहीं होगा" in pay

    seen = {}

    def fake_assist(payload, sessions, factory):
        seen["payload"] = dict(payload)
        seen["factory"] = factory
        return {
            "success": True,
            "submitted": False,
            "filled_count": 2,
            "skipped_count": 1,
            "verified_profile": True,
            "review": {
                "submitted": False,
                "proposed": [{
                    "profile_key": "name",
                    "field": "full_name",
                    "value": "Secret Value",
                }],
            },
            "attachments": [
                {"status": "attached"},
                {"status": "needs_user"},
            ],
        }

    monkeypatch.setattr(rendered_assist, "run_local_assist", fake_assist)
    filled = client.post(f"/apply/{job_id}/fill", data={"csrf_token": _csrf(pay)})
    page = filled.get_data(as_text=True)
    assert filled.status_code == 200
    assert "2 खाने भरे" in page
    assert "Submit नहीं हुआ" in page
    assert "Secret Value" not in page
    assert "paid नहीं लिखा गया" in page
    assert seen["payload"]["url"] == "https://example.gov.in/notice"
    assert seen["payload"]["action"] == "open"
    assert seen["factory"] is BrowserSession
    assert has_paid_fee(job_id, 1) is False

    pdf_pay = client.get(f"/apply/{pdf_id}/pay").get_data(as_text=True)
    client.post(f"/apply/{pdf_id}/pay", data={
        "csrf_token": _csrf(pdf_pay),
        "method": "upi",
    })
    pdf_again = client.get(f"/apply/{pdf_id}/pay").get_data(as_text=True)
    client.post(f"/apply/{pdf_id}/fill", data={"csrf_token": _csrf(pdf_again)})
    assert seen["payload"]["url"] == "https://ssc.gov.in/candidate-portal/one-time-registration"
    assert has_paid_fee(pdf_id, 1) is False

    pan_menu = client.get("/other-fill/pan").get_data(as_text=True)
    assert "नया PAN" in pan_menu
    assert "https://www.incometax.gov.in/iec/foportal" not in pan_menu
    assert "OTR" not in pan_menu
    pan = client.post("/other-fill/pan/fill", data={"csrf_token": _csrf(pay)})
    assert pan.status_code == 200
    assert "Submit नहीं हुआ" in pan.get_data(as_text=True)
    assert seen["payload"]["url"] == "https://www.incometax.gov.in/iec/foportal"
    assert "खुले पन्ने पर फिर भरो" in pan.get_data(as_text=True)
    again = client.post("/other-fill/pan/fill", data={
        "csrf_token": _csrf(pan.get_data(as_text=True)),
        "again": "yes",
    })
    assert again.status_code == 200
    assert seen["payload"]["action"] == "reread"


def test_closed_notice_pdf_is_not_opened_as_the_form(monkeypatch, tmp_path):
    client, _database = _client(monkeypatch, tmp_path)
    created = client.post("/api/vacancies", json={
        "title": "SSC CHSL Recruitment 2026",
        "organization": "SSC",
        "official_link": (
            "https://ssc.gov.in/api/attachment/uploads/masterData/"
            "NoticeBoards/Notice_of_adv_chsl_2026.pdf"
        ),
        "registration_board": "ssc",
        "application_start": "2026-09-07",
        "application_end": "2026-10-07",
    })
    assert created.status_code == 201
    job_id = created.get_json()["vacancy"]["id"]
    page = client.get(f"/job/{job_id}").get_data(as_text=True)
    assert "बंद हो चुका है" in page
    assert "07/10/2026" in page
    assert "नोटिस है, फॉर्म नहीं" in page
    assert "हाँ, ऑटो-फिल से भरो" not in page
    assert "window.open" not in page
    assert "Notice_of_adv_chsl_2026.pdf" in page
