import importlib.util
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from app.runtime_config import database_path, load_settings, storage_dir


REPO = Path(__file__).resolve().parents[2]


def test_development_settings_keep_local_defaults(monkeypatch):
    monkeypatch.delenv("FORMBHARAT_ENV", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("FORMBHARAT_DATABASE_PATH", raising=False)
    monkeypatch.delenv("FORMBHARAT_STORAGE_DIR", raising=False)

    settings = load_settings()

    assert settings["environment"] == "development"
    assert settings["production"] is False
    assert settings["debug"] is True
    assert settings["host"] == "0.0.0.0"
    assert settings["port"] == 5000
    assert database_path() == REPO / "formbharat.db"
    assert storage_dir() == REPO / "documents"


def test_production_settings_disable_debug_and_read_host_port(monkeypatch, tmp_path):
    monkeypatch.setenv("FORMBHARAT_ENV", "production")
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "8123")
    monkeypatch.setenv("FORMBHARAT_DATABASE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("FORMBHARAT_STORAGE_DIR", str(tmp_path / "files"))

    settings = load_settings()

    assert settings["environment"] == "production"
    assert settings["debug"] is False
    assert settings["host"] == "127.0.0.1"
    assert settings["port"] == 8123
    assert settings["database_path"] == tmp_path / "app.db"
    assert settings["storage_dir"] == tmp_path / "files"


def test_port_must_be_an_integer(monkeypatch):
    monkeypatch.setenv("PORT", "abc")
    with pytest.raises(ValueError, match="PORT"):
        load_settings()


def _load_main(module_name):
    spec = importlib.util.spec_from_file_location(
        module_name,
        REPO / "src" / "main.py",
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_production_serve_uses_waitress_without_debug(monkeypatch, tmp_path):
    from app import application_tracker
    from app import document_vault
    from app import profile
    from app import vacancy
    from app import verified_profile

    database = tmp_path / "formbharat.db"
    monkeypatch.setenv("FORMBHARAT_ENV", "production")
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "8124")
    monkeypatch.setenv("FORMBHARAT_DATABASE_PATH", str(database))
    monkeypatch.setenv("FORMBHARAT_STORAGE_DIR", str(tmp_path / "documents"))
    monkeypatch.setattr(profile, "DB_PATH", database)
    monkeypatch.setattr(vacancy, "DB_PATH", database)
    monkeypatch.setattr(application_tracker, "DB_PATH", database)
    monkeypatch.setattr(verified_profile, "DB_PATH", database)
    monkeypatch.setattr(document_vault, "DB_PATH", str(database))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))

    loaded = _load_main("formbharat_production_main")
    calls = {}

    def fake_serve(application, host, port):
        calls["debug"] = application.debug
        calls["propagate"] = application.config["PROPAGATE_EXCEPTIONS"]
        calls["host"] = host
        calls["port"] = port

    import waitress

    monkeypatch.setattr(waitress, "serve", fake_serve)
    loaded.serve()

    assert calls == {
        "debug": False,
        "propagate": False,
        "host": "127.0.0.1",
        "port": 8124,
    }


def test_production_process_serves_health(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    env = os.environ.copy()
    env["FORMBHARAT_ENV"] = "production"
    env["HOST"] = "127.0.0.1"
    env["PORT"] = str(port)
    env["FORMBHARAT_DATABASE_PATH"] = str(tmp_path / "formbharat.db")
    env["FORMBHARAT_STORAGE_DIR"] = str(tmp_path / "documents")
    process = subprocess.Popen(
        [sys.executable, str(REPO / "src" / "main.py")],
        cwd=REPO,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        body = ""
        for _ in range(40):
            if process.poll() is not None:
                break
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health",
                    timeout=1,
                ) as response:
                    body = response.read().decode("utf-8")
                    status = response.status
                break
            except Exception:
                time.sleep(0.25)
        else:
            status = 0
        output = ""
        if process.poll() is not None:
            output = process.stdout.read()
        assert status == 200
        assert '"status":"ok"' in body.replace(" ", "") or '"status": "ok"' in body
        assert "Debugger is active" not in output
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
