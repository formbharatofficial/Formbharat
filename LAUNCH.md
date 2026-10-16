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
- Mobile navigation, form CSRF, and the local verified-profile fill path have tests.
- OTP, CAPTCHA, verification codes, and final form submission stay user-controlled.
- Local browser tests use installed Microsoft Edge. Playwright Chromium is not required.

## Not yet ready

- No public deployment has been performed or verified from this repository.
- No custom domain or DNS is configured.
- No hosted production database is configured. The default is still the local SQLite file.
- OCR needs the Tesseract program, and PDF OCR needs Poppler's `pdftoppm`, installed on the host. Those are not Python packages.
- No external accounts, API keys, or payment credentials are part of this application.
- Legal, business, and store-listing approvals are outside the repository.
- Accounts can register and log in. A new account does not receive old profile slots. Only an empty slot can be claimed, and only with `FORMBHARAT_SLOT_CLAIM_CODE` plus an explicit confirmation.
- New documents are encrypted only when `FORMBHARAT_DOCUMENT_KEY` is a valid 32-byte key. Set `FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION=1` to reject uploads when that key is missing. Existing files stay readable and are not rewritten. A lost key cannot be recovered, and a new key does not open files written with the old key. OCR text for new encrypted uploads is stored with an `FBTEXT1` prefix. Older OCR rows in the database remain plaintext. Temporary OCR files are deleted after reading. Downloads are decrypted in memory and are not written back.
- Vacancy eligibility text is not an automatic pass or fail. Only an explicit criteria list can be compared, and a missing list stays unknown.
- Live government-site filling, payments, and a public deployment are not implemented.
- The browser test uses installed Edge through Playwright. Chromium download is not required.
