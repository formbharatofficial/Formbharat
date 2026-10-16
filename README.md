# Formbharat

## Run locally

```text
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

Development is the default. The Flask development server listens on `0.0.0.0:5000` with the debugger enabled. Open `http://127.0.0.1:5000/`.

## Production mode

Set `FORMBHARAT_ENV=production` before starting. Production uses Waitress and does not enable the Flask debugger. `HOST` and `PORT` override the listen address; Replit provides `PORT`.

Optional paths:

- `FORMBHARAT_DATABASE_PATH` — SQLite database. Unset keeps `formbharat.db` in the repository root.
- `FORMBHARAT_STORAGE_DIR` — uploaded documents. Unset keeps the `documents/` directory.

See `.env.example` and `LAUNCH.md`. Do not commit a `.env` file or real credentials.

OCR of uploaded images needs the Tesseract program. PDF OCR also needs Poppler's `pdftoppm`. The application still starts when those programs are absent. OCR text is not treated as verified profile data.

Local rendered-page tests use the installed Microsoft Edge browser through Playwright. They do not download Playwright's Chromium package. Set `FORMBHARAT_SECRET_KEY` outside the repository when a stable session secret is required. If it is unset, the process uses a temporary random secret.

Accounts are created at `/account`. Registration does not claim profile slots. An empty slot can be claimed only with an explicit confirmation and `FORMBHARAT_SLOT_CLAIM_CODE`. Legacy profile, document, and application data cannot be claimed. Guardian name is a separate profile field and is filled only from a verified value that is not the applicant's own name.

Documents stay in their original bytes until a 32-byte `FORMBHARAT_DOCUMENT_KEY` is configured outside the repository. `FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION=1` rejects a new upload when the key is missing. A lost key cannot be recovered. See `LAUNCH.md`. A vacancy eligibility sentence is not an automatic pass or fail. `GET /api/access` reports the account and encryption boundary. The app is not production-ready.

## First deployment target

`.replit` runs `python src/main.py` with `FORMBHARAT_ENV=production`. That prepares a Replit start command. It does not by itself publish the application.
