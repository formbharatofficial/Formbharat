# FormBharat launch readiness

This checklist is based on what can be verified in the repository. It is not a claim that a public deployment has succeeded.

## Ready

- The application starts from `python src/main.py`.
- `FORMBHARAT_ENV=production` uses Waitress and does not enable the Flask debugger.
- Local development still uses the Flask development server when `FORMBHARAT_ENV` is unset or `development`.
- `HOST` and `PORT` come from the environment. Defaults remain `0.0.0.0` and `5000`.
- Runtime dependencies are listed in `requirements.txt`.
- Optional database and document-storage locations are `FORMBHARAT_DATABASE_PATH` and `FORMBHARAT_STORAGE_DIR`. Unset values keep the existing local files.
- `.env.example` documents the settings and contains no credentials.
- `.replit` starts the app in production mode. Replit supplies `PORT`.
- Phase 8 mobile UI and security behavior remain covered by the existing tests.
- OTP, CAPTCHA, verification codes, and final form submission stay user-controlled.

## Not yet ready

- No public deployment has been performed or verified from this repository.
- No custom domain or DNS is configured.
- No hosted production database is configured. The default is still the local SQLite file.
- OCR needs the Tesseract program, and PDF OCR needs Poppler's `pdftoppm`, installed on the host. Those are not Python packages.
- No external accounts, API keys, or payment credentials are part of this application.
- Legal, business, and store-listing approvals are outside the repository.
- The browser test still requires Playwright, which is not installed in this environment.
