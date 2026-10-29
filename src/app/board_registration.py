"""SSC OTR and RRB Candidate Account records.

Live pages on ssc.gov.in and rrbapply.gov.in are not assisted. Local
file assist is a different feature and is not treated as portal support.

A registration number is stored only after explicit consent. Declining
does not write a row. Deletion removes that row, including its consent
text. The board password, OTP, CAPTCHA, cookies, tokens, and Aadhaar are
never stored.

Checked 2026-10-28:
- SSC home: https://ssc.gov.in/
- SSC candidate portal: https://ssc.gov.in/candidate-portal/one-time-registration
- SSC OTR flow: https://ssc.gov.in/api/attachment/uploads/masterData/SpecialInstructions/One_Time_Registration_flow%201.pdf
- SSC notice that old ssc.nic.in OTR is void (19.02.2024): https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/OTR_Notice_22022024.pdf
- SSC edit-OTR notice (08.10.2025): https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_08102025.pdf
- RRB FAQ naming rrbapply.gov.in and Create an Account: https://www.rrbcdg.gov.in/uploads/2025/05-JE/052025JE-ApplicationFAQs.pdf
- RRB portal named by that FAQ: https://www.rrbapply.gov.in/

Those PDFs do not publish one fixed registration-number pattern. The
identifier check below is only a length and character limit.
"""

import os
import re
import sqlite3
from datetime import datetime, timezone

from app.document_encryption import (
    TEXT_PREFIX,
    DocumentStorageError,
    protect_text,
    reveal_text,
)
from app.profile import (
    MAX_PROFILES,
    get_profile,
    _validate_profile_id,
)
from app.runtime_config import database_path
from app.verified_profile import get_verified_profile


CONSENT_VERSION = "2026-10-28.1"
SOURCES_CHECKED = "2026-10-28"
LIVE_PORTAL_ASSIST = "unavailable"

_NUMBER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{3,63}$")
_FORBIDDEN = {
    "password",
    "board_password",
    "otp",
    "captcha",
    "cookie",
    "cookies",
    "session",
    "session_cookie",
    "token",
    "auth_token",
    "authentication_token",
    "aadhaar",
    "aadhar",
    "uid",
}

_LABELS = {
    "name": ("नाम", "Name"),
    "father_name": ("पिता का नाम", "Father's name"),
    "mother_name": ("माता का नाम", "Mother's name"),
    "dob": ("जन्म तिथि", "Date of birth"),
    "mobile": ("मोबाइल नंबर", "Mobile number"),
    "email": ("ईमेल", "Email"),
    "category": ("श्रेणी", "Category"),
    "nationality": ("नागरिकता", "Nationality"),
    "address": ("पता", "Address"),
    "state": ("राज्य", "State"),
    "district": ("जिला", "District"),
    "pincode": ("पिन कोड", "PIN code"),
    "gender": ("लिंग", "Gender"),
    "tenth_roll_number": ("मैट्रिक रोल नंबर", "Matriculation roll number"),
}


def _field(key):
    hindi, english = _LABELS[key]
    return {"key": key, "label_hi": hindi, "label_en": english}


_SSC_FIELDS = (
    "name", "father_name", "mother_name", "dob", "mobile", "email",
    "category", "nationality", "address", "state", "district", "pincode",
)
_RRB_FIELDS = (
    "name", "father_name", "mother_name", "dob", "gender", "nationality",
    "tenth_roll_number", "email", "mobile",
)

