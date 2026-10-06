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

OCR of uploaded images needs the Tesseract program. PDF OCR also needs Poppler's `pdftoppm`. The application still starts when those programs are absent.

## First deployment target

`.replit` runs `python src/main.py` with `FORMBHARAT_ENV=production`. That prepares a Replit start command. It does not by itself publish the application.
