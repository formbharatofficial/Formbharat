from ai_engine import FormBharatAI


def test_about():
    ai = FormBharatAI()
    assert ai.about() is None


def test_analyze():
    ai = FormBharatAI()

    result = ai.analyze(["Name", "Age"])

    assert result == ["Name", "Age"]


def test_match_fields():
    ai = FormBharatAI()

    fields = [
        {
            "name": "name",
            "label": "Full Name",
            "purpose": "name"
        },
        {
            "name": "email",
            "label": "Email",
            "purpose": "email"
        },
        {
            "name": "mobile",
            "label": "Mobile Number",
            "purpose": "phone"
        },
        {
            "name": "dob",
            "label": "Date of Birth",
            "purpose": "age"
        },
        {
            "name": "address",
            "label": "Address",
            "purpose": "address"
        }
    ]

    profile = {
        "name": "Shiva Singh",
        "email": "test@example.com",
        "phone": "9876543210",
        "dob": "20-06-1991",
        "address": "Prayagraj"
    }

    result = ai.match_fields(fields, profile)

    assert result[0]["profile_key"] == "name"
    assert result[0]["profile_value"] == "Shiva Singh"

    assert result[1]["profile_key"] == "email"
    assert result[1]["profile_value"] == "test@example.com"

    assert result[2]["profile_key"] == "phone"
    assert result[2]["profile_value"] == "9876543210"

    assert result[3]["profile_key"] == "dob"
    assert result[3]["profile_value"] == "20-06-1991"

    assert result[4]["profile_key"] == "address"
    assert result[4]["profile_value"] == "Prayagraj"

    assert all(item["matched"] for item in result)


def test_unknown_field():
    ai = FormBharatAI()

    fields = [
        {
            "name": "favorite_color",
            "label": "Favorite Color",
            "type": "text",
            "purpose": "unknown"
        }
    ]

    profile = {
        "name": "Shiva Singh"
    }

    result = ai.match_fields(fields, profile)

    assert result[0]["matched"] is False
    assert result[0]["profile_value"] is None
    assert result[0]["confidence"] == "low"


def test_none_fields():
    ai = FormBharatAI()

    assert ai.match_fields(None, {}) == []
