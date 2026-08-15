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
