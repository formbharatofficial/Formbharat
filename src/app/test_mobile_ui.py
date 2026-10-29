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
    assert "https://www.incometax.gov.in/iec/foportal" in pan
    assert "ऑटो-फिल से भरना चाहते हैं" in pan
    assert "ऐप भरे" not in pan
    assert "window.open" in pan
    assert "OTR" not in pan
    assert "One Time Registration" not in pan
    assert "https://www.pan.utiitsl.com/PAN/" not in other_forms
    assert "https://tinpan.proteantech.in/services/pan/pan-index/" not in other_forms
    assert 'href="/other-fill/ration"' in other_forms
    ration = _page(client, "/other-fill/ration")
    assert "https://nfsa.gov.in/portal/state_portals" in ration
    assert "OTR" not in ration
    assert "Uttar Pradesh" not in other_forms
    assert "Odisha" not in other_forms
    assert "http://fcs.up.gov.in/FoodPortal.aspx" not in other_forms
    assert "https://www.pdsodisha.gov.in/" not in other_forms
    assert "Andaman and Nicobar" not in other_forms
    assert "https://myaadhaar.uidai.gov.in/" not in other_forms
    assert "Shram card" in other_forms
    assert "https://www.eshram.gov.in/" in _page(client, "/other-fill/shram")
    assert "Ayushman card" in other_forms
    assert "https://nha.gov.in/Ayushman-Card" in _page(client, "/other-fill/ayushman")
    assert "Kisan Samman Nidhi" in other_forms
    assert "https://www.pmkisan.gov.in/" in _page(client, "/other-fill/kisan")
    assert "https://voters.eci.gov.in/" in _page(client, "/other-fill/voter")
    assert "https://sarathi.parivahan.gov.in/sarathiservice/stateSelection.do" in _page(client, "/other-fill/licence")
    assert "https://www.passportindia.gov.in/psp/Apply" in _page(client, "/other-fill/passport")
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
