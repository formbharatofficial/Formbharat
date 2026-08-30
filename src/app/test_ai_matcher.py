from app.ai_matcher import AIMatcher


ai = AIMatcher()


def test_name_matching():
    result = ai.match("Candidate Name")

    assert result["purpose"] == "name"
    assert result["confidence"] == "high"
    assert result["blocked"] is False


def test_email_matching():
    result = ai.match("Email Address")

    assert result["purpose"] == "email"
    assert result["blocked"] is False


def test_mobile_matching():
    result = ai.match("Mobile Number")

    assert result["purpose"] == "mobile"
    assert result["blocked"] is False


def test_dob_matching():
    result = ai.match("Date of Birth")

    assert result["purpose"] == "dob"
    assert result["blocked"] is False


def test_address_matching():
    result = ai.match("Permanent Address")

    assert result["purpose"] == "address"
    assert result["blocked"] is False


def test_country_matching():
    result = ai.match("Nationality")

    assert result["purpose"] == "country"
    assert result["blocked"] is False


def test_father_name_is_allowed_for_dedicated_profile_value():
    result = ai.match("Father Name")

    assert result["blocked"] is False
    assert result["purpose"] == "father_name"
    assert result["confidence"] == "high"


def test_mother_name_is_allowed_for_dedicated_profile_value():
    result = ai.match("Mother Name")

    assert result["blocked"] is False
    assert result["purpose"] == "mother_name"


def test_guardian_name_is_blocked():
    result = ai.match("Guardian Name")

    assert result["blocked"] is True
    assert result["purpose"] == "blocked"


def test_otp_is_blocked():
    result = ai.match("OTP")

    assert result["blocked"] is True
    assert result["purpose"] == "blocked"
    assert result["reason"] == "otp_or_captcha"


def test_captcha_is_blocked():
    result = ai.match("Captcha")

    assert result["blocked"] is True
    assert result["purpose"] == "blocked"


def test_unknown_field():
    result = ai.match("Random Unknown Field")

    assert result["purpose"] == "unknown"
    assert result["confidence"] == "low"
    assert result["blocked"] is False