BOARDS = {
    "ssc": {
        "board": "ssc",
        "record_type": "ssc_otr",
        "account_name_hi": "वन टाइम रजिस्ट्रेशन (OTR)",
        "account_name_en": "One Time Registration (OTR)",
        "board_name_hi": "कर्मचारी चयन आयोग",
        "board_name_en": "Staff Selection Commission",
        "portal_url": "https://ssc.gov.in/candidate-portal/one-time-registration",
        "portal_home": "https://ssc.gov.in/",
        "live_portal_assist": LIVE_PORTAL_ASSIST,
        "sources_checked": SOURCES_CHECKED,
        "fields": [_field(key) for key in _SSC_FIELDS],
        "portal_only": [
            {
                "label_hi": "आधार नंबर केवल आधिकारिक पेज पर लिखें। FormBharat इसे सेव नहीं करता।",
                "label_en": "Type the Aadhaar number only on the official page. FormBharat does not save it.",
            },
            {
                "label_hi": "पहचान चिह्न और विकलांगता का विवरण प्रोफाइल में नहीं है। उसे आधिकारिक पेज पर लिखें।",
                "label_en": "Identification mark and disability details are not in the profile. Enter them on the official page.",
            },
        ],
        "steps_hi": [
            "ssc.gov.in खोलें। होमपेज पर जो स्क्राइब वाला OTR है, वह आपका उम्मीदवार OTR नहीं है।",
            "Login or Register दबाएँ, फिर Register Now।",
            "नाम, माता-पिता का नाम और जन्म तिथि आप खुद लिखें। मोबाइल और ईमेल का OTP आप खुद डालें।",
            "आधिकारिक पेज OTP के बाद रजिस्ट्रेशन नंबर दिखाता है। वही नंबर बाद में यहाँ लिखें।",
            "आधिकारिक निर्देश के अनुसार अधूरी OTR 14 दिन में मिट सकती है।",
        ],
        "steps_en": [
            "Open ssc.gov.in. The scribe OTR on the home page is not your candidate OTR.",
            "Choose Login or Register, then Register Now.",
            "Enter your name, parent names, and date of birth yourself. Enter the mobile and email OTP yourself.",
            "The official page shows the registration number after the OTP. Type that number here afterwards.",
            "Official instructions say an unfinished OTR can be removed after 14 days.",
        ],
        "edit_warning_hi": "08.10.2025 की SSC सूचना के अनुसार OTR संपादन की सुविधा उस तारीख से उपलब्ध है। फिर भी बदलने से पहले आधिकारिक पेज पर जाँच लें।",
        "edit_warning_en": "An SSC notice dated 08.10.2025 says OTR editing is available from that date. Still check the official page before relying on a later change.",
    },
    "rrb": {
        "board": "rrb",
        "record_type": "rrb_candidate_account",
        "account_name_hi": "उम्मीदवार खाता",
        "account_name_en": "Candidate Account",
        "board_name_hi": "रेलवे भर्ती बोर्ड",
        "board_name_en": "Railway Recruitment Board",
        "portal_url": "https://www.rrbapply.gov.in/",
        "portal_home": "https://www.rrbcdg.gov.in/",
        "live_portal_assist": LIVE_PORTAL_ASSIST,
        "sources_checked": SOURCES_CHECKED,
        "fields": [_field(key) for key in _RRB_FIELDS],
        "portal_only": [
            {
                "label_hi": "मैट्रिक प्रमाणपत्र का सीरियल नंबर और तारीख प्रोफाइल में नहीं है।",
                "label_en": "The matriculation certificate serial number and date are not in the profile.",
            },
            {
                "label_hi": "आधार ई-केवाईसी और चुना हुआ RRB केवल आधिकारिक पेज पर चुनें। FormBharat इन्हें सेव नहीं करता।",
                "label_en": "Choose Aadhaar e-KYC and the RRB only on the official page. FormBharat does not save them.",
            },
        ],
        "steps_hi": [
            "rrbapply.gov.in खोलें। यह SSC OTR नहीं है।",
            "Apply में Create an Account चुनें।",
            "अपना मोबाइल और अपना ईमेल लिखें। OTP आप खुद डालें। पासवर्ड आधिकारिक पेज पर ही रखें।",
            "RRB के आधिकारिक FAQ के अनुसार खाता बनने के बाद Create an Account की जानकारी बदली नहीं जा सकती।",
        ],
        "steps_en": [
            "Open rrbapply.gov.in. This is not an SSC One Time Registration.",
            "Under Apply, choose Create an Account.",
            "Use your own mobile number and email. Enter the OTP yourself. Keep the password on the official page.",
            "RRB's official FAQ says Create an Account details cannot be edited after the account is created.",
        ],
        "edit_warning_hi": "RRB FAQ: नाम, माता-पिता का नाम, जन्म तिथि, लिंग, नागरिकता, मैट्रिक विवरण, ईमेल, मोबाइल और चुना हुआ RRB खाता बनने के बाद नहीं बदलते।",
        "edit_warning_en": "RRB FAQ: name, parent names, date of birth, gender, nationality, matriculation details, email, mobile, and the chosen RRB cannot be edited after the account is created.",
    },
}

