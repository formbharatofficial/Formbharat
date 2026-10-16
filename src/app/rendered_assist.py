"""Assist one local rendered page. This does not open a website or submit."""

import re
from datetime import datetime

from app.ai_matcher import AIMatcher
from app.field_analyzer import FieldAnalyzer
from app.fill_engine import fill_form
from app.form_reader import FormReader
from app.profile_matcher import match_profile_to_fields


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PIN = re.compile(r"^[1-9][0-9]{5}$")
_MOBILE = re.compile(r"^[6-9][0-9]{9}$")
_UNSAFE_TYPES = {"password", "file", "submit", "button", "reset", "image"}
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
_CALLER_PROFILE_KEYS = {"profile", "verified_profile", "html"}


def _local_page(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")
    if not url.strip().lower().startswith("file:"):
        raise ValueError("only a local file page can be assisted")
    return url.strip()


def _valid_date(value):
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        return parsed.strftime(fmt) == value
    return False


def _value_is_valid(field):
    key = field.get("profile_key")
    value = str(field.get("profile_value") or "").strip()
    if key == "email":
        return _EMAIL.fullmatch(value) is not None
    if key == "dob":
        return _valid_date(value)
    if key == "pincode":
        return _PIN.fullmatch(value) is not None
    if key == "mobile":
        return _MOBILE.fullmatch(value) is not None
    return value != ""


def _withhold(field, reason, review):
    review.append({
        "field": field.get("name") or field.get("id"),
        "reason": reason,
    })
    field["matched"] = False
    field["profile_value"] = None


def apply_fill_boundaries(matched_fields):
    """Withhold blocked, uncertain, invalid, and unsafe controls before fill."""
    if not isinstance(matched_fields, list):
        raise ValueError("matched_fields must be a list")

    withheld = []
    for field in matched_fields:
        if not isinstance(field, dict):
            continue
        field_type = str(field.get("type") or "").lower()
        if (
            field.get("ai_blocked")
            or field.get("match_confidence") == "blocked"
            or field_type in _UNSAFE_TYPES
        ):
            _withhold(field, "blocked", withheld)
        elif field.get("matched") is not True:
            _withhold(field, "uncertain", withheld)
        elif not _value_is_valid(field):
            _withhold(field, "invalid", withheld)
    return withheld


def build_review(filled, withheld):
    """Describe what would be filled. This does not submit the form."""
    return {
        "submitted": False,
        "proposed": [
            {
                "field": item.get("field"),
                "profile_key": item.get("profile_key"),
                "value": item.get("value"),
            }
            for item in filled
            if isinstance(item, dict)
        ],
        "withheld": list(withheld),
    }


def _profile_id(profile_id):
    if isinstance(profile_id, bool) or not isinstance(profile_id, int):
        raise ValueError("profile_id must be an integer between 1 and 5")
    if not 1 <= profile_id <= 5:
        raise ValueError("profile_id must be an integer between 1 and 5")
    return profile_id


def _assist_html(local_url, html, verified_profile, documents=None, attachment_dir=None):
    if not isinstance(html, str) or not html.strip():
        raise ValueError("rendered html must be a non-empty string")

    fields = FormReader().read(html)
    analyzed = FieldAnalyzer().analyze(fields) or []
    matcher = AIMatcher()

    for field in analyzed:
        ai_text = " ".join([
            str(field.get("label") or ""),
            str(field.get("name") or ""),
            str(field.get("id") or ""),
            str(field.get("placeholder") or ""),
        ]).strip()
        ai_result = matcher.match(ai_text)
        field["ai_purpose"] = ai_result.get("purpose")
        field["ai_confidence"] = ai_result.get("confidence")
        field["ai_blocked"] = ai_result.get("blocked", False)
        if ai_result.get("reason"):
            field["ai_block_reason"] = ai_result["reason"]

    matched = match_profile_to_fields(analyzed, verified_profile)
    attachments = []
    if documents is not None and attachment_dir is not None:
        from app.form_attachments import plan_attachments
        attachments = plan_attachments(matched, documents, attachment_dir)
    withheld = apply_fill_boundaries(matched)
    filled = fill_form(html, matched)
    return {
        "url": local_url,
        "submitted": False,
        "fields_detected": len(fields),
        "filled_html": filled["html"],
        "filled": filled["filled"],
        "skipped": filled["skipped"],
        "review": build_review(filled["filled"], withheld),
        "filled_count": filled["filled_count"],
        "skipped_count": filled["skipped_count"],
        "attachments": attachments,
    }


def assist_rendered_page(browser, url, verified_profile):
    """Fill one local page from a profile that has already passed the gate.

    Browser assistance entry points must call assist_verified_profile.
    This function does not click controls or submit the form.
    """
    local_url = _local_page(url)
    if verified_profile is not None and not isinstance(verified_profile, dict):
        raise ValueError("verified_profile must be a dictionary or None")
    return _assist_html(local_url, browser.open(local_url), verified_profile)


def assist_verified_profile(browser, url, profile_id, reread=False):
    """Fill a local page from the verified profile stored for profile_id.

    A caller-supplied profile dictionary is not accepted. An unverified
    or missing record reads the page and fills nothing.
    """
    from app.verified_profile import get_verified_profile

    selected = _profile_id(profile_id)
    from app.ownership import assert_slot_access
    assert_slot_access(selected)
    import shutil
    import tempfile

    from app.form_attachments import public_attachments, saved_documents

    local_url = _local_page(url)
    stored = get_verified_profile(selected)
    if reread and callable(getattr(browser, "read_current", None)):
        html = browser.read_current()
    else:
        html = browser.open(local_url)
    documents = saved_documents(selected) if stored is not None else None
    directory = tempfile.mkdtemp(prefix="fb-fit-")
    try:
        result = _assist_html(
            local_url,
            html,
            stored,
            documents=documents,
            attachment_dir=directory,
        )
        if callable(getattr(browser, "attach_files", None)):
            browser.attach_files(result["attachments"])
            if callable(getattr(browser, "keep_prepared_files", None)):
                browser.keep_prepared_files(directory)
                directory = None
        if callable(getattr(browser, "apply_filled", None)):
            browser.apply_filled(result["filled"])
        visible = public_attachments(result["attachments"])
    finally:
        if directory is not None:
            shutil.rmtree(directory, ignore_errors=True)
    result["attachments"] = visible
    result["review"]["attachments"] = visible
    result["profile_id"] = selected
    result["verified_profile"] = stored is not None
    result["submitted"] = False
    return result


def run_local_assist(payload, sessions, browser_factory):
    """Open, reread, or close one local browser session for a profile slot.

    The payload cannot carry profile values or HTML. Reread uses the
    page already open in the session and does not navigate again.
    """
    if not isinstance(payload, dict):
        raise ValueError("request must be a JSON object")
    if any(key in payload for key in _CALLER_PROFILE_KEYS):
        raise ValueError("only a profile_id and local file URL are accepted")
    if not isinstance(sessions, dict):
        raise ValueError("sessions must be a dictionary")

    profile_id = _profile_id(payload.get("profile_id"))
    action = payload.get("action") or "open"
    if action not in {"open", "reread", "close"}:
        raise ValueError("action must be open, reread, or close")

    if action == "close":
        browser = sessions.pop(profile_id, None)
        if browser is not None and callable(getattr(browser, "close", None)):
            browser.close()
        return {"success": True, "closed": True, "submitted": False}

    if action == "reread":
        browser = sessions.get(profile_id)
        if browser is None or not callable(getattr(browser, "read_current", None)):
            raise ValueError("open a local page before rereading it")
        url = getattr(browser, "url", None) or payload.get("url")
        result = assist_verified_profile(browser, url, profile_id, reread=True)
    else:
        url = _local_page(payload.get("url"))
        browser = sessions.get(profile_id)
        if browser is None:
            browser = browser_factory()
            sessions[profile_id] = browser
        result = assist_verified_profile(browser, url, profile_id, reread=False)

    result["success"] = True
    return result


class RenderedAssistSession:
    """Read a local page from the browser, then read it again later.

    Each call asks the browser for the current page. The previous HTML
    is not reused. This does not click Next, fill OTP or CAPTCHA, or submit.
    """

    def __init__(self, browser):
        self._browser = browser

    def read(self, url, profile_id):
        return assist_verified_profile(self._browser, url, profile_id)

    def reread(self, url, profile_id):
        return assist_verified_profile(
            self._browser, url, profile_id, reread=True
        )
