from app.profile_matcher import match_profile_to_fields


def test_profile_matches_basic_fields():
    profile = {
        "name": "Test User",
        "email": "test@example.com",
        "mobile": "9999999999",
        "dob": "1990-01-01",
        "address": "Prayagraj",
        "country": "in"
    }

    fields = [
        {"id": "name", "label": "Full Name", "name": "name"},
        {"id": "email", "label": "Email", "name": "email"},
        {"id": "mobile", "label": "Mobile Number", "name": "mobile"},
        {"id": "dob", "label": "Date of Birth", "name": "dob"},
        {"id": "address", "label": "Address", "name": "address"},
        {"id": "country", "label": "Country", "name": "country"},
    ]

    result = match_profile_to_fields(fields, profile)

    assert result[0]["profile_value"] == "Test User"
    assert result[1]["profile_value"] == "test@example.com"
    assert result[2]["profile_value"] == "9999999999"
    assert result[3]["profile_value"] == "1990-01-01"
    assert result[4]["profile_value"] == "Prayagraj"
    assert result[5]["profile_value"] == "in"


def test_unknown_field_is_not_filled():
    profile = {"name": "Test User"}

    fields = [
        {"id": "unknown_field", "label": "Father Name", "name": "father_name"}
    ]

    result = match_profile_to_fields(fields, profile)

    assert result[0]["matched"] is False
    assert result[0]["profile_value"] is None


def test_father_and_mother_names_use_their_dedicated_profile_values():
    profile = {
        "name": "Test User",
        "father_name": "Test Father",
        "mother_name": "Test Mother",
    }
    fields = [
        {"id": "father_name", "label": "Father Name", "name": "father_name"},
        {"id": "mother_name", "label": "Mother Name", "name": "mother_name"},
    ]

    result = match_profile_to_fields(fields, profile)

    assert result[0]["matched"] is True
    assert result[0]["profile_key"] == "father_name"
    assert result[0]["profile_value"] == "Test Father"
    assert result[1]["matched"] is True
    assert result[1]["profile_key"] == "mother_name"
    assert result[1]["profile_value"] == "Test Mother"


def test_father_and_mother_names_are_not_invented_without_dedicated_values():
    profile = {"name": "Test User"}
    fields = [
        {"id": "father_name", "label": "Father Name", "name": "father_name"},
        {"id": "mother_name", "label": "Mother Name", "name": "mother_name"},
    ]

    result = match_profile_to_fields(fields, profile)

    assert result[0]["matched"] is False
    assert result[0]["profile_value"] is None
    assert result[1]["matched"] is False
    assert result[1]["profile_value"] is None


def test_otp_and_captcha_are_always_blocked():
    profile = {
        "otp": "123456",
        "captcha": "never-fill",
    }
    fields = [
        {"id": "otp", "label": "OTP", "name": "otp"},
        {"id": "captcha", "label": "Captcha", "name": "captcha"},
    ]

    result = match_profile_to_fields(fields, profile)

    assert all(field["matched"] is False for field in result)
    assert all(field["profile_value"] is None for field in result)
    assert all(field["match_confidence"] == "blocked" for field in result)