_CONSENT_TEXT = {
    "hi": (
        "FormBharat इस प्रोफाइल स्लॉट पर बोर्ड का नाम, आपके लिखे रजिस्ट्रेशन नंबर, "
        "स्थिति user-confirmed, और सहमति का समय सेव करेगा। अगली बार उसी बोर्ड "
        "के फॉर्म में यही नंबर दिखाया जाएगा। इस पेज पर देख और मिटा सकते हैं। "
        "बोर्ड का पासवर्ड, OTP, CAPTCHA और आधार सेव नहीं होगा। "
        "अनुमति न दें तो कुछ सेव नहीं होगा।"
    ),
    "en": (
        "FormBharat will save the board name, the registration number you type, "
        "the status user-confirmed, and the time of this permission on this "
        "profile slot. The same number can be shown the next time you use this "
        "board. You can view or delete it on this page. The board password, "
        "OTP, CAPTCHA, and Aadhaar are not saved. If you do not allow this, "
        "nothing is saved."
    ),
}


class BoardRegistrationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _connect():
    return sqlite3.connect(database_path())


def _now():
    return datetime.now(timezone.utc).isoformat()


def init_board_registration_db():
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS board_registration_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                owner_user_id INTEGER,
                board TEXT NOT NULL,
                record_type TEXT NOT NULL,
                registration_number TEXT NOT NULL,
                status TEXT NOT NULL,
                confirmation_source TEXT NOT NULL,
                account_path TEXT NOT NULL,
                consent_version TEXT NOT NULL,
                consent_text TEXT NOT NULL,
                consent_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(profile_id, board)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _profile_id(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise BoardRegistrationError(
            "profile",
            f"profile_id must be an integer between 1 and {MAX_PROFILES}",
        )
    try:
        _validate_profile_id(value)
    except ValueError as error:
        raise BoardRegistrationError("profile", str(error)) from error
    return value


def _assert_access(profile_id):
    from app.ownership import SlotAccessError, assert_slot_access

    try:
        assert_slot_access(profile_id)
    except SlotAccessError as error:
        raise BoardRegistrationError("forbidden_slot", str(error)) from error


def _has_forbidden(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).strip().lower() in _FORBIDDEN or _has_forbidden(item):
                return True
        return False
    if isinstance(value, list):
        return any(_has_forbidden(item) for item in value)
    return False


def _owner_clause(owner_user_id):
    if owner_user_id is None:
        return "owner_user_id IS NULL", ()
    return "(owner_user_id = ? OR owner_user_id IS NULL)", (owner_user_id,)


def _current_owner():
    from app.ownership import current_user_id
    return current_user_id()


def board_config(board):
    selected = str(board or "").strip().lower()
    if selected not in BOARDS:
        raise BoardRegistrationError("board", "board is not supported")
    config = dict(BOARDS[selected])
    config["fields"] = [dict(item) for item in BOARDS[selected]["fields"]]
    config["portal_only"] = [dict(item) for item in BOARDS[selected]["portal_only"]]
    config["steps_hi"] = list(BOARDS[selected]["steps_hi"])
    config["steps_en"] = list(BOARDS[selected]["steps_en"])
    return config


def list_board_configs():
    return [board_config(board) for board in ("ssc", "rrb")]


def requirement_for_vacancy(vacancy):
    """Use the stored field only. A job title never selects the board."""
    if not isinstance(vacancy, dict):
        return {"state": "ask", "board": "", "record_type": ""}
    raw = str(vacancy.get("registration_board") or "").strip().lower()
    if raw == "none":
        return {"state": "skip", "board": "", "record_type": ""}
    if raw in BOARDS:
        return {
            "state": "required",
            "board": raw,
            "record_type": BOARDS[raw]["record_type"],
        }
    return {"state": "ask", "board": "", "record_type": ""}


def _document_flags(profile_id):
    flags = {"photo": "missing", "signature": "missing"}
    if not os.path.exists(database_path()):
        return flags
    conn = _connect()
    try:
        found = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'documents'"
        ).fetchone()
        if found is None:
            return flags
        rows = conn.execute(
            """
            SELECT doc_type, verified
            FROM documents
            WHERE profile_id = ? AND doc_type IN ('photo', 'signature')
            """,
            (profile_id,),
        ).fetchall()
    except sqlite3.Error:
        return flags
    finally:
        conn.close()
    for doc_type, verified in rows:
        if doc_type not in flags:
            continue
        if verified:
            flags[doc_type] = "verified"
        elif flags[doc_type] == "missing":
            flags[doc_type] = "saved"
    return flags


