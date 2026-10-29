# Board registration assistance

SSC One Time Registration and the RRB Candidate Account are separate.
This page does not change the locked 8-phase roadmap.

Checked on 2026-10-28:

- SSC home: https://ssc.gov.in/
- SSC candidate portal: https://ssc.gov.in/candidate-portal/one-time-registration
- SSC OTR flow: https://ssc.gov.in/api/attachment/uploads/masterData/SpecialInstructions/One_Time_Registration_flow%201.pdf
- Notice that an old ssc.nic.in OTR is void (19 February 2024): https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/OTR_Notice_22022024.pdf
- SSC edit-OTR notice (8 October 2025): https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_08102025.pdf
- RRB FAQ that names rrbapply.gov.in and Create an Account: https://www.rrbcdg.gov.in/uploads/2025/05-JE/052025JE-ApplicationFAQs.pdf
- RRB portal named by that FAQ: https://www.rrbapply.gov.in/

Those official texts do not publish one fixed registration-number pattern. FormBharat only checks that the saved value is a short identifier. It does not invent an SSC or RRB digit rule.

## Vacancy metadata

`vacancies.registration_board` may be empty, `none`, `ssc`, or `rrb`.

- `ssc` or `rrb` shows that board's assistance.
- `none` skips the step.
- empty asks the user. The job title is not used as a guess.

## What is stored

A row is written only when consent is the JSON value true.

The row stores the board, record type (`ssc_otr` or `rrb_candidate_account`), registration number, status `user_confirmed`, confirmation source `user`, account path, consent version, consent text, consent time, profile slot, and the signed-in account id when there is one.

When `FORMBHARAT_DOCUMENT_KEY` is a valid 32-byte key, the number is protected with the existing `FBTEXT1` helper. Without a key, the number stays plaintext. If `FORMBHARAT_REQUIRE_DOCUMENT_ENCRYPTION` is on and the key is missing, the save is rejected. This is not a second encryption scheme, and plaintext mode is not called encrypted.

## What is not stored

The board password, OTP, CAPTCHA, session cookie, authentication token, and Aadhaar. A request that includes those names is rejected and writes nothing.

## Deletion

Deleting a record removes that row, including the consent text and the number. The number is not written to an application log.

## Live portal

Assisted fill still accepts only a local file page. The board page tells the user that live portal fill is unavailable. OTP, CAPTCHA, and final Submit stay with the user. A typed number is labeled user-confirmed, not independently verified.
