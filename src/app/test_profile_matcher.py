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


def test_medium_confidence_match_is_not_filled():
    profile = {"name": "Test User"}
    fields = [
        {"id": "notes", "label": "Enter candidate name carefully", "name": "notes"}
    ]

    result = match_profile_to_fields(fields, profile)

    assert result[0]["profile_key"] == "name"
    assert result[0]["match_confidence"] == "medium"
    assert result[0]["matched"] is False
    assert result[0]["profile_value"] is None


def test_gender_category_place_and_nationality_use_their_own_fields():
    profile = {
        "gender": "Female",
        "category": "OBC",
        "pincode": "211001",
        "district": "Prayagraj",
        "state": "Uttar Pradesh",
        "nationality": "Indian",
        "country": "in",
    }
    fields = [
        {"id": "gender", "label": "Gender", "name": "gender"},
        {"id": "sex", "label": "Sex", "name": "sex"},
        {"id": "category", "label": "Category", "name": "category"},
        {"id": "caste", "label": "Caste", "name": "caste"},
        {"id": "pincode", "label": "Pincode", "name": "pincode"},
        {"id": "pin_code", "label": "Pin Code", "name": "pin_code"},
        {"id": "district", "label": "District", "name": "district"},
        {"id": "state", "label": "State", "name": "state"},
        {"id": "nationality", "label": "Nationality", "name": "nationality"},
        {"id": "country", "label": "Country", "name": "country"},
    ]

    result = match_profile_to_fields(fields, profile)

    assert [(item["profile_key"], item["profile_value"]) for item in result] == [
        ("gender", "Female"),
        ("gender", "Female"),
        ("category", "OBC"),
        ("category", "OBC"),
        ("pincode", "211001"),
        ("pincode", "211001"),
        ("district", "Prayagraj"),
        ("state", "Uttar Pradesh"),
        ("nationality", "Indian"),
        ("country", "in"),
    ]
    assert all(item["matched"] is True for item in result)
    assert all(item["match_confidence"] == "high" for item in result)


def test_dob_stays_separate_from_age():
    profile = {
        "dob": "1990-01-01",
        "age": "36",
    }
    fields = [
        {"id": "dob", "label": "Date of Birth", "name": "dob"},
        {"id": "age", "label": "Age", "name": "age"},
    ]

    result = match_profile_to_fields(fields, profile)

    assert result[0]["matched"] is True
    assert result[0]["profile_key"] == "dob"
    assert result[0]["profile_value"] == "1990-01-01"
    assert result[1]["matched"] is False
    assert result[1]["profile_key"] is None
    assert result[1]["profile_value"] is None


def test_generic_education_is_not_mapped_to_one_qualification():
    profile = {
        "graduation_degree": "B.A.",
        "other_qualification": "Diploma",
        "tenth_percentage": "80",
    }
    fields = [
        {"id": "education", "label": "Education", "name": "education"},
        {"id": "qualification", "label": "Qualification", "name": "qualification"},
    ]

    result = match_profile_to_fields(fields, profile)

    assert result[0]["matched"] is False
    assert result[0]["profile_key"] is None
    assert result[0]["profile_value"] is None
    assert result[1]["matched"] is False
    assert result[1]["profile_key"] is None
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
