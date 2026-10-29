import pytest

from app.rendered_assist import assist_rendered_page


PAGE = """
<form>
  <label for="full_name">Full Name</label>
  <input id="full_name" name="full_name" type="text">
  <label for="email">Email</label>
  <input id="email" name="email" type="email">
  <label for="dob">Date of Birth</label>
  <input id="dob" name="dob" type="date">
  <label for="otp">OTP</label>
  <input id="otp" name="otp" type="text">
  <label for="captcha">Captcha</label>
  <input id="captcha" name="captcha" type="text">
  <label for="notes">Random Unknown Field</label>
  <input id="notes" name="notes" type="text">
  <button type="submit" name="submit_application">Submit</button>
</form>
"""


class LocalOpener:
    def __init__(self, html):
        self.html = html
        self.opened = []

    def open(self, url):
        self.opened.append(url)
        return self.html


def _file_url(tmp_path):
    page = tmp_path / "local-form.html"
    page.write_text(PAGE, encoding="utf-8")
    return page.as_uri()


def test_rendered_local_page_fills_only_valid_verified_values(tmp_path):
    opener = LocalOpener(PAGE)
    result = assist_rendered_page(
        opener,
        _file_url(tmp_path),
        {
            "name": "Sunil Kumar",
            "email": "not-an-email",
            "dob": "20-06-1991",
            "otp": "123456",
            "captcha": "AB12",
        },
    )

    assert opener.opened
    assert opener.opened[0].startswith("file:")
    assert result["submitted"] is False
    assert result["fields_detected"] == 6
    filled = {item["field"]: item["value"] for item in result["filled"]}
    assert filled == {"full_name": "Sunil Kumar", "dob": "20-06-1991"}
    assert 'value="Sunil Kumar"' in result["filled_html"]
    assert "not-an-email" not in result["filled_html"]
    assert "123456" not in result["filled_html"]
    assert "AB12" not in result["filled_html"]
    assert result["review"]["submitted"] is False
    reasons = {
        item["field"]: item["reason"]
        for item in result["review"]["withheld"]
    }
    assert reasons["email"] == "invalid"
    assert reasons["otp"] == "blocked"
    assert reasons["captcha"] == "blocked"
    assert reasons["notes"] == "uncertain"
    assert result["review"]["proposed"] == [
        {"field": "full_name", "profile_key": "name", "value": "Sunil Kumar"},
        {"field": "dob", "profile_key": "dob", "value": "20-06-1991"},
    ]
    assert "submit_application" not in filled


def test_missing_verified_profile_fills_nothing(tmp_path):
    result = assist_rendered_page(LocalOpener(PAGE), _file_url(tmp_path), None)

    assert result["submitted"] is False
    assert result["filled_count"] == 0
    assert result["filled"] == []


def test_non_local_url_is_rejected_without_opening():
    opener = LocalOpener(PAGE)

    with pytest.raises(ValueError, match="form page"):
        assist_rendered_page(opener, "javascript:alert(1)", {"name": "A"})

    assert opener.opened == []


def test_https_form_page_is_filled_and_not_submitted():
    opener = LocalOpener(PAGE)
    result = assist_rendered_page(
        opener,
        "https://example.gov.in/apply",
        {"name": "Sunil Kumar"},
    )

    assert opener.opened == ["https://example.gov.in/apply"]
    assert result["submitted"] is False
    filled = {item["field"]: item["value"] for item in result["filled"]}
    assert filled["full_name"] == "Sunil Kumar"
    assert "submit_application" not in filled