def review_profile(profile_id, board):
    profile_id = _profile_id(profile_id)
    config = board_config(board)
    _assert_access(profile_id)
    verified = get_verified_profile(profile_id)
    raw = get_profile(profile_id)
    copy_fields = []
    missing = []
    conflicts = []
    verified_ready = isinstance(verified, dict)
    for field in config["fields"]:
        key = field["key"]
        verified_value = ""
        if verified_ready:
            verified_value = str(verified.get(key) or "").strip()
        raw_value = str(raw.get(key) or "").strip()
        item = dict(field)
        if (
            verified_value
            and raw_value
            and verified_value.casefold() != raw_value.casefold()
        ):
            item["verified_value"] = verified_value
            item["profile_value"] = raw_value
            conflicts.append(item)
            continue
        if not verified_value:
            missing.append(dict(field))
            continue
        item["value"] = verified_value
        copy_fields.append(item)
    if not verified_ready:
        profile_state = "unverified"
    elif missing or conflicts:
        profile_state = "incomplete"
    else:
        profile_state = "ready"
    config["profile_state"] = profile_state
    config["copy_fields"] = copy_fields
    config["missing"] = missing
    config["conflicts"] = conflicts
    config["documents"] = _document_flags(profile_id)
    config["consent_version"] = CONSENT_VERSION
    config["consent_text_hi"] = _CONSENT_TEXT["hi"]
    config["consent_text_en"] = _CONSENT_TEXT["en"]
    return config


