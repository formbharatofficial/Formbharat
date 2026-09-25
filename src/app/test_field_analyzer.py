from field_analyzer import FieldAnalyzer


def test_name():
    fields = [{"name": "full_name", "label": "Full Name", "type": "text"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "name"


def test_email():
    fields = [{"name": "email", "label": "Email Address", "type": "email"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "email"


def test_phone():
    fields = [{"name": "mobile", "label": "Mobile Number", "type": "tel"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "phone"


def test_age():
    fields = [{"name": "age", "label": "Age", "type": "number"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "age"


def test_address():
    fields = [{"name": "city", "label": "City", "type": "text"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "address"


def test_country():
    fields = [{"name": "country", "label": "Country", "type": "select"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "country"


def test_father_and_mother_are_not_the_user_name():
    fields = [
        {"name": "father_name", "label": "Father Name", "type": "text"},
        {"name": "mother_name", "label": "Mother Name", "type": "text"},
    ]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "father_name"
    assert result[0]["confidence"] == "high"
    assert result[1]["purpose"] == "mother_name"
    assert result[1]["confidence"] == "high"


def test_date_of_birth_is_not_classified_as_age():
    fields = [{"name": "dob", "label": "Date of Birth", "type": "text"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "dob"
    assert result[0]["confidence"] == "high"


def test_otp_and_captcha_are_blocked_from_understanding():
    fields = [
        {"name": "otp", "label": "OTP", "type": "text"},
        {"name": "captcha", "label": "Captcha", "type": "text"},
    ]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "blocked"
    assert result[1]["purpose"] == "blocked"
    assert result[0]["confidence"] == "high"


def test_profile_fields_keep_their_own_purpose():
    fields = [
        {"name": "gender", "label": "Gender", "type": "select"},
        {"name": "category", "label": "Category", "type": "select"},
        {"name": "qualification", "label": "Qualification", "type": "text"},
        {"name": "state", "label": "State", "type": "text"},
        {"name": "district", "label": "District", "type": "text"},
        {"name": "pincode", "label": "PIN Code", "type": "text"},
        {"name": "nationality", "label": "Nationality", "type": "text"},
    ]

    result = FieldAnalyzer().analyze(fields)
    purposes = [item["purpose"] for item in result]

    assert purposes == [
        "gender",
        "category",
        "qualification",
        "state",
        "district",
        "pincode",
        "nationality",
    ]
    assert all(item["confidence"] == "high" for item in result)


def test_understand_form_does_not_fill_or_submit():
    from app.field_analyzer import understand_form

    html = """
    <form action="/apply" method="post">
        <label for="father_name">Father Name</label>
        <input id="father_name" name="father_name" required>
        <input type="submit" value="Final Submit">
    </form>
    """

    understood = understand_form(html)

    assert understood["forms"][0]["submit_control"] == "user"
    assert understood["forms"][0]["fields"][0]["purpose"] == "father_name"
    assert "profile_value" not in understood["forms"][0]["fields"][0]
    assert all(field["type"] != "submit" for field in understood["forms"][0]["fields"])


def test_guardian_and_spouse_are_not_the_user_name():
    fields = [
        {"name": "guardian_name", "label": "Guardian Name", "type": "text"},
        {"name": "spouse_name", "label": "Spouse Name", "type": "text"},
    ]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "guardian"
    assert result[1]["purpose"] == "spouse"
    assert result[0]["understanding"] == "understood"
    assert "profile_value" not in result[0]


def test_security_code_is_blocked():
    fields = [
        {"name": "verification_code", "label": "Verification Code", "type": "text"},
        {"name": "security_code", "label": "Security Code", "type": "text"},
    ]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "blocked"
    assert result[0]["understanding"] == "blocked"
    assert result[1]["understanding"] == "blocked"


def test_bare_pin_needs_review_and_has_no_value():
    result = FieldAnalyzer().analyze(
        [{"name": "pin", "label": "PIN", "type": "text"}]
    )

    assert result[0]["purpose"] == "pincode"
    assert result[0]["confidence"] == "medium"
    assert result[0]["understanding"] == "needs_review"
    assert "profile_value" not in result[0]


def test_file_input_is_a_document_requirement_only():
    result = FieldAnalyzer().analyze(
        [{"name": "marksheet", "label": "Upload Marksheet", "type": "file"}]
    )

    assert result[0]["purpose"] == "document_requirement"
    assert result[0]["understanding"] == "understood"
    assert "profile_value" not in result[0]


def test_legend_does_not_invent_a_father_value():
    from app.field_analyzer import understand_form

    html = """
    <form>
        <fieldset>
            <legend>Father Details</legend>
            <label for="person_name">Name</label>
            <input id="person_name" name="person_name" type="text">
        </fieldset>
    </form>
    """

    field = understand_form(html)["forms"][0]["fields"][0]

    assert field["legend"] == "Father Details"
    assert field["purpose"] == "name"
    assert "profile_value" not in field


def test_rendered_html_can_be_read_again_after_it_changes():
    from app.field_analyzer import FormReadSession, understand_browser_page

    class Page:
        def __init__(self):
            self.html = "<form><input name='full_name' type='text'></form>"

        def open(self, url):
            assert url == "https://example.test/form"
            return self.html

    page = Page()
    session = FormReadSession()
    first = session.read(page.open("https://example.test/form"))
    assert first["source"] == "rendered_html"
    assert first["filled"] is False
    assert first["submitted"] is False
    assert first["forms"][0]["fields"][0]["purpose"] == "name"

    page.html = "<form><input name='email' type='email'></form>"
    second = session.reread(page.open("https://example.test/form"))

    assert second["forms"][0]["fields"][0]["purpose"] == "email"
    assert session.current["forms"][0]["fields"][0]["purpose"] == "email"
    opened = understand_browser_page(page, "https://example.test/form")
    assert opened["url"] == "https://example.test/form"
    assert opened["filled"] is False
    assert opened["submitted"] is False


def test_unspecified_non_english_label_stays_unknown():
    result = FieldAnalyzer().analyze(
        [{"name": "field_1", "label": "पिता का नाम", "type": "text"}]
    )

    assert result[0]["purpose"] == "unknown"
    assert result[0]["understanding"] == "unknown"
    assert "profile_value" not in result[0]


def test_unknown():
    fields = [{"name": "favorite_color", "label": "Favorite Color", "type": "text"}]

    result = FieldAnalyzer().analyze(fields)

    assert result[0]["purpose"] == "unknown"
    assert result[0]["understanding"] == "unknown"
    assert result[0]["confidence"] == "low"
