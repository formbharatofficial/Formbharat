# FormBharat — Current State

## Current Phase
Phase 5 — Form Intelligence: COMPLETE

## Next Phase
Phase 6 — Assisted Form Filling: NOT STARTED

## Phase Status
- Phase 1 — Foundation: COMPLETE
- Phase 2 — User System: COMPLETE
- Phase 3 — Document Vault: COMPLETE
- Phase 4 — Vacancy: COMPLETE
- Phase 5 — Form Intelligence: COMPLETE
- Phase 6 — Assisted Form Filling: NOT STARTED
- Phase 7 — Application Tracker: NOT STARTED
- Phase 8 — Mobile UI + Security + Production: NOT STARTED

## Phase 5 Limitation
Phase 5 understands supplied HTML and HTML already rendered by a caller.
It supports rereading a new supplied HTML snapshot.
It does not fill fields, click through steps, or submit a form.
Live `Browser.open` integration is not claimed as a Phase 5 completion requirement.

## Repository
formbharatofficial/Formbharat

Previous verified checkpoint on main:
748ffbf — Complete Phase 1-4 foundation and quality gates

## Development Rule
The 8-phase roadmap is locked.
The phase labels above are the roadmap record. They are not a certificate that the current code has finished every phase.
Inspect the existing reader, fill boundary, and tests before changing them.

## Verified local checkpoint — 2026-10-16
Local verified-profile assistance, a kept-open headless Edge reread, review before submit, form and multipart CSRF, request rate limiting, document profile checks, and the shared screen theme were exercised. Radio and select controls are filled only when one option matches. Accounts can register and log in. Old profile slots are not claimed automatically. Only an empty slot can be claimed with a server claim code and explicit confirmation. `guardian_name` is a separate field and is auto-filled only from a verified value that is not the applicant's own name. New documents are encrypted when `FORMBHARAT_DOCUMENT_KEY` is valid. If encryption is required and the key is missing, the upload is rejected. Existing document files are not rewritten. `GET /api/vacancies/<id>/eligibility` returns unknown unless a vacancy supplies an explicit criteria list. From `src`, the latest full `py -3 -m pytest app -q --tb=line` result is in PROJECT_STATUS.md. Government-site filling is not implemented. No phase is certified complete by this checkpoint.
