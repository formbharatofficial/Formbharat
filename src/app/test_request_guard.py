import importlib.util
from pathlib import Path

from bs4 import BeautifulSoup
from flask import Flask, jsonify


def test_form_posts_require_a_csrf_token_and_json_rejects_another_origin():
    from app.request_guard import install_request_guard

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["FORMBHARAT_RATE_LIMIT"] = 5
    install_request_guard(app)

    @app.post("/save")
    def save():
        return jsonify({"success": True})

    @app.delete("/save")
    def remove():
        return jsonify({"success": True, "deleted": True})

    client = app.test_client()
    denied = client.post("/save", data={"name": "A"})
    assert denied.status_code == 403
    assert denied.get_json()["error"] == "csrf token is required"

    issued = client.get("/api/csrf")
    token = issued.get_json()["token"]
    cookie = " ".join(issued.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookie
    assert "SameSite=Strict" in cookie
    allowed = client.post("/save", data={"name": "A", "csrf_token": token})
    assert allowed.status_code == 200

    foreign = client.post(
        "/save",
        json={"name": "A"},
        headers={"Origin": "http://evil.test"},
    )
    assert foreign.status_code == 403
    assert foreign.get_json()["error"] == "cross-origin request was rejected"

    same_origin = client.post("/save", json={"name": "A"})
    assert same_origin.status_code == 200

    deleted = client.delete("/save")
    assert deleted.status_code == 200
    assert deleted.get_json()["deleted"] is True


def test_localhost_tunnel_https_counts_as_the_same_page():
    from app.request_guard import install_request_guard

    app = Flask(__name__)
    app.config["TESTING"] = True
    install_request_guard(app)

    @app.post("/save")
    def save():
        return jsonify({"success": True})

    client = app.test_client()
    phone = client.post(
        "/save",
        base_url="http://phone.example",
        json={"name": "A"},
        headers={
            "Origin": "https://phone.example",
            "X-Forwarded-Proto": "https",
        },
    )
    outsider = client.post(
        "/save",
        base_url="http://phone.example",
        json={"name": "A"},
        headers={
            "Origin": "https://phone.example",
            "X-Forwarded-Proto": "https",
        },
        environ_base={"REMOTE_ADDR": "10.9.9.9"},
    )
    evil = client.post(
        "/save",
        base_url="http://phone.example",
        json={"name": "A"},
        headers={
            "Origin": "https://evil.test",
            "X-Forwarded-Proto": "https",
        },
    )

    visitor = client.post(
        "/save",
        base_url="http://phone.example",
        json={"name": "A"},
        headers={
            "Origin": "https://phone.example",
            "CF-Visitor": '{"scheme":"https"}',
        },
    )
    visitor_out = client.post(
        "/save",
        base_url="http://phone.example",
        json={"name": "A"},
        headers={
            "Origin": "https://phone.example",
            "CF-Visitor": '{"scheme":"https"}',
        },
        environ_base={"REMOTE_ADDR": "10.9.9.9"},
    )

    assert phone.status_code == 200
    assert visitor.status_code == 200
    assert visitor_out.status_code == 403
    assert outsider.status_code == 403
    assert outsider.get_json()["error"] == "cross-origin request was rejected"
    assert evil.status_code == 403


def test_sensitive_requests_are_rate_limited():
    from app.request_guard import install_request_guard

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["FORMBHARAT_RATE_LIMIT"] = 2
    install_request_guard(app)

    @app.post("/save")
    def save():
        return jsonify({"success": True})

    client = app.test_client()
    assert client.post("/save", json={"n": 1}).status_code == 200
    assert client.post("/save", json={"n": 2}).status_code == 200
    limited = client.post("/save", json={"n": 3})
    assert limited.status_code == 429
    assert limited.get_json()["error"] == "too many requests"


def _load_main(monkeypatch, tmp_path):
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
        "formbharat_request_guard_main",
        Path(__file__).resolve().parents[1] / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    loaded.app.config["TESTING"] = True
    return loaded


def test_local_assist_route_rejects_bad_urls_and_profile_payloads(
    monkeypatch, tmp_path
):
    client = _load_main(monkeypatch, tmp_path).app.test_client()

    remote = client.post(
        "/api/local-assist",
        json={"url": "javascript:alert(1)", "profile_id": 1},
    )
    supplied = client.post(
        "/api/local-assist",
        json={
            "url": "file:///C:/local.html",
            "profile_id": 1,
            "profile": {"name": "Attacker"},
        },
    )

    assert remote.status_code == 400
    assert remote.get_json()["submitted"] is False
    assert "form page" in remote.get_json()["error"]
    assert supplied.status_code == 400
    assert "profile_id and form page URL" in supplied.get_json()["error"]
    assert client.application.extensions.get("local_browser_sessions", {}) == {}


def test_profile_form_post_requires_the_page_token(monkeypatch, tmp_path):
    client = _load_main(monkeypatch, tmp_path).app.test_client()
    page = client.get("/profile")
    token = BeautifulSoup(page.get_data(as_text=True), "html.parser").find(
        "input",
        attrs={"name": "csrf_token"},
    )["value"]

    denied = client.post("/profile", data={"name": "No Token"})
    allowed = client.post("/profile", data={"name": "Token User", "csrf_token": token})

    assert page.status_code == 200
    assert denied.status_code == 403
    assert allowed.status_code == 302