def test_reread_discovers_fields_on_the_new_rendered_page(tmp_path, monkeypatch):
    from app import profile as profile_module
    from app import verified_profile
    from app.rendered_assist import RenderedAssistSession

    monkeypatch.setattr(profile_module, "DB_PATH", tmp_path / "verified.db")
    monkeypatch.setattr(verified_profile, "DB_PATH", tmp_path / "verified.db")
    from app import document_vault
    monkeypatch.setattr(document_vault, "DB_PATH", str(tmp_path / "verified.db"))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    verified_profile.save_verified_profile(
        {"name": "Sunil Kumar", "pincode": "211001"},
        profile_id=1,
        verified=True,
    )

    url = _file_url(tmp_path)
    states = [
        """
        <form>
          <label for="full_name">Full Name</label>
          <input id="full_name" name="full_name" type="text">
        </form>
        """,
        """
        <form>
          <label for="pincode">PIN Code</label>
          <input id="pincode" name="pincode" type="text">
          <label for="otp">OTP</label>
          <input id="otp" name="otp" type="text">
          <input id="secret" name="secret" type="password">
          <button type="submit">Submit</button>
        </form>
        """,
    ]

    class LivePage:
        def __init__(self):
            self.calls = []

        def open(self, requested):
            self.calls.append(requested)
            return states[len(self.calls) - 1]

        def click(self, _target):
            raise AssertionError("navigation must stay with the user")

    page = LivePage()
    session = RenderedAssistSession(page)

    first = session.read(url, 1)
    second = session.reread(url, 1)

    assert page.calls == [url, url]
    assert [item["field"] for item in first["filled"]] == ["full_name"]
    assert [item["field"] for item in second["filled"]] == ["pincode"]
    assert "211001" in second["filled_html"]
    assert "123456" not in second["filled_html"]
    assert second["submitted"] is False
    withheld = {item["field"]: item["reason"] for item in second["review"]["withheld"]}
    assert withheld["otp"] == "blocked"
    assert withheld["secret"] == "blocked"
    assert second["review"]["proposed"] == [
        {"field": "pincode", "profile_key": "pincode", "value": "211001"}
    ]


def test_invalid_date_and_pin_stay_unfilled(tmp_path):
    result = assist_rendered_page(
        LocalOpener(
            """
            <form>
              <label for="dob">Date of Birth</label>
              <input id="dob" name="dob" type="date">
              <label for="pincode">PIN Code</label>
              <input id="pincode" name="pincode" type="text">
            </form>
            """
        ),
        _file_url(tmp_path),
        {"dob": "31-02-1991", "pincode": "011001"},
    )

    assert result["filled"] == []
    assert result["review"]["proposed"] == []
    reasons = {item["field"]: item["reason"] for item in result["review"]["withheld"]}
    assert reasons == {"dob": "invalid", "pincode": "invalid"}


def test_radio_and_select_use_only_the_matching_verified_value(tmp_path):
    result = assist_rendered_page(
        LocalOpener(
            """
            <form>
              <label for="gender_male">Gender</label>
              <input id="gender_male" name="gender" type="radio" value="male">
              <input id="gender_female" name="gender" type="radio" value="female">
              <label for="category">Category</label>
              <select id="category" name="category">
                <option value="gen">General</option>
                <option value="obc">OBC</option>
              </select>
            </form>
            """
        ),
        _file_url(tmp_path),
        {"gender": "female", "category": "OBC"},
    )

    filled = {(item["field"], item["value"]) for item in result["filled"]}
    assert ("gender", "female") in filled
    assert ("category", "OBC") in filled
    assert result["review"]["proposed"] == [
        {
            "field": item["field"],
            "profile_key": item["profile_key"],
            "value": item["value"],
        }
        for item in result["filled"]
    ]
    assert 'value="female"' in result["filled_html"]
    assert 'checked="True"' in result["filled_html"]
    assert 'value="male" checked' not in result["filled_html"]
    assert result["submitted"] is False


def test_invalid_mobile_stays_unfilled(tmp_path):
    result = assist_rendered_page(
        LocalOpener(
            """
            <form>
              <label for="mobile">Mobile</label>
              <input id="mobile" name="mobile" type="tel">
            </form>
            """
        ),
        _file_url(tmp_path),
        {"mobile": "12345"},
    )

    assert result["filled"] == []
    reasons = {item["field"]: item["reason"] for item in result["review"]["withheld"]}
    assert reasons["mobile"] == "invalid"


def test_session_rejects_a_caller_supplied_profile(tmp_path):
    from app.rendered_assist import RenderedAssistSession

    class Closed:
        def open(self, _url):
            raise AssertionError("a supplied profile must not open a page")

    with pytest.raises(ValueError, match="profile_id"):
        RenderedAssistSession(Closed()).read(_file_url(tmp_path), {"name": "Attacker"})


def test_unverified_profile_record_fills_nothing(tmp_path, monkeypatch):
    from app import profile as profile_module
    from app import verified_profile
    from app.rendered_assist import assist_verified_profile

    monkeypatch.setattr(profile_module, "DB_PATH", tmp_path / "verified.db")
    monkeypatch.setattr(verified_profile, "DB_PATH", tmp_path / "verified.db")
    from app import document_vault
    monkeypatch.setattr(document_vault, "DB_PATH", str(tmp_path / "verified.db"))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    verified_profile.save_verified_profile(
        {"name": "Not Verified"},
        profile_id=1,
        verified=False,
    )
    result = assist_verified_profile(LocalOpener(PAGE), _file_url(tmp_path), 1)

    assert result["verified_profile"] is False
    assert result["filled"] == []
    assert result["submitted"] is False
    assert "Not Verified" not in result["filled_html"]


