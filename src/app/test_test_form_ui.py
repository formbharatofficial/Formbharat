import importlib.util
import re
from pathlib import Path

from bs4 import BeautifulSoup


def _load_main(monkeypatch, tmp_path):
    from app import document_vault, profile, verified_profile

    db = tmp_path / "formbharat.db"
    monkeypatch.setattr(profile, "DB_PATH", db)
    monkeypatch.setattr(document_vault, "DB_PATH", str(db))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(verified_profile, "DB_PATH", db)

    spec = importlib.util.spec_from_file_location(
        "formbharat_test_form_main",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded.app.config["TESTING"] = True
    return loaded


def _page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _assert_analyze_contract(page, form_id):
    assert "innerHTML" not in page
    assert "textContent" in page
    assert "replaceChildren" in page

    soup = BeautifulSoup(page, "html.parser")
    form = soup.find(id=form_id)
    profile_id = soup.find(id="profile_id")

    assert form is not None
    assert profile_id is not None
    assert profile_id.get("value") in (None, "")
    assert form.find(id="profile_id") is None

    blocks = re.findall(r"JSON\.stringify\(\{(.*?)\}\)", page, re.S)
    assert len(blocks) == 1
    assert "html:" in blocks[0]
    assert "profile_id: Number(profileId)" in blocks[0]
    assert re.search(r"(?<![\w])profile\s*:", blocks[0]) is None
    assert "/^[1-5]$/" in page
    assert "profile_id: 1" not in page
    assert "profile_id = 1" not in page


def test_test_form_sends_html_and_explicit_profile_id(monkeypatch, tmp_path):
    client = _load_main(monkeypatch, tmp_path).app.test_client()
    page = _page(client, "/test-form")

    _assert_analyze_contract(page, "testForm")
    assert "analyzeAndFill" in page
    assert "showResultText" in page
    assert "showAnalysisResult" in page


def test_root_form_sends_html_and_explicit_profile_id(monkeypatch, tmp_path):
    client = _load_main(monkeypatch, tmp_path).app.test_client()
    page = _page(client, "/")

    _assert_analyze_contract(page, "rootForm")
    assert "analyzeForm" in page
    assert "showRootResult" in page
    assert "const profile =" not in page
    assert "profile: profile" not in page
