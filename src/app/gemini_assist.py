"""Two Gemini steps for a local form.

The planner reads field labels and says what the user must do.
The filler may name a saved profile key for the remaining fields.
Code copies the saved value. The model cannot invent a value, and it
cannot take OTP, CAPTCHA, submit, review, password, payment, or a live camera.
"""

import json
import os
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.profile import PROFILE_FIELDS
from app.runtime_config import gemini_api_key


PLANNER_MODEL = "gemini-3.8-flash"
FILLER_MODEL = "gemini-3.5-flash-lite"
_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_WORDS = re.compile(r"[^a-z0-9\u0900-\u097f]+", re.IGNORECASE)
_USER_WORDS = {
    "otp",
    "captcha",
    "password",
    "submit",
    "review",
    "payment",
    "fee",
    "fees",
    "cvv",
    "webcam",
    "camera",
}
_USER_PHRASES = (
    "verification code",
    "security code",
    "one time password",
    "live photo",
    "live photograph",
    "ओटीपी",
    "कैप्चा",
    "जमा करें",
    "समीक्षा",
    "लाइव फोटो",
)
_UNSAFE_TYPES = {"password", "file", "submit", "button", "reset", "image"}


def _text(field):
    return " ".join([
        str(field.get("label") or ""),
        str(field.get("name") or ""),
        str(field.get("id") or ""),
        str(field.get("placeholder") or ""),
        str(field.get("type") or ""),
    ])


def user_keeps(field):
    """True when this control stays with the person, not the filler."""
    if not isinstance(field, dict):
        return True
    if str(field.get("capture") or "").strip():
        return True
    if str(field.get("type") or "").lower() in _UNSAFE_TYPES:
        return True
    raw = _text(field).lower()
    compact = raw.replace(" ", "")
    if "cardnumber" in compact or "debitcard" in compact or "creditcard" in compact:
        return True
    words = set(_WORDS.split(raw))
    if words & _USER_WORDS:
        return True
    if {"verification", "code"} <= words or {"security", "code"} <= words:
        return True
    if {"one", "time", "password"} <= words:
        return True
    return any(phrase in raw for phrase in _USER_PHRASES)


def _hold(field):
    field["ai_blocked"] = True
    field["ai_block_reason"] = "user_only"
    field["matched"] = False
    field["profile_value"] = None


def _brief(field):
    return {
        "id": field.get("id") or field.get("name") or "",
        "name": field.get("name") or "",
        "label": field.get("label") or "",
        "type": field.get("type") or "",
        "placeholder": field.get("placeholder") or "",
    }


def _key_for(item, fields):
    wanted = str(item.get("id") or item.get("name") or "")
    for field in fields:
        if wanted and wanted in {str(field.get("id") or ""), str(field.get("name") or "")}:
            return field
    return None


def _parse_model_json(text):
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1]
    start = raw.find("[")
    end = raw.rfind("]")
    if start < 0 or end < start:
        return []
    try:
        parsed = json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _post(model, prompt, key):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }).encode("utf-8")
    request = Request(
        _ENDPOINT.format(model=model),
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    parts = payload["candidates"][0]["content"]["parts"]
    return _parse_model_json(parts[0].get("text") or "")


def _http_ask(kind, fields, profile_keys):
    key = gemini_api_key()
    if not key:
        return []
    if kind == "plan":
        model = os.environ.get("FORMBHARAT_GEMINI_PLANNER", PLANNER_MODEL).strip() or PLANNER_MODEL
        prompt = (
            "You only classify form fields. Reply with a JSON array of "
            '{"id","action"} where action is "fill" or "user". '
            "action user is required for OTP, CAPTCHA, password, payment, "
            "submit, review, and any live camera or webcam photo. "
            "Do not invent values.\n"
            + json.dumps(fields, ensure_ascii=False)
        )
    else:
        model = os.environ.get("FORMBHARAT_GEMINI_FILLER", FILLER_MODEL).strip() or FILLER_MODEL
        prompt = (
            "Map each field to one profile key from the allowed list. "
            "Reply with a JSON array of "
            '{"id","profile_key"}. Use an empty profile_key when none fits. '
            "Do not return a person's data, only the key name.\nFields:\n"
            + json.dumps(fields, ensure_ascii=False)
            + "\nAllowed keys:\n"
            + json.dumps(list(profile_keys), ensure_ascii=False)
        )
    return _post(model, prompt, key)


def assist_fields(fields, profile, ask=None):
    """Hold user-only controls, then let Gemini fill what the local rules missed.

    Without an API key, or when the call fails, the local matches stay as they are.
    """
    if not isinstance(fields, list):
        raise ValueError("fields must be a list")
    saved = profile if isinstance(profile, dict) else {}
    for field in fields:
        if isinstance(field, dict) and user_keeps(field):
            _hold(field)

    open_fields = [
        field for field in fields
        if isinstance(field, dict)
        and not field.get("ai_blocked")
        and field.get("matched") is not True
        and str(field.get("type") or "").lower() not in _UNSAFE_TYPES
    ]
    if not open_fields:
        return fields
    if ask is None and not gemini_api_key():
        return fields
    caller = ask or _http_ask
    try:
        plan = caller("plan", [_brief(field) for field in open_fields], [])
        allowed = []
        by_id = {}
        for item in plan:
            if not isinstance(item, dict):
                continue
            field = _key_for(item, open_fields)
            if field is None or user_keeps(field):
                continue
            if str(item.get("action") or "").lower() != "fill":
                continue
            allowed.append(field)
            by_id[id(field)] = field
        if not allowed:
            return fields
        present = [
            key for key in PROFILE_FIELDS
            if str(saved.get(key) or "").strip()
        ]
        filled = caller("fill", [_brief(field) for field in allowed], present)
    except (OSError, URLError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return fields

    for item in filled:
        if not isinstance(item, dict):
            continue
        field = _key_for(item, allowed)
        if field is None or user_keeps(field):
            continue
        profile_key = str(item.get("profile_key") or "").strip()
        if profile_key not in PROFILE_FIELDS:
            continue
        value = str(saved.get(profile_key) or "").strip()
        if not value:
            continue
        field["profile_key"] = profile_key
        field["profile_value"] = value
        field["matched"] = True
        field["match_confidence"] = "high"
        field["ai_purpose"] = profile_key
        field["ai_blocked"] = False
    return fields
