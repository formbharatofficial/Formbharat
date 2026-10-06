import importlib.util
from pathlib import Path

from bs4 import BeautifulSoup


def _client(monkeypatch, tmp_path):
    from app import document_vault, profile, verified_profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(profile, "DB_PATH", db)
    monkeypatch.setattr(document_vault, "DB_PATH", str(db))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(verified_profile, "DB_PATH", db)

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
    }

    for path, page in pages.items():
        assert 'class="fb-nav"' in page
        assert 'href="/profile"' in page
        assert 'href="/documents"' in page
        assert 'href="/vacancies"' in page
        assert 'href="/applications"' in page
        assert 'href="/"' in page
        assert "viewport" in page
        assert path


def test_home_dashboard_keeps_the_analyze_form(monkeypatch, tmp_path):
    page = _page(_client(monkeypatch, tmp_path), "/")

    assert "Dashboard" in page
    assert 'href="/test-form"' in page
    assert 'id="rootForm"' in page
    assert "analyzeForm" in page
    assert "innerHTML" not in page
    soup = BeautifulSoup(page, "html.parser")
    assert soup.find(id="profile_id").get("value") in (None, "")


def test_vacancy_page_is_read_only(monkeypatch, tmp_path):
    page = _page(_client(monkeypatch, tmp_path), "/vacancies")

    assert 'fetch("/api/vacancies")' in page
    assert "No vacancies saved yet." in page
    assert "Could not load vacancies." in page
    assert "PUT" not in page
    assert "POST" not in page
    assert "Create" not in page
    assert "Delete" not in page
    assert "innerHTML" not in page


def test_application_page_is_read_only(monkeypatch, tmp_path):
    page = _page(_client(monkeypatch, tmp_path), "/applications")

    assert "/api/applications/" in page
    assert "/history" in page
    assert "No applications saved yet." in page
    assert "No status history." in page
    assert "profile_id must be an integer between 1 and 5" in page
    assert "PUT" not in page
    assert "POST" not in page
    assert "Create" not in page
    assert "innerHTML" not in page
    soup = BeautifulSoup(page, "html.parser")
    assert soup.find(id="profile_id").get("value") in (None, "")
