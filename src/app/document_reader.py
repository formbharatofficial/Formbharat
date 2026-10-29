"""Read a saved document into fields. The profile is not changed here."""

import re


_DATE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
)
_AADHAAR = re.compile(r"\b(\d{4})\s?(\d{4})\s?(\d{4})\b")
_PAN = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")

_LABELS = (
    ("father_name", ("father", "fathers name", "father's name", "पिता", "पिता का नाम")),
    ("mother_name", ("mother", "mothers name", "mother's name", "माता", "माता का नाम")),
    ("guardian_name", ("guardian", "guardian name", "अभिभावक")),
    ("dob", ("dob", "date of birth", "birth", "जन्म", "जन्म तिथि", "जन्म की तारीख")),
    ("gender", ("gender", "sex", "लिंग")),
    ("address", ("address", "पता")),
    ("roll_number", ("roll", "roll no", "roll number", "रोल")),
    ("passing_year", ("passing year", "year of passing", "उत्तीर्ण")),
    ("class", ("class", "कक्षा")),
    ("name", ("name", "kame", "applicant name", "candidate name", "नाम")),
)


def _clean(value):
    return " ".join(str(value or "").replace(":", " ").split())


def _line_key(line):
    folded = _clean(line).lower().strip(" .-")
    if not folded:
        return None
    for key, names in _LABELS:
        for name in names:
            if folded == name or folded.startswith(name + " "):
                return key
    return None


def _value_on_line(line, key):
    folded = _clean(line)
    lower = folded.lower()
    names = sorted(dict(_LABELS)[key], key=len, reverse=True)
    for name in names:
        if lower.startswith(name):
            return folded[len(name):].strip(" :-'")
    return ""


def _plausible_name(value):
    text = _clean(value)
    if not text or len(text) > 80:
        return False
    if _DATE.search(text) or _PAN.search(text) or _AADHAAR.search(text):
        return False
    if _line_key(text):
        return False
    letters = re.sub(r"[^A-Za-z\u0900-\u097F]", "", text)
    return len(letters) >= 2


def _normalize_gender(value):
    text = _clean(value).lower()
    if text in {"m", "male", "पुरुष"}:
        return "male"
    if text in {"f", "female", "महिला"}:
        return "female"
    if "trans" in text or text in {"other", "अन्य"}:
        return "other"
    return ""


def _apply_context(data, lines):
    window = " ".join(lines).lower()
    roll = data.get("roll_number") or ""
    year = data.get("passing_year") or ""
    if not roll and not year:
        return
    if any(word in window for word in ("10th", "matric", "secondary", "दसवीं")):
        if roll:
            data["tenth_roll_number"] = roll
        if year:
            data["tenth_passing_year"] = year
    elif any(word in window for word in ("12th", "intermediate", "senior secondary", "बारहवीं")):
        if roll:
            data["twelfth_roll_number"] = roll
        if year:
            data["twelfth_passing_year"] = year
    elif "graduation" in window or "degree" in window or "स्नातक" in window:
        if roll:
            data["graduation_roll_number"] = roll
        if year:
            data["graduation_passing_year"] = year


def read_document_text(extracted_text):
    """Turn OCR text into fields. Unknown lines stay only in raw_text."""
    text = extracted_text or ""
    data = {
        "name": "",
        "father_name": "",
        "mother_name": "",
        "guardian_name": "",
        "dob": "",
        "gender": "",
        "address": "",
        "class": "",
        "roll_number": "",
        "passing_year": "",
        "aadhaar_number": "",
        "pan_number": "",
        "document_kind": "document",
        "raw_text": text,
    }
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    index = 0
    while index < len(lines):
        line = lines[index]
        key = _line_key(line)
        if key is None:
            alone = _normalize_gender(line)
            if alone and _clean(line).lower() in {"m", "f", "male", "female", "पुरुष", "महिला"}:
                data["gender"] = data["gender"] or alone
            care = re.search(r"\b(?:S|D)\s*/\s*O\b\s*[:\-]?\s*(.+)$", line, re.IGNORECASE)
            if care and _plausible_name(care.group(1).split(",")[0]):
                data["father_name"] = data["father_name"] or _clean(care.group(1).split(",")[0])
            index += 1
            continue
        value = _value_on_line(line, key)
        if not value and index + 1 < len(lines) and _line_key(lines[index + 1]) is None:
            value = lines[index + 1].strip(" :-")
            index += 1
        if key == "dob":
            found = _DATE.search(value) or _DATE.search(line)
            if found:
                data["dob"] = data["dob"] or found.group(1)
        elif key == "gender":
            data["gender"] = data["gender"] or _normalize_gender(value)
        elif key == "address":
            parts = [value] if value else []
            look = index + 1
            while look < len(lines) and look < index + 4 and _line_key(lines[look]) is None:
                parts.append(lines[look])
                look += 1
            data["address"] = data["address"] or _clean(" ".join(parts))[:200]
        elif key == "passing_year":
            found = _YEAR.search(value)
            if found:
                data["passing_year"] = data["passing_year"] or found.group(1)
        elif key in {"name", "father_name", "mother_name", "guardian_name"}:
            if _plausible_name(value):
                data[key] = data[key] or _clean(value)
        elif key == "roll_number":
            token = re.search(r"[A-Za-z0-9][A-Za-z0-9/-]{2,}", value)
            if token:
                data["roll_number"] = data["roll_number"] or token.group(0)
        elif key == "class" and value:
            data["class"] = data["class"] or _clean(value)[:40]
        index += 1

    pan = _PAN.search(text.upper())
    if pan:
        data["pan_number"] = pan.group(1).upper()
    aadhaar = _AADHAAR.search(text)
    if aadhaar:
        data["aadhaar_number"] = "".join(aadhaar.groups())
    if not data["dob"]:
        found = _DATE.search(text)
        if found:
            data["dob"] = found.group(1)

    lowered = text.lower()
    if data["pan_number"] or "permanent account" in lowered or "income tax" in lowered:
        data["document_kind"] = "pan"
    elif data["aadhaar_number"] or "aadhaar" in lowered or "aadhar" in lowered or "आधार" in text:
        data["document_kind"] = "aadhaar"
    elif data["roll_number"] or "marksheet" in lowered or "marks" in lowered:
        data["document_kind"] = "marksheet"
    _apply_context(data, lines)
    return data
