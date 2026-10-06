import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def database_path():
    """Return the SQLite file used by the application.

    Unset configuration keeps the existing repository database.
    """
    configured = os.environ.get("FORMBHARAT_DATABASE_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    return REPO_ROOT / "formbharat.db"


def storage_dir():
    """Return the document storage directory.

    Unset configuration keeps the existing documents directory.
    """
    configured = os.environ.get("FORMBHARAT_STORAGE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return REPO_ROOT / "documents"


def apply_document_vault_paths(vault):
    """Point the document vault at configured paths when they are set."""
    if os.environ.get("FORMBHARAT_DATABASE_PATH", "").strip():
        vault.DB_PATH = str(database_path())
    if os.environ.get("FORMBHARAT_STORAGE_DIR", "").strip():
        vault.STORAGE_DIR = str(storage_dir())


def load_settings():
    """Read deployment settings. Production never enables the debugger."""
    environment = os.environ.get("FORMBHARAT_ENV", "development").strip().lower()
    production = environment == "production"
    host = os.environ.get("HOST", "0.0.0.0").strip() or "0.0.0.0"
    port_text = os.environ.get("PORT", "5000").strip() or "5000"
    if not port_text.isdigit():
        raise ValueError("PORT must be an integer between 1 and 65535")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be an integer between 1 and 65535")
    return {
        "environment": "production" if production else "development",
        "production": production,
        "debug": False if production else True,
        "host": host,
        "port": port,
        "database_path": database_path(),
        "storage_dir": storage_dir(),
    }