def _public_record(row):
    stored = row["registration_number"]
    encrypted = isinstance(stored, str) and stored.startswith(TEXT_PREFIX)
    number = reveal_text(stored) if encrypted else ("" if stored is None else str(stored))
    if encrypted and number == "" and stored:
        readable = False
        number = ""
    else:
        readable = number != ""
    return {
        "id": row["id"],
        "profile_id": row["profile_id"],
        "board": row["board"],
        "record_type": row["record_type"],
        "registration_number": number if readable else "",
        "number_readable": readable,
        "number_storage": "encrypted" if encrypted else "plaintext",
        "status": row["status"],
        "confirmation": "user_confirmed_not_independently_verified",
        "account_path": row["account_path"],
        "consent_version": row["consent_version"],
        "consent_at": row["consent_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_records(profile_id):
    profile_id = _profile_id(profile_id)
    _assert_access(profile_id)
    init_board_registration_db()
    clause, params = _owner_clause(_current_owner())
    conn = _connect()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""
            SELECT * FROM board_registration_records
            WHERE profile_id = ? AND {clause}
            ORDER BY board
            """,
            (profile_id, *params),
        ).fetchall()
    finally:
        conn.close()
    return [_public_record(row) for row in rows]


def _clean_number(value):
    number = str(value or "").strip()
    if _NUMBER.fullmatch(number) is None:
        raise BoardRegistrationError(
            "number",
            "registration number must be a short identifier",
        )
    return number


def save_record(profile_id, payload):
    profile_id = _profile_id(profile_id)
    if not isinstance(payload, dict):
        raise BoardRegistrationError("json", "Invalid or missing JSON data")
    if _has_forbidden(payload):
        raise BoardRegistrationError("forbidden", "That value cannot be saved.")
    board = str(payload.get("board") or "").strip().lower()
    config = board_config(board)
    _assert_access(profile_id)
    if payload.get("consent") is not True:
        return {"saved": False, "persisted": False}

    language = str(payload.get("consent_language") or "").strip().lower()
    if language not in _CONSENT_TEXT:
        raise BoardRegistrationError("consent", "consent language is not supported")
    path = str(payload.get("account_path") or "").strip().lower()
    if path not in {"existing", "new"}:
        raise BoardRegistrationError("path", "account_path is not supported")
    number = _clean_number(payload.get("registration_number"))
    try:
        stored_number = protect_text(number)
    except DocumentStorageError as error:
        raise BoardRegistrationError("storage", "The record was not saved.") from error

    owner = _current_owner()
    now = _now()
    replace = payload.get("replace") is True
    shared = (
        config["record_type"],
        stored_number,
        "user_confirmed",
        "user",
        path,
        CONSENT_VERSION,
        _CONSENT_TEXT[language],
        now,
    )
    init_board_registration_db()
    conn = _connect()
    try:
        existing = conn.execute(
            """
            SELECT id FROM board_registration_records
            WHERE profile_id = ? AND board = ?
            """,
            (profile_id, board),
        ).fetchone()
        if existing is not None and not replace:
            raise BoardRegistrationError(
                "duplicate",
                "A saved record already exists for this board.",
            )
        if existing is None:
            cursor = conn.execute(
                """
                INSERT INTO board_registration_records (
                    profile_id, owner_user_id, board, record_type,
                    registration_number, status, confirmation_source,
                    account_path, consent_version, consent_text,
                    consent_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (profile_id, owner, board, *shared, now, now),
            )
            record_id = cursor.lastrowid
        else:
            clause, params = _owner_clause(owner)
            cursor = conn.execute(
                f"""
                UPDATE board_registration_records
                SET record_type = ?, registration_number = ?, status = ?,
                    confirmation_source = ?, account_path = ?,
                    consent_version = ?, consent_text = ?, consent_at = ?,
                    updated_at = ?
                WHERE id = ? AND profile_id = ? AND {clause}
                """,
                (*shared, now, existing[0], profile_id, *params),
            )
            if cursor.rowcount != 1:
                raise BoardRegistrationError(
                    "duplicate",
                    "A saved record already exists for this board.",
                )
            record_id = existing[0]
        conn.commit()
    except BoardRegistrationError:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as error:
        conn.rollback()
        raise BoardRegistrationError(
            "duplicate",
            "A saved record already exists for this board.",
        ) from error
    except sqlite3.Error as error:
        conn.rollback()
        raise BoardRegistrationError("storage", "The record was not saved.") from error
    finally:
        conn.close()
    saved = next(item for item in list_records(profile_id) if item["id"] == record_id)
    return {"saved": True, "persisted": True, "record": saved}


def delete_record(profile_id, record_id):
    profile_id = _profile_id(profile_id)
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id < 1:
        raise BoardRegistrationError("record", "record id is not valid")
    _assert_access(profile_id)
    init_board_registration_db()
    clause, params = _owner_clause(_current_owner())
    conn = _connect()
    try:
        cursor = conn.execute(
            f"""
            DELETE FROM board_registration_records
            WHERE id = ? AND profile_id = ? AND {clause}
            """,
            (record_id, profile_id, *params),
        )
        conn.commit()
        deleted = cursor.rowcount == 1
    except sqlite3.Error as error:
        conn.rollback()
        raise BoardRegistrationError("storage", "The record was not deleted.") from error
    finally:
        conn.close()
    if not deleted:
        raise BoardRegistrationError("missing", "Record not found")
    return {"deleted": True}


def register_board_routes(app, viewer_slot):
    from flask import jsonify, redirect, request, url_for

    from app.vacancy import get_vacancy

    init_board_registration_db()

    def _json_error(error):
        status = 400
        if error.code == "duplicate":
            status = 409
        elif error.code == "storage":
            status = 503
        elif error.code in {"forbidden_slot", "missing"}:
            status = 403 if error.code == "forbidden_slot" else 404
        return jsonify({
            "success": False,
            "error": str(error),
            "code": error.code,
        }), status

    @app.route("/board-registration")
    def board_registration_page():
        raw_id = request.args.get("vacancy_id", "")
        if str(raw_id).isdigit():
            vacancy = get_vacancy(int(raw_id))
            if vacancy is None:
                return redirect(url_for("vacancies_page"))
            if requirement_for_vacancy(vacancy).get("state") == "required":
                return redirect(url_for("apply_account", vacancy_id=int(raw_id)))
            return redirect(url_for("apply_check", vacancy_id=int(raw_id)))
        return redirect(url_for("vacancies_page"))

    @app.route("/api/board-registration/boards", methods=["GET"])
    def board_registration_boards():
        return jsonify({"success": True, "boards": list_board_configs()})

    @app.route("/api/board-registration/requirement", methods=["GET"])
    def board_registration_requirement():
        raw_id = request.args.get("vacancy_id", "")
        if raw_id == "":
            return jsonify({
                "success": True,
                "requirement": requirement_for_vacancy({}),
            })
        if not str(raw_id).isdigit():
            return jsonify({
                "success": False,
                "error": "vacancy_id must be a positive integer",
                "code": "vacancy",
            }), 400
        vacancy = get_vacancy(int(raw_id))
        if vacancy is None:
            return jsonify({
                "success": False,
                "error": "Vacancy not found",
                "code": "vacancy",
            }), 404
        return jsonify({
            "success": True,
            "requirement": requirement_for_vacancy(vacancy),
            "title": vacancy.get("title") or "",
        })

    @app.route("/api/board-registration/review", methods=["GET"])
    def board_registration_review():
        try:
            profile_id = request.args.get("profile_id", type=int)
            if request.args.get("profile_id") in {None, ""}:
                raise BoardRegistrationError(
                    "profile",
                    f"profile_id must be an integer between 1 and {MAX_PROFILES}",
                )
            review = review_profile(profile_id, request.args.get("board"))
        except BoardRegistrationError as error:
            return _json_error(error)
        review["success"] = True
        return jsonify(review)

    @app.route("/api/board-registration/records/<int:profile_id>", methods=["GET"])
    def board_registration_list(profile_id):
        try:
            records = list_records(profile_id)
        except BoardRegistrationError as error:
            return _json_error(error)
        return jsonify({"success": True, "records": records})

    @app.route("/api/board-registration/records/<int:profile_id>", methods=["POST"])
    def board_registration_save(profile_id):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({
                "success": False,
                "error": "Invalid or missing JSON data",
                "code": "json",
            }), 400
        try:
            result = save_record(profile_id, payload)
        except BoardRegistrationError as error:
            return _json_error(error)
        result["success"] = True
        return jsonify(result), 201 if result.get("saved") else 200

    @app.route(
        "/api/board-registration/records/<int:profile_id>/<int:record_id>",
        methods=["DELETE"],
    )
    def board_registration_delete(profile_id, record_id):
        try:
            result = delete_record(profile_id, record_id)
        except BoardRegistrationError as error:
            return _json_error(error)
        result["success"] = True
        return jsonify(result)