def test_live_reread_uses_the_current_dom_without_opening_again(tmp_path, monkeypatch):
    from app import profile as profile_module
    from app import verified_profile
    from app.rendered_assist import run_local_assist

    monkeypatch.setattr(profile_module, "DB_PATH", tmp_path / "verified.db")
    monkeypatch.setattr(verified_profile, "DB_PATH", tmp_path / "verified.db")
    from app import document_vault
    monkeypatch.setattr(document_vault, "DB_PATH", str(tmp_path / "verified.db"))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    verified_profile.save_verified_profile(
        {"name": "Sunil Kumar", "mobile": "9876543210"},
        profile_id=1,
        verified=True,
    )
    url = _file_url(tmp_path)

    class LivePage:
        def __init__(self):
            self.html = """
            <form>
              <label for="full_name">Full Name</label>
              <input id="full_name" name="full_name" type="text">
            </form>
            """
            self.url = None
            self.opens = 0
            self.reads = 0

        def open(self, requested):
            self.opens += 1
            self.url = requested
            return self.html

        def read_current(self):
            self.reads += 1
            return self.html

        def click(self, _target):
            raise AssertionError("navigation must stay with the user")

    page = LivePage()
    sessions = {}
    first = run_local_assist(
        {"url": url, "profile_id": 1},
        sessions,
        lambda: page,
    )
    page.html = """
    <form>
      <label for="mobile">Mobile</label>
      <input id="mobile" name="mobile" type="tel">
      <label for="otp">OTP</label>
      <input id="otp" name="otp" type="text">
    </form>
    """
    second = run_local_assist(
        {"action": "reread", "profile_id": 1, "url": "https://example.test/next"},
        sessions,
        lambda: (_ for _ in ()).throw(AssertionError("reread must reuse the session")),
    )

    assert page.opens == 1
    assert page.reads == 1
    assert [item["field"] for item in first["filled"]] == ["full_name"]
    assert [item["field"] for item in second["filled"]] == ["mobile"]
    assert second["submitted"] is False
    assert "https://example.test" not in second["url"]
    withheld = {item["field"]: item["reason"] for item in second["review"]["withheld"]}
    assert withheld["otp"] == "blocked"
    closed = run_local_assist({"action": "close", "profile_id": 1}, sessions, lambda: page)
    assert closed == {"success": True, "closed": True, "submitted": False}
    assert sessions == {}


def test_local_assist_rejects_profile_payloads_before_opening(tmp_path):
    from app.rendered_assist import run_local_assist

    opened = []

    def factory():
        opened.append("opened")
        raise AssertionError("rejected payloads must not create a browser")

    with pytest.raises(ValueError, match="profile_id and form page URL"):
        run_local_assist(
            {
                "url": _file_url(tmp_path),
                "profile_id": 1,
                "profile": {"name": "Attacker"},
            },
            {},
            factory,
        )
    with pytest.raises(ValueError, match="form page"):
        run_local_assist(
            {"url": "javascript:alert(1)", "profile_id": 1},
            {},
            factory,
        )
    assert opened == []


def test_parent_fields_stay_separate_and_file_upload_is_blocked(tmp_path):
    result = assist_rendered_page(
        LocalOpener(
            """
            <form>
              <label for="father_name">Father Name</label>
              <input id="father_name" name="father_name" type="text">
              <label for="mother_name">Mother Name</label>
              <input id="mother_name" name="mother_name" type="text">
              <label for="guardian_name">Guardian Name</label>
              <input id="guardian_name" name="guardian_name" type="text">
              <label for="photo">Photo</label>
              <input id="photo" name="photo" type="file">
            </form>
            """
        ),
        _file_url(tmp_path),
        {
            "name": "Sunil Kumar",
            "father_name": "Test Father",
            "photo": "not-a-file",
        },
    )

    filled = {item["field"]: item["value"] for item in result["filled"]}
    assert filled == {"father_name": "Test Father"}
    assert "Sunil Kumar" not in result["filled_html"]
    reasons = {
        item["field"]: item["reason"] for item in result["review"]["withheld"]
    }
    assert reasons["mother_name"] == "uncertain"
    assert reasons["guardian_name"] == "uncertain"
    assert reasons["photo"] == "blocked"
    assert result["submitted"] is False


