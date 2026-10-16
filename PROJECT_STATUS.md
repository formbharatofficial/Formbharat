# FormBharat — PROJECT STATUS

## CURRENT POSITION
- Current Phase: Phase 5 — Form Intelligence
- Status: COMPLETE
- Last verified device: Windows
- Latest verified backup: 2026-09-25

## PHASE STATUS
- Phase 1 — Foundation: COMPLETE
- Phase 2 — User System: COMPLETE
- Phase 3 — Document Vault: COMPLETE
- Phase 4 — Vacancy: COMPLETE
- Phase 5 — Form Intelligence: COMPLETE
- Phase 6 — Assisted Form Filling: NOT STARTED
- Phase 7 — Application Tracker: NOT STARTED
- Phase 8 — Mobile UI + Security + Production: NOT STARTED

## PHASE 5 RECORD
Phase 5 understands supplied HTML and HTML already rendered by a caller.
It can reread a new supplied HTML snapshot.
It does not fill fields, click through steps, or submit a form.
Live `Browser.open` integration is not claimed as a Phase 5 completion requirement.
Unsupported labels, including Hindi labels with no specified mapping, stay unknown.

## LOCKED ROADMAP
1. Foundation
2. User System
3. Document Vault
4. Vacancy
5. Form Intelligence
6. Assisted Form Filling
7. Application Tracker
8. Mobile UI + Security + Production

## LOCKED SAFETY RULES
- OTP must always be handled by the user.
- CAPTCHA must always be handled by the user.
- Final form submission must always be handled by the user.
- Related-person fields such as Father/Mother must not be globally blocked when verified data exists in the user's saved profile/documents.

## CURRENT NEXT STEP
The locked roadmap below is unchanged. The phase labels in this file are not a certificate that the current code has finished every phase.

The verified local checkpoint is recorded at the end of this file. Account login, at-rest encryption, and live government-site filling remain unresolved.

## WORK RULE
Do not guess.
Do not redo completed phases.
Do not modify existing architecture before inspection.
Every completed task must be verified by tests or documented evidence.
After verified work, commit and push to the central GitHub repository.

## DEVICE CONTINUITY
When changing device:
1. Get the latest project from GitHub.
2. Read this file first.
3. Continue from CURRENT POSITION / CURRENT NEXT STEP.
4. Never start by guessing what was previously completed.

## LAST VERIFIED LOCAL COMMIT
748ffbf — Complete Phase 1-4 foundation and quality gates

Phase 5 is recorded by the commit that contains this status update.

## NOTES
This file is the project continuity record.
Update it whenever the verified project state changes.

## VERIFIED LOCAL CHECKPOINT — 2026-10-16
This checkpoint does not mark any phase, government-site support, production deployment, encryption, or MeitY/legal compliance complete.

### Implemented and tested
- Local-file assistance loads the verified profile for a profile slot. A caller-supplied profile dictionary is rejected by that entry point.
- A kept-open Edge session can reread the current DOM after a page change. It does not click Next or submit.
- Email, real calendar date, six-digit PIN, and ten-digit mobile values are withheld when invalid.
- Review payload lists proposed and withheld fields and sets submitted to false.
- Form and multipart requests require the session CSRF token. JSON and empty-body API calls stay available to the local app. JSON requests from another Origin are rejected. Unsafe requests have an in-memory rate limit.
- A document file is returned only for its own profile slot. Application responses include the saved vacancy's official link and deadline, and they are marked as profile-slot access rather than an authenticated account.
- Existing screens share a saffron, white, and green mobile-first header and navigation. Review results list proposed and withheld values. OCR status is shown as not verification.
- Radio and select fields are filled only when one option matches the verified value. A missing option is withheld, not reported as filled.
- Accounts register and log in with a password hash. A new account cannot see or automatically claim an existing slot. Claim works only for an empty slot, with explicit confirmation and `FORMBHARAT_SLOT_CLAIM_CODE`.
- `guardian_name` is stored separately from father and mother. Auto-fill uses it only when the verified profile has a value and that value is not the applicant's own name.
- New document bytes and new OCR text are encrypted when a valid 32-byte `FORMBHARAT_DOCUMENT_KEY` is set. `FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION=1` rejects the upload when the key is missing. Files without the `FBDOC1` header stay readable and are not rewritten. A lost key cannot be recovered, and replacing the key does not decrypt older files.
- `GET /api/vacancies/<id>/eligibility` returns unknown for stored vacancies because their eligibility value is free text and the vacancy table has no criteria column. The comparison function accepts an explicit criteria list only when that list is supplied in memory. A missing profile value stays unknown. It does not invent an official pass or fail.
- On 2026-10-16, `py -3 -m pytest app -q --tb=line` from `src` passed 200 tests, with 14 warnings and exit code 0. One test opened a local HTML form in Microsoft Edge. The warnings are the existing `datetime.utcnow()` deprecation.

### Not implemented
- Public deployment, hosted accounts, password reset, and email verification.
- Re-encryption or recovery of files whose key was lost or changed.
- Claiming a slot that already has profile, document, or application data.
- Payment or premium features.
- Automatic government-site navigation or submission.

### Blocked or waiting on a decision
- Playwright's Chromium download failed earlier because of DNS. Tests use the installed Edge browser.
- The operator must keep `FORMBHARAT_DOCUMENT_KEY` outside the repository. Existing files are not encrypted in place.
- Password reset and email verification are not implemented.
