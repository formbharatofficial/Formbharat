from app.gemini_assist import assist_fields, user_keeps


def _field(**values):
    field = {
        "name": "",
        "id": "",
        "type": "text",
        "label": "",
        "placeholder": "",
        "capture": "",
        "matched": False,
        "profile_value": None,
    }
    field.update(values)
    return field


def test_otp_captcha_submit_review_and_live_camera_stay_with_the_user():
    fields = [
        _field(id="otp", label="OTP", matched=True, profile_value="123456"),
        _field(id="captcha", label="CAPTCHA"),
        _field(id="go", type="submit", label="Submit"),
        _field(id="review", type="button", label="Review"),
        _field(id="live", type="file", label="Live photograph", capture="user"),
        _field(id="pay", label="Payment fee"),
    ]
    for field in fields:
        assert user_keeps(field) is True

    assist_fields(fields, {"name": "Asha"}, ask=lambda *args: (_ for _ in ()).throw(AssertionError("no model")))

    assert all(field["matched"] is False for field in fields)
    assert all(field["profile_value"] is None for field in fields)


def test_filler_can_use_only_a_saved_profile_key():
    name = _field(id="applicant_name", label="आवेदक का नाम")
    calls = []

    def ask(kind, fields, keys):
        calls.append(kind)
        if kind == "plan":
            return [{"id": "applicant_name", "action": "fill"}]
        return [
            {"id": "applicant_name", "profile_key": "name", "value": "Invented Person"},
            {"id": "applicant_name", "profile_key": "not_a_field"},
        ]

    assist_fields([name], {"name": "Asha Singh"}, ask=ask)

    assert calls == ["plan", "fill"]
    assert name["matched"] is True
    assert name["profile_key"] == "name"
    assert name["profile_value"] == "Asha Singh"


def test_planner_cannot_mark_otp_as_fill():
    otp = _field(id="otp_code", label="Enter OTP")
    name = _field(id="full_name", label="Full name")

    def ask(kind, fields, keys):
        ids = [item["id"] for item in fields]
        assert "otp_code" not in ids
        if kind == "plan":
            return [
                {"id": "otp_code", "action": "fill"},
                {"id": "full_name", "action": "fill"},
            ]
        return [
            {"id": "otp_code", "profile_key": "mobile"},
            {"id": "full_name", "profile_key": "name"},
        ]

    assist_fields([otp, name], {"name": "Asha", "mobile": "9876543210"}, ask=ask)

    assert otp["matched"] is False
    assert otp["profile_value"] is None
    assert name["profile_value"] == "Asha"


def test_missing_key_does_not_call_the_network(monkeypatch):
    monkeypatch.setattr("app.runtime_config.load_env_file", lambda path=None: None)
    for name in ("FORMBHARAT_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    name = _field(id="full_name", label="Full name", matched=True, profile_key="name", profile_value="Asha")

    assist_fields([name], {"name": "Asha"})

    assert name["profile_value"] == "Asha"
    assert name["matched"] is True
