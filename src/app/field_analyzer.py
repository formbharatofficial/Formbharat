import re


def _understanding(purpose, confidence):
    if purpose == "blocked":
        return "blocked"
    if purpose == "unknown" or confidence == "low":
        return "unknown"
    if confidence == "medium":
        return "needs_review"
    if confidence == "high":
        return "understood"
    return "needs_review"


class FieldAnalyzer:

    def _tokens(self, item):
        text = " ".join([
            str(item.get("name", "")),
            str(item.get("label", "")),
            str(item.get("id", "")),
            str(item.get("placeholder", "")),
            str(item.get("type", "")),
        ]).lower()
        return [
            token for token in re.split(r"[^a-z0-9]+", text)
            if token
        ]

    def _purpose(self, tokens):
        token_set = set(tokens)

        if (
            token_set & {"otp", "captcha"}
            or "verificationcode" in token_set
            or {"verification", "code"} <= token_set
            or {"security", "code"} <= token_set
            or {"one", "time", "password"} <= token_set
        ):
            return "blocked", "high"

        if "guardian" in token_set:
            return "guardian", "high"

        if token_set & {"spouse", "husband", "wife"}:
            return "spouse", "high"

        if "father" in token_set or "fathername" in token_set:
            return "father_name", "high"

        if "mother" in token_set or "mothername" in token_set:
            return "mother_name", "high"

        if (
            "dob" in token_set
            or "birthdate" in token_set
            or {"date", "birth"} <= token_set
        ):
            return "dob", "high"

        if "age" in token_set:
            return "age", "high"

        if (
            "email" in token_set
            or "emailid" in token_set
            or {"e", "mail"} <= token_set
        ):
            return "email", "high"

        if token_set & {"mobile", "phone", "tel"} or (
            "contact" in token_set and "number" in token_set
        ):
            return "phone", "high"

        if "gender" in token_set or "sex" in token_set:
            return "gender", "high"

        if "category" in token_set or "caste" in token_set:
            return "category", "high"

        if token_set & {"qualification", "education", "degree"}:
            return "qualification", "high"

        if "nationality" in token_set:
            return "nationality", "high"

        if token_set & {"pincode", "zip", "zipcode"} or {"pin", "code"} <= token_set:
            return "pincode", "high"

        if "pin" in token_set:
            return "pincode", "medium"

        if "district" in token_set:
            return "district", "high"

        if "state" in token_set:
            return "state", "high"

        if "address" in token_set or "city" in token_set:
            return "address", "high"

        if "country" in token_set:
            return "country", "high"

        if (
            "name" in token_set
            or "fullname" in token_set
            or {"full", "name"} <= token_set
        ):
            return "name", "high"

        return "unknown", "low"

    def analyze(self, fields=None):
        print("Field Analyzer Loaded")

        if fields is None:
            return None

        analyzed = []

        for field in fields:
            if not isinstance(field, dict):
                continue

            item = dict(field)
            if str(item.get("type", "")).lower() == "file":
                purpose, confidence = "document_requirement", "high"
            else:
                purpose, confidence = self._purpose(self._tokens(item))
            item["purpose"] = purpose
            item["confidence"] = confidence
            item["understanding"] = _understanding(purpose, confidence)
            analyzed.append(item)

        return analyzed


def understand_form(html):
    """Read a form page and classify its fields.

    This does not fetch a website, fill a field, or submit a form.
    Legend text is kept on each field and is not used as a value.
    """
    from app.form_reader import FormReader

    structure = FormReader().read_structure(html)
    analyzer = FieldAnalyzer()
    for form in structure["forms"]:
        form["fields"] = analyzer.analyze(form["fields"]) or []
    structure["unattached_fields"] = (
        analyzer.analyze(structure["unattached_fields"]) or []
    )
    structure["filled"] = False
    structure["submitted"] = False
    return structure


def understand_rendered_html(html):
    """Understand HTML already produced by Browser.open.

    This does not launch a browser, fill a field, or submit a form.
    """
    if not isinstance(html, str) or not html.strip():
        raise ValueError("rendered html must be a non-empty string")
    understood = understand_form(html)
    understood["source"] = "rendered_html"
    return understood


def understand_browser_page(browser, url):
    """Read one rendered page from an existing browser opener.

    The opener's open(url) must return HTML. This function does not
    fill or submit that page.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")
    html = browser.open(url)
    understood = understand_rendered_html(html)
    understood["url"] = url
    return understood


class FormReadSession:
    """Read the current rendered form, then read it again after it changes.

    Each call replaces the current understanding. Nothing is filled or clicked.
    """

    def __init__(self):
        self.current = None

    def read(self, html):
        self.current = understand_rendered_html(html)
        return self.current

    def reread(self, html):
        return self.read(html)
