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


def load_env_file(path=None):
    """Load KEY=value lines from the repo .env. Existing variables stay as they are."""
    file = Path(path) if path else REPO_ROOT / ".env"
    if not file.is_file():
        return
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


def gemini_api_key():
    """Return the Gemini key from the environment or .env. Never invent one."""
    load_env_file()
    for name in ("FORMBHARAT_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


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
