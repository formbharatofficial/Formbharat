import re

from bs4 import BeautifulSoup


SAFE_TEXT_TYPES = {"", "text", "email", "tel", "number", "date", "search", "url"}
UNSAFE_TYPES = {"submit", "button", "reset", "image", "file", "password"}


def _words(text):
    return [
        token for token in re.split(r"[^a-z0-9]+", str(text or "").lower())
        if token
    ]


def _is_security(*parts):
    tokens = []
    for part in parts:
        tokens.extend(_words(part))
    if not tokens:
        return False

    token_set = set(tokens)
    compact = "".join(tokens)
    if token_set & {"otp", "captcha", "verification"}:
        return True
    if "otp" in compact or "captcha" in compact or "verification" in compact:
        return True
    if (
        "verificationcode" in compact
        or "securitycode" in compact
        or "onetimepassword" in compact
    ):
        return True
    if {"verification", "code"} <= token_set:
        return True
    if {"security", "code"} <= token_set:
        return True
    if {"one", "time", "password"} <= token_set:
        return True
    return False


def _skip(skipped, field, reason):
    skipped.append({
        "field": field.get("name") or field.get("id"),
        "reason": reason,
    })


def _field_security(field):
    return _is_security(
        field.get("name"),
        field.get("id"),
        field.get("label"),
        field.get("placeholder"),
        field.get("type"),
        field.get("purpose"),
    )


def _tag_security(tag, soup):
    label = ""
    tag_id = tag.get("id")
    if tag_id:
        lbl = soup.find("label", attrs={"for": tag_id})
        if lbl is not None:
            label = lbl.get_text(" ", strip=True)
    parent_label = tag.find_parent("label")
    if parent_label is not None:
        label = (label + " " + parent_label.get_text(" ", strip=True)).strip()
    return _is_security(
        tag.get("name"),
        tag.get("id"),
        tag.get("placeholder"),
        tag.get("type"),
        tag.get("aria-label"),
        label,
        tag.get_text(" ", strip=True) if tag.name == "button" else "",
    )


def _is_unsafe_control(tag):
    if tag.name == "button":
        return True
    if tag.name != "input":
        return False
    return str(tag.get("type") or "").lower() in UNSAFE_TYPES


def fill_form(html, matched_fields):
    """Write matched profile values into a copy of the HTML form.

    OTP, CAPTCHA, verification, and security-code fields are skipped even
    when matched is true. Submit, button, reset, file-upload, and similar
    controls are never filled or activated.
    """

    if not isinstance(html, str):
        raise ValueError("html must be a string")

    if not isinstance(matched_fields, list):
        raise ValueError("matched_fields must be a list")

    soup = BeautifulSoup(html, "html.parser")

    filled = []
    skipped = []

    for field in matched_fields:

        if not isinstance(field, dict):
            continue

        field_name = str(field.get("name") or "").strip()
        field_id = str(field.get("id") or "").strip()
        field_type = str(field.get("type") or "").lower()

        if _field_security(field):
            _skip(skipped, field, "blocked")
            continue

        if field_type in UNSAFE_TYPES:
            _skip(skipped, field, "unsafe control")
            continue

        if field.get("matched") is not True:
            _skip(skipped, field, "not matched")
            continue

        value = field.get("profile_value")

        if value is None:
            _skip(skipped, field, "empty profile value")
            continue

        tag = None

        if field_id:
            tag = soup.find(id=field_id)

        if tag is None and field_name:
            tag = soup.find(
                ["input", "textarea", "select"],
                attrs={"name": field_name}
            )

        if tag is None:
            _skip(skipped, field, "HTML field not found")
            continue

        if _tag_security(tag, soup):
            _skip(skipped, field, "blocked")
            continue

        if _is_unsafe_control(tag):
            _skip(skipped, field, "unsafe control")
            continue

        tag_name = tag.name.lower()
        tag_type = str(tag.get("type") or "").lower()

        # ------------------------------------------
        # SELECT
        # ------------------------------------------

        if tag_name == "select":

            for option in tag.find_all("option"):
                option_value = option.get("value", "")

                if str(option_value) == str(value):
                    option["selected"] = True
                else:
                    option.attrs.pop("selected", None)

        # ------------------------------------------
        # CHECKBOX / RADIO
        # ------------------------------------------

        elif tag_name == "input" and tag_type in (
            "checkbox",
            "radio"
        ):

            if str(value).lower() in (
                "true",
                "1",
                "yes",
                "on"
            ):
                tag["checked"] = True
            else:
                tag.attrs.pop("checked", None)

        # ------------------------------------------
        # NORMAL INPUT / TEXTAREA
        # ------------------------------------------

        elif tag_name == "textarea" or (
            tag_name == "input" and tag_type in SAFE_TEXT_TYPES
        ):
            tag["value"] = str(value)

            if tag_name == "textarea":
                tag.clear()
                tag.append(str(value))

        else:
            _skip(skipped, field, "unsupported control")
            continue

        filled.append({
            "field": field_name or field_id,
            "profile_key": field.get("profile_key"),
            "value": value
        })

    return {
        "html": str(soup),
        "filled": filled,
        "skipped": skipped,
        "filled_count": len(filled),
        "skipped_count": len(skipped)
    }