class _ReturnedHtml:
    """Return HTML already produced by Browser.open. Does not browse again."""

    def __init__(self, html):
        self.html = html
        self.opened = []

    def open(self, url):
        self.opened.append(url)
        return self.html


def test_browser_open_rendered_html_is_assisted_for_a_local_file(tmp_path):
    pytest.importorskip(
        "playwright.sync_api",
        reason="Playwright is not installed",
    )
    from app.browser import Browser

    page = tmp_path / "rendered-form.html"
    page.write_text(
        """<!DOCTYPE html>
        <html>
          <head><title>FormBharat Render</title></head>
          <body>
            <p id="marker">waiting</p>
            <script>
              document.getElementById("marker").textContent = "rendered-marker";
            </script>
            <form>
              <label for="full_name">Full Name</label>
              <input id="full_name" name="full_name" type="text">
              <label for="otp">OTP</label>
              <input id="otp" name="otp" type="text">
              <label for="captcha">Captcha</label>
              <input id="captcha" name="captcha" type="text">
              <button type="submit" name="submit_application">Submit</button>
            </form>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    url = page.as_uri()
    assert url.lower().startswith("file:")

    try:
        rendered = Browser().open(url)
    except Exception as error:
        pytest.skip(f"Playwright browser is unavailable: {error}")

    assert "rendered-marker" in rendered
    assert "waiting" not in rendered

    opener = _ReturnedHtml(rendered)
    result = assist_rendered_page(
        opener,
        url,
        {"name": "Sunil Kumar", "otp": "123456", "captcha": "AB12"},
    )

    assert opener.opened == [url]
    assert result["submitted"] is False
    filled = {item["field"]: item["value"] for item in result["filled"]}
    assert filled == {"full_name": "Sunil Kumar"}
    assert "123456" not in result["filled_html"]
    assert "AB12" not in result["filled_html"]
    reasons = {
        item["field"]: item["reason"]
        for item in result["review"]["withheld"]
    }
    assert reasons["otp"] == "blocked"
    assert reasons["captcha"] == "blocked"
    assert "submit_application" not in filled


def test_edge_session_reread_sees_a_field_added_on_the_open_page(tmp_path, monkeypatch):
    pytest.importorskip(
        "playwright.sync_api",
        reason="Playwright is not installed",
    )
    from app import profile as profile_module
    from app import verified_profile
    from app.browser import BrowserSession
    from app.rendered_assist import RenderedAssistSession

    monkeypatch.setattr(profile_module, "DB_PATH", tmp_path / "verified.db")
    monkeypatch.setattr(verified_profile, "DB_PATH", tmp_path / "verified.db")
    from app import document_vault
    monkeypatch.setattr(document_vault, "DB_PATH", str(tmp_path / "verified.db"))
    monkeypatch.setattr(document_vault, "STORAGE_DIR", str(tmp_path / "documents"))
    verified_profile.save_verified_profile(
        {"name": "Sunil Kumar", "mobile": "9876543210"},
        profile_id=1,
        verified=True,
    )
    page = tmp_path / "live-form.html"
    page.write_text(
        """<!DOCTYPE html>
        <html><body>
          <form>
            <label for="full_name">Full Name</label>
            <input id="full_name" name="full_name" type="text">
          </form>
        </body></html>
        """,
        encoding="utf-8",
    )
    browser = BrowserSession()
    try:
        try:
            first = RenderedAssistSession(browser).read(page.as_uri(), 1)
        except Exception as error:
            pytest.skip(f"Playwright browser is unavailable: {error}")
        assert [item["field"] for item in first["filled"]] == ["full_name"]
        browser._page.evaluate(
            """() => {
                const form = document.querySelector("form");
                const label = document.createElement("label");
                label.htmlFor = "mobile";
                label.textContent = "Mobile";
                const input = document.createElement("input");
                input.id = "mobile";
                input.name = "mobile";
                input.type = "tel";
                form.appendChild(label);
                form.appendChild(input);
            }"""
        )
        second = RenderedAssistSession(browser).reread(page.as_uri(), 1)
    finally:
        browser.close()

    assert browser._page is None
    filled = {item["field"]: item["value"] for item in second["filled"]}
    assert filled["full_name"] == "Sunil Kumar"
    assert filled["mobile"] == "9876543210"
    assert "9876543210" in second["filled_html"]
    assert second["submitted"] is False
    assert second["verified_profile"] is True
