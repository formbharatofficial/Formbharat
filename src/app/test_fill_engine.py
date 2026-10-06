from app.fill_engine import fill_form


def _field(**overrides):
    field = {
        "matched": True,
        "profile_key": "name",
        "profile_value": "Bharat",
        "name": "full_name",
        "id": "full_name",
        "type": "text",
        "label": "Full Name",
    }
    field.update(overrides)
    return field


def _result_keys(result):
    return set(result.keys())


def test_return_shape_and_safe_text_fill():
    html = '<form><input id="full_name" name="full_name" type="text"></form>'
    result = fill_form(html, [_field()])

    assert _result_keys(result) == {
        "html",
        "filled",
        "skipped",
        "filled_count",
        "skipped_count",
    }
    assert result["filled_count"] == 1
    assert result["skipped_count"] == 0
    assert result["filled"] == [{
        "field": "full_name",
        "profile_key": "name",
        "value": "Bharat",
    }]
    assert 'value="Bharat"' in result["html"]


def test_unmatched_and_empty_values_are_skipped():
    html = """
    <form>
        <input id="full_name" name="full_name" type="text">
        <input id="email" name="email" type="email">
    </form>
    """
    result = fill_form(html, [
        _field(matched=False),
        _field(name="email", id="email", type="email", profile_value=None),
    ])

    assert result["filled_count"] == 0
    assert result["skipped"] == [
        {"field": "full_name", "reason": "not matched"},
        {"field": "email", "reason": "empty profile value"},
    ]
    assert "Bharat" not in result["html"]


def test_security_fields_are_blocked_when_matched():
    html = """
    <form>
        <label for="otp">Enter OTP</label>
        <input id="otp" name="otp" type="text">
        <label for="captcha_text">CAPTCHA</label>
        <input id="captcha_text" name="captcha_text" type="text">
        <label for="verify">Verification</label>
        <input id="verify" name="verify" type="text">
        <label for="sec">Security Code</label>
        <input id="sec" name="security-code" type="text">
        <input id="secret" name="secret" type="password" placeholder="one-time password">
    </form>
    """
    fields = [
        _field(name="otp", id="otp", label="Enter OTP", profile_value="123456"),
        _field(name="captcha_text", id="captcha_text", label="CAPTCHA", profile_value="AB12"),
        _field(name="verify", id="verify", label="Verification", profile_value="999999"),
        _field(
            name="security-code",
            id="sec",
            label="Security Code",
            profile_value="4455",
        ),
        _field(
            name="secret",
            id="secret",
            label="Code",
            type="password",
            placeholder="one-time password",
            profile_value="7788",
        ),
    ]

    result = fill_form(html, fields)

    assert result["filled"] == []
    assert result["filled_count"] == 0
    assert [item["reason"] for item in result["skipped"]] == ["blocked"] * 5
    for secret in ("123456", "AB12", "999999", "4455", "7788"):
        assert secret not in result["html"]


def test_html_security_control_is_blocked_when_metadata_looks_safe():
    html = """
    <form>
        <label for="code">Mobile OTP</label>
        <input id="code" name="user_code" type="text">
    </form>
    """
    result = fill_form(html, [
        _field(
            name="user_code",
            id="code",
            label="Code",
            profile_value="123456",
        )
    ])

    assert result["filled_count"] == 0
    assert result["skipped"] == [{"field": "user_code", "reason": "blocked"}]
    assert "123456" not in result["html"]


def test_unsafe_controls_are_never_filled_or_activated():
    html = """
    <form>
        <input id="go" name="go" type="submit" value="Send">
        <button id="action" name="action" type="button">Go</button>
        <input id="clear" name="clear" type="reset" value="Reset">
        <input id="marksheet" name="marksheet" type="file">
        <input id="photo" name="photo" type="image" src="go.png">
        <input id="pwd" name="pwd" type="password">
    </form>
    """
    original = html
    fields = [
        _field(name="go", id="go", type="submit", profile_value="Send now"),
        _field(name="action", id="action", type="button", profile_value="clicked"),
        _field(name="clear", id="clear", type="reset", profile_value="Reset now"),
        _field(name="marksheet", id="marksheet", type="file", profile_value="a.pdf"),
        _field(name="photo", id="photo", type="image", profile_value="pressed"),
        _field(name="pwd", id="pwd", type="password", profile_value="secret"),
    ]

    result = fill_form(original, fields)

    assert result["filled"] == []
    assert [item["reason"] for item in result["skipped"]] == ["unsafe control"] * 6
    for leaked in ("Send now", "clicked", "Reset now", "a.pdf", "pressed", "secret"):
        assert leaked not in result["html"]
    assert 'type="submit"' in result["html"]
    assert 'type="file"' in result["html"]
    assert 'type="reset"' in result["html"]


def test_html_unsafe_control_is_not_activated_when_metadata_says_text():
    html = '<form><input id="upload" name="upload" type="file"></form>'
    result = fill_form(html, [
        _field(name="upload", id="upload", type="text", profile_value="a.pdf")
    ])

    assert result["filled_count"] == 0
    assert result["skipped"] == [{"field": "upload", "reason": "unsafe control"}]
    assert "a.pdf" not in result["html"]


def test_supported_data_controls_still_fill():
    html = """
    <form>
        <input id="email" name="email" type="email">
        <textarea id="address" name="address"></textarea>
        <select id="country" name="country">
            <option value="in">India</option>
            <option value="us">USA</option>
        </select>
        <input id="agree" name="agree" type="checkbox" value="yes">
        <input id="gender_m" name="gender" type="radio" value="male">
    </form>
    """
    result = fill_form(html, [
        _field(name="email", id="email", type="email", profile_key="email", profile_value="a@b.in"),
        _field(name="address", id="address", type="textarea", profile_value="Prayagraj"),
        _field(name="country", id="country", type="select", profile_value="in"),
        _field(name="agree", id="agree", type="checkbox", profile_value="yes"),
        _field(name="gender", id="gender_m", type="radio", profile_value="on"),
    ])

    assert result["filled_count"] == 5
    assert result["skipped_count"] == 0
    assert 'value="a@b.in"' in result["html"]
    assert "Prayagraj" in result["html"]
    assert 'value="in" selected' in result["html"] or 'selected' in result["html"]
    assert 'id="agree"' in result["html"] and "checked" in result["html"]


def test_missing_html_field_is_skipped():
    result = fill_form("<form></form>", [_field(name="missing", id="missing")])

    assert result["filled_count"] == 0
    assert result["skipped"] == [{
        "field": "missing",
        "reason": "HTML field not found",
    }]
