import importlib.util
from pathlib import Path

from bs4 import BeautifulSoup


def _client(monkeypatch, tmp_path):
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

    spec = importlib.util.spec_from_file_location(
        "formbharat_mobile_ui_main",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded.app.config["TESTING"] = True
    return loaded.app.test_client()


def _page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_existing_and_new_pages_share_mobile_navigation(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    pages = {
        "/": _page(client, "/"),
        "/test-form": _page(client, "/test-form"),
        "/profile": _page(client, "/profile"),
        "/documents": _page(client, "/documents"),
        "/vacancies": _page(client, "/vacancies"),
        "/applications": _page(client, "/applications"),
        "/other-forms": _page(client, "/other-forms"),
    }

    for path, page in pages.items():
        assert 'class="fb-nav"' in page
        assert 'rel="manifest"' in page
        assert "font-size:11px;line-height:1.15" in page
        assert "Home" in page
        assert 'href="/profile"' in page
        assert 'href="/documents"' in page
        assert 'href="/vacancies"' in page
        assert 'href="/applications"' in page
        assert 'href="/other-forms"' in page
        assert "Other Form" in page
        assert 'href="/"' in page
        assert "viewport" in page
        assert path

    assert "OCR is not verification." in pages["/documents"]
    assert "/api/csrf" in pages["/documents"]
    assert 'name="csrf_token"' in pages["/profile"]
    other_forms = pages["/other-forms"]
    assert "PAN card" in other_forms
    assert "Ration card" in other_forms
    assert 'href="/other-fill/pan"' in other_forms
    assert "ऐप भरे" not in other_forms
    pan = _page(client, "/other-fill/pan")
    assert "कौन सा काम करना है?" in pan
    assert "नया PAN" in pan
    assert "PAN में सुधार" in pan
    assert "https://www.incometax.gov.in/iec/foportal" not in pan
    assert "ऑटो-फिल से भरना चाहते हैं" not in pan
    assert "ऐप भरे" not in pan
    assert "window.open" not in pan
    assert "OTR" not in pan
    assert "One Time Registration" not in pan
    assert "https://www.pan.utiitsl.com/PAN/" not in other_forms
    assert "https://tinpan.proteantech.in/services/pan/pan-index/" not in other_forms
    assert 'href="/other-fill/ration"' in other_forms
    ration = _page(client, "/other-fill/ration")
    assert "नया राशन कार्ड" in ration
    assert "https://nfsa.gov.in/portal/state_portals" not in ration
    assert "OTR" not in ration
    assert "Uttar Pradesh" not in other_forms
    assert "Odisha" not in other_forms
    assert "http://fcs.up.gov.in/FoodPortal.aspx" not in other_forms
    assert "https://www.pdsodisha.gov.in/" not in other_forms
    assert "Andaman and Nicobar" not in other_forms
    assert "https://myaadhaar.uidai.gov.in/" not in other_forms
    assert "Shram card" in other_forms
    assert "नया श्रम कार्ड" in _page(client, "/other-fill/shram")
    assert "https://www.eshram.gov.in/" not in _page(client, "/other-fill/shram")
    assert "Ayushman card" in other_forms
    assert "नया आयुष्मान कार्ड" in _page(client, "/other-fill/ayushman")
    assert "https://nha.gov.in/Ayushman-Card" not in _page(client, "/other-fill/ayushman")
    assert "Kisan Samman Nidhi" in other_forms
    assert "नया किसान पंजीकरण" in _page(client, "/other-fill/kisan")
    assert "https://www.pmkisan.gov.in/" not in _page(client, "/other-fill/kisan")
    assert "नया वोटर कार्ड" in _page(client, "/other-fill/voter")
    assert "https://voters.eci.gov.in/" not in _page(client, "/other-fill/voter")
    licence = _page(client, "/other-fill/licence")
    assert "कौन सा काम करना है?" in licence
    assert "लर्नर लाइसेंस" in licence
    assert "ड्राइविंग लाइसेंस" in licence
    assert "लाइसेंस रिन्यू" in licence
    assert "डुप्लीकेट लाइसेंस" in licence
    assert "पते में बदलाव" in licence
    assert "इंटरनेशनल ड्राइविंग परमिट" in licence
    assert "window.open" not in licence
    assert "sarathi.parivahan.gov.in" not in licence
    assert "हाँ, ऑटो-फिल से भरो" not in licence
    passport = _page(client, "/other-fill/passport")
    assert "नया पासपोर्ट" in passport
    assert "https://www.passportindia.gov.in/psp/Apply" not in passport
    assert "Asli website:" not in other_forms
    assert "Sarkari site kholo" not in other_forms
    assert "khud nahi bharega" not in other_forms
    assert "innerHTML" not in other_forms
    assert "One Time Registration" not in other_forms
    assert "OTR" not in other_forms
    assert "/board-registration" not in other_forms
    assert "rrbapply.gov.in" not in other_forms


def test_home_dashboard_keeps_the_analyze_form(monkeypatch, tmp_path):
    page = _page(_client(monkeypatch, tmp_path), "/")

    assert "Dashboard" in page
    assert "OTP, CAPTCHA, and final Submit stay with you." in page
    assert "Sign in from Account." in page
    assert 'href="/test-form"' in page
    assert "Latest Updates" in page
    assert "See All" in page
    assert "function liveDate" in page
    assert ".slice(0, 3)" in page
    assert "Abhi koi current link nahi hai." in page
    assert 'fetch("/api/vacancies")' in page
    assert 'id="rootForm"' in page
    assert "analyzeForm" in page
    assert "innerHTML" not in page
    soup = BeautifulSoup(page, "html.parser")
    assert soup.find(id="profile_id").get("value") in (None, "")


def test_vacancy_page_is_read_only(monkeypatch, tmp_path):
    page = _page(_client(monkeypatch, tmp_path), "/vacancies")

    assert 'fetch("/api/vacancies")' in page
    assert "No vacancies saved yet." in page
    assert "Latest Jobs" in page
    assert "Admit Cards" in page
    assert "Results" in page
    assert "Dikhao" not in page
    assert "Yahan likho" not in page
    assert "Could not load vacancies." in page
    assert "PUT" not in page
    assert "POST" not in page
    assert "ऐप भरे" not in page
    assert "Create" not in page
    assert "Delete" not in page
    assert "innerHTML" not in page
    assert "Board step" not in page
    assert "/board-registration" not in page


def test_application_page_is_read_only(monkeypatch, tmp_path):
    page = _page(_client(monkeypatch, tmp_path), "/applications")

    assert "/api/applications/" in page
    assert "/history" in page
    assert "No applications saved yet." in page
    assert "does not submit a government form" in page
    assert "Official link:" in page
    assert "Deadline:" in page
    assert "No status history." in page
    assert "profile_id must be an integer between 1 and 5" in page
    assert "PUT" not in page
    assert "POST" not in page
    assert "Create" not in page
    assert "innerHTML" not in page
    assert "Board step" not in page
    assert "/board-registration" not in page
    soup = BeautifulSoup(page, "html.parser")
    assert soup.find(id="profile_id").get("value") in (None, "")


def test_licence_charge_starts_only_after_the_profile_is_ready(monkeypatch, tmp_path):
    import sqlite3
    from datetime import datetime, timezone

    from app.profile import save_profile

    client = _client(monkeypatch, tmp_path)
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    blocked = client.get("/other-fill/licence/check?service=learner")
    blocked_page = blocked.get_data(as_text=True)
    assert blocked.status_code == 200
    assert "अभी ₹20 नहीं कटेगा" in blocked_page
    assert "सरकारी साइट" not in blocked_page
    assert 'href="/other-fill/licence/pay?service=learner"' not in blocked_page
    pan_need = client.get("/other-fill/pan/check?service=new").get_data(as_text=True)
    assert "आधार" in pan_need
    assert "हस्ताक्षर" in pan_need
    assert "10th" not in pan_need
    assert "माता" not in pan_need
    voter_shift = client.get("/other-fill/voter/check?service=shift").get_data(as_text=True)
    assert "पता" in voter_shift
    assert "ज़िला" in voter_shift
    assert "नाम" not in voter_shift
    assert "फोटो" not in voter_shift

    save_profile({
        "name": "Ready User",
        "email": "ready@example.com",
        "mobile": "9000000011",
        "dob": "1990-01-01",
        "address": "Lucknow",
        "state": "Uttar Pradesh",
        "father_name": "Father User",
    })
    stamp = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(tmp_path / "formbharat.db")
    for doc_type, ref in (("photo", "DOC-PHOTO"), ("signature", "DOC-SIGN")):
        conn.execute(
            """
            INSERT INTO documents (
                profile_id, doc_type, original_filename, storage_path,
                created_at, updated_at, document_reference
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, doc_type, doc_type + ".jpg", doc_type + ".jpg", stamp, stamp, ref),
        )
    conn.commit()
    conn.close()

    ready = client.get("/other-fill/licence/check?service=learner")
    ready_page = ready.get_data(as_text=True)
    assert "जो इस काम में चाहिए वह सेव है" in ready_page
    assert 'href="/other-fill/licence/pay?service=learner"' in ready_page
    pay = client.get("/other-fill/licence/pay?service=learner")
    pay_page = pay.get_data(as_text=True)
    assert pay.status_code == 200
    assert "https://sarathi.parivahan.gov.in/sarathiservice/stateSelection.do" in pay_page
    assert "फॉर्म भरो" in pay_page
    assert "लर्नर लाइसेंस" in pay_page
