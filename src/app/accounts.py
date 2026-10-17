"""Local accounts. Registration does not claim any profile slot."""

import re
import sqlite3
from datetime import datetime, timezone

from flask import jsonify, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.profile import init_db


def _db_path():
    from app import profile
    return profile.DB_PATH
from app.request_guard import issue_csrf_token


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8

_LOGO = """
<svg class="fb-mark" viewBox="0 0 140 120" aria-hidden="true"><rect x="40" y="14" width="44" height="56" rx="5" fill="none" stroke="#1b4f9c" stroke-width="4.5"/><path d="M50 30h24M50 39h24M50 48h15" stroke="#1b4f9c" stroke-width="3" stroke-linecap="round"/><path d="M16 84c24-36 52-38 84-8" fill="none" stroke="#f58220" stroke-width="9" stroke-linecap="round"/><path d="M22 100c24-28 54-24 78 8" fill="none" stroke="#14913d" stroke-width="9" stroke-linecap="round"/><g transform="translate(98,44)"><circle r="16" fill="#fff" stroke="#0a3d91" stroke-width="2"/><circle r="3.2" fill="#0a3d91"/><circle r="11.5" fill="none" stroke="#0a3d91" stroke-width="1.3" stroke-dasharray="1.5 2.3"/></g></svg>
"""

ACCOUNT_PAGE = """
<!doctype html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat</title>
<style>
body.fb-gate{margin:0;padding:0;background:#eef4f8;font-family:"Segoe UI",system-ui,sans-serif;color:#17345c}
body.fb-gate .fb-header,body.fb-gate .fb-nav,body.fb-gate .fb-flag-wave{display:none}
.fb-stage{position:relative;max-width:430px;min-height:100vh;margin:0 auto;background:#fff;display:flex;flex-direction:column;box-shadow:0 0 40px rgba(22,50,79,.08)}
.fb-wave-top{position:absolute;left:0;top:0;width:100%;height:150px;pointer-events:none}
.fb-wave-bottom{position:relative;display:block;width:100%;height:120px;margin-top:auto;pointer-events:none}
.fb-back{position:relative;z-index:2;align-self:flex-start;margin:18px 0 0 16px;width:36px;height:36px;border-radius:50%;display:grid;place-items:center;color:#17345c;text-decoration:none;font-size:1.3rem;font-weight:700}
.fb-brand-block{position:relative;z-index:2;text-align:center;padding:8px 24px 0}
.fb-mark{width:108px;height:92px}
.fb-word{margin:2px 0 0;font-size:1.95rem;font-weight:800;letter-spacing:-.04em;line-height:1}
.fb-word span:first-child{color:#12833a}
.fb-word span:last-child{color:#ef8b14}
.fb-tagline{margin:6px 0 0;color:#1d4e89;font-weight:700;line-height:1.35}
.fb-sheet{position:relative;z-index:2;margin:18px 16px 24px;padding:18px 16px 16px;background:#fff;border:1px solid #e7eef6;border-radius:22px;box-shadow:0 10px 28px rgba(22,50,79,.06)}
.fb-register{position:relative;z-index:2;padding:8px 16px 28px}
.fb-register h1,.fb-sheet h1{margin:0 0 6px;text-align:center;font-size:1.45rem}
.fb-sub{margin:0 0 14px;text-align:center;color:#5d7088}
.fb-alert{background:#fff4f4;color:#9d174d;border-radius:12px;padding:10px 12px;margin:0 0 12px}
body.fb-gate label{display:block;margin:12px 0 6px;color:#24507a;font-weight:800;font-size:.95rem}
.fb-field{position:relative}
body.fb-gate .fb-field input{width:100%;box-sizing:border-box;border:1px solid #e1e8f0;background:#fff;border-radius:16px;min-height:52px;padding:14px 44px 14px 46px;font-size:16px;color:#17345c}
.fb-ico{position:absolute;left:14px;top:14px;width:22px;height:22px;color:#7b8da3}
body.fb-gate button.fb-eye{position:absolute;right:8px;top:8px;width:36px;min-height:36px;margin:0;padding:0;border:0;border-radius:10px;background:transparent;color:#7b8da3;font-weight:700}
body.fb-gate button.fb-go{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;box-sizing:border-box;margin-top:16px;min-height:54px;border:0;border-radius:16px;background:#12833a;color:#fff;font-size:1.08rem;font-weight:800}
body.fb-gate .fb-forgot{display:block;width:auto;min-height:0;margin:8px 0 0 auto;padding:0;border:0;background:transparent;color:#1d6fe8;font-weight:700;font-size:.92rem;text-align:right;text-decoration:none}
.fb-ok{background:#e7f8ee;color:#0f6d2e;border-radius:12px;padding:10px 12px;margin:0 0 12px}
.fb-split{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center;color:#8aa0b5;margin:16px 0}
.fb-split::before,.fb-split::after{content:"";height:1px;background:#e1e8f0}
.fb-outline{display:flex;align-items:center;justify-content:center;min-height:52px;border:1.5px solid #b7e4c7;border-radius:16px;color:#12833a;text-decoration:none;font-weight:800}
.fb-check{display:flex;gap:10px;align-items:flex-start;margin-top:14px;color:#24507a;font-weight:600}
body.fb-gate .fb-check input{width:18px;height:18px;margin-top:3px;padding:0}
.fb-links{color:#1d6fe8}
.fb-note{color:#5d7088;font-size:.92rem}
.fb-grow{flex:1}
</style>
</head>
<body class="fb-gate">
<div class="fb-stage">
<svg class="fb-wave-top" viewBox="0 0 400 160" preserveAspectRatio="none" aria-hidden="true"><path d="M0 0h210C170 48 140 86 200 130 110 46 50 16 0 84Z" fill="#ff9a1f"/><path d="M0 0h140C130 56 80 84 60 140 30 74 8 36 0 92Z" fill="#ffb24d"/></svg>
{% if not email and mode in ["register", "reset"] %}
<a class="fb-back" href="/account" aria-label="Back">←</a>
{% elif not email %}
<a class="fb-back" href="/" aria-label="Back">←</a>
{% else %}
<a class="fb-back" href="/" aria-label="Home">←</a>
{% endif %}
<div class="fb-brand-block">
""" + _LOGO + """
<p class="fb-word"><span>Form</span><span>Bharat</span></p>
<p class="fb-tagline">Government Forms,<br>Ab aur bhi Aasaan</p>
</div>
{% if email %}
<div class="fb-sheet">
<h1>आप अंदर हैं</h1>
<p class="fb-sub">{{ email }}</p>
{% if notice %}<p class="fb-alert">{{ notice }}</p>{% endif %}
{% if error %}<p class="fb-alert">{{ error }}</p>{% endif %}
<form method="POST" action="{{ logout_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button class="fb-go" type="submit">लॉग आउट</button>
</form>
<p class="fb-note">My Profile खोलने पर खाली slot अपने-आप मिल जाता है। पुरानी भरी हुई प्रोफाइल तभी जुड़ेगी जब आप खुद पुष्टि करें।</p>
{% for slot in slots %}
{% if slot.mine %}
<p class="fb-note">आपकी एक प्रोफाइल Documents, Applications और Auto Fill में इस्तेमाल होगी।</p>
{% elif slot.status == "legacy_locked" %}
<form method="POST" action="{{ adopt_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<input type="hidden" name="profile_id" value="{{ slot.id }}">
<p class="fb-note">पुरानी प्रोफाइल {{ slot.id }}{% if slot.name %}: {{ slot.name }}{% endif %}</p>
<label class="fb-check"><input name="confirm_adopt" type="checkbox" value="yes"> यह मेरी प्रोफाइल है</label>
<button class="fb-go" type="submit">इस अकाउंट से जोड़ें</button>
</form>
{% endif %}
{% endfor %}
</div>
{% elif mode == "register" %}
<div class="fb-register">
<h1>नया अकाउंट बनाएं</h1>
<p class="fb-sub">अपनी जानकारी दर्ज करके FormBharat से जुड़ें</p>
{% if error %}<p class="fb-alert">{{ error }}</p>{% endif %}
<form method="POST" action="{{ register_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label>पूरा नाम *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="3.2"/><path d="M5 19c1.4-3 3.8-4.5 7-4.5S17.6 16 19 19"/></svg>
<input name="full_name" autocomplete="name" placeholder="अपना पूरा नाम दर्ज करें" required>
</div>
<label>मोबाइल नंबर *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="8" y="3" width="8" height="18" rx="2"/><path d="M11 18h2"/></svg>
<input name="mobile" inputmode="numeric" autocomplete="tel" placeholder="मोबाइल नंबर दर्ज करें" required>
</div>
<label>ईमेल *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="6" width="18" height="12" rx="2"/><path d="M4 7l8 6 8-6"/></svg>
<input name="email" type="email" autocomplete="username" placeholder="ईमेल दर्ज करें" required>
</div>
<label>पासवर्ड *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V8a4 4 0 0 1 8 0v2"/></svg>
<input id="reg-password" name="password" type="password" minlength="8" autocomplete="new-password" placeholder="पासवर्ड बनाएं" required>
<p class="fb-note">कम से कम 8 अक्षर।</p>
<button class="fb-eye" type="button" data-eye="reg-password" aria-label="Show password">◉</button>
</div>
<label>पासवर्ड दुबारा दर्ज करें *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V8a4 4 0 0 1 8 0v2"/></svg>
<input id="reg-confirm" name="confirm_password" type="password" autocomplete="new-password" placeholder="पासवर्ड फिर से दर्ज करें" required>
<button class="fb-eye" type="button" data-eye="reg-confirm" aria-label="Show password">◉</button>
</div>
<label class="fb-check"><input name="accept_terms" type="checkbox" value="yes" required> <span>मैं समझता हूँ कि OTP, CAPTCHA और final Submit मेरे पास रहेंगे। <span class="fb-links">Terms</span> और <span class="fb-links">Privacy</span> इसी ऐप के नियम हैं।</span></label>
<button class="fb-go" type="submit">अकाउंट बनाएं <span aria-hidden="true">→</span></button>
</form>
</div>
{% elif mode == "reset" %}
<div class="fb-register">
<h1>पासवर्ड बदलें</h1>
<p class="fb-sub">जिस ईमेल से अकाउंट बना है, वही डालें। नया पासवर्ड यहीं सेट हो जाएगा।</p>
{% if error %}<p class="fb-alert">{{ error }}</p>{% endif %}
<form method="POST" action="{{ reset_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label>ईमेल *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="6" width="18" height="12" rx="2"/><path d="M4 7l8 6 8-6"/></svg>
<input name="email" type="email" autocomplete="username" placeholder="ईमेल दर्ज करें" required>
</div>
<label>नया पासवर्ड *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V8a4 4 0 0 1 8 0v2"/></svg>
<input id="reset-password" name="password" type="password" minlength="8" autocomplete="new-password" placeholder="नया पासवर्ड" required>
<button class="fb-eye" type="button" data-eye="reset-password" aria-label="Show password">◉</button>
</div>
<p class="fb-note">कम से कम 8 अक्षर।</p>
<label>पासवर्ड दुबारा दर्ज करें *</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V8a4 4 0 0 1 8 0v2"/></svg>
<input id="reset-confirm" name="confirm_password" type="password" minlength="8" autocomplete="new-password" placeholder="पासवर्ड फिर से दर्ज करें" required>
<button class="fb-eye" type="button" data-eye="reset-confirm" aria-label="Show password">◉</button>
</div>
<button class="fb-go" type="submit">पासवर्ड बदलें <span aria-hidden="true">→</span></button>
</form>
</div>
{% else %}
<div class="fb-sheet">
{% if notice %}<p class="fb-ok">{{ notice }}</p>{% endif %}
{% if error %}<p class="fb-alert">{{ error }}</p>{% endif %}
<form method="POST" action="{{ login_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label>मोबाइल नंबर या ईमेल</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="3.2"/><path d="M5 19c1.4-3 3.8-4.5 7-4.5S17.6 16 19 19"/></svg>
<input name="email" autocomplete="username" placeholder="मोबाइल नंबर या ईमेल दर्ज करें" required>
</div>
<label>पासवर्ड</label>
<div class="fb-field">
<svg class="fb-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V8a4 4 0 0 1 8 0v2"/></svg>
<input id="login-password" name="password" type="password" autocomplete="current-password" placeholder="पासवर्ड दर्ज करें" required>
<button class="fb-eye" type="button" data-eye="login-password" aria-label="Show password">◉</button>
</div>
<a class="fb-forgot" href="{{ reset_url }}">पासवर्ड भूल गए?</a>
<button class="fb-go" type="submit">Login करें <span aria-hidden="true">→</span></button>
</form>
<p class="fb-split">या</p>
<a class="fb-outline" href="/account/register">नया अकाउंट बनाएं (Register करें) <span aria-hidden="true">→</span></a>
</div>
{% endif %}
<div class="fb-grow"></div>
<svg class="fb-wave-bottom" viewBox="0 0 400 150" preserveAspectRatio="none" aria-hidden="true"><path d="M0 36c80-28 150 12 220 18 80 6 120-16 180-22v118H0Z" fill="#ff9933"/><path d="M0 68c80-24 150 10 220 14 70 4 120-12 180-16v84H0Z" fill="#fff"/><path d="M0 102c70-20 150 8 220 10 70 2 120-8 180-12v50H0Z" fill="#138808"/></svg>
</div>
<script>
document.querySelectorAll("[data-eye]").forEach(function (button) {
    button.addEventListener("click", function () {
        var input = document.getElementById(button.getAttribute("data-eye"));
        if (!input) return;
        input.type = input.type === "password" ? "text" : "password";
    });
});
</script>
</body>
</html>
"""


def init_accounts():
    init_db()
    connection = sqlite3.connect(_db_path())
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                mobile TEXT NOT NULL DEFAULT ''
            )
            """
        )
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(users)")
        }
        if "full_name" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT ''"
            )
        if "mobile" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN mobile TEXT NOT NULL DEFAULT ''"
            )
        connection.commit()
    finally:
        connection.close()


def _clean_email(email):
    value = str(email or "").strip().lower()
    if not _EMAIL.fullmatch(value):
        raise ValueError("Email is not valid.")
    return value


def _clean_password(password):
    value = "" if password is None else str(password)
    if len(value) < MIN_PASSWORD:
        raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
    return value


def _clean_name(value):
    text = " ".join(str(value or "").split())
    if len(text) > 80:
        raise ValueError("Full name is too long.")
    return text


def _clean_mobile(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if not digits:
        return ""
    if not re.fullmatch(r"[6-9][0-9]{9}", digits):
        raise ValueError("Mobile number is not valid.")
    return digits


def _hindi_error(error):
    return {
        "Email is not valid.": "ईमेल सही नहीं है। Login ईमेल से होता है।",
        f"Password must be at least {MIN_PASSWORD} characters.": f"पासवर्ड कम से कम {MIN_PASSWORD} अक्षरों का रखें।",
        "No account for that email.": "इस ईमेल का अकाउंट नहीं मिला।",
        "An account with that email already exists.": "इस ईमेल का अकाउंट पहले से है।",
        "Password confirmation does not match.": "दोनों पासवर्ड एक जैसे नहीं हैं।",
        "Full name is required.": "पूरा नाम दर्ज करें।",
        "Full name is too long.": "नाम बहुत लंबा है।",
        "Mobile number is not valid.": "मोबाइल नंबर 10 अंकों का होना चाहिए।",
        "Terms must be accepted.": "आगे बढ़ने से पहले नियम स्वीकार करें।",
        "Email or password is incorrect.": "ईमेल या पासवर्ड सही नहीं है।",
    }.get(str(error), str(error))


def register_user(email, password, full_name="", mobile=""):
    clean_email = _clean_email(email)
    clean_password = _clean_password(password)
    clean_name = _clean_name(full_name)
    clean_mobile = _clean_mobile(mobile)
    init_accounts()
    connection = sqlite3.connect(_db_path())
    try:
        existing = connection.execute(
            "SELECT 1 FROM users WHERE email = ?",
            (clean_email,),
        ).fetchone()
        if existing is not None:
            raise ValueError("An account with that email already exists.")
        cursor = connection.execute(
            """
            INSERT INTO users (email, password_hash, created_at, full_name, mobile)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                clean_email,
                generate_password_hash(clean_password),
                datetime.now(timezone.utc).isoformat(),
                clean_name,
                clean_mobile,
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def authenticate(email, password):
    try:
        clean_email = _clean_email(email)
    except ValueError:
        return None
    supplied = "" if password is None else str(password)
    init_accounts()
    connection = sqlite3.connect(_db_path())
    try:
        row = connection.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (clean_email,),
        ).fetchone()
    finally:
        connection.close()
    if row is None or not check_password_hash(row[1], supplied):
        return None
    return int(row[0])


def reset_password(email, password):
    clean_email = _clean_email(email)
    clean_password = _clean_password(password)
    init_accounts()
    connection = sqlite3.connect(_db_path())
    try:
        row = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (clean_email,),
        ).fetchone()
        if row is None:
            raise ValueError("No account for that email.")
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(clean_password), int(row[0])),
        )
        connection.commit()
    finally:
        connection.close()


def user_email(user_id):
    init_accounts()
    connection = sqlite3.connect(_db_path())
    try:
        row = connection.execute(
            "SELECT email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()
    return None if row is None else row[0]


def start_session(user_id):
    session.clear()
    session["user_id"] = int(user_id)


def end_session():
    session.pop("user_id", None)


def _slot_name(profile_id):
    from app.profile import get_profile

    try:
        saved = get_profile(profile_id)
    except (TypeError, ValueError):
        return ""
    return str((saved or {}).get("name") or "").strip()


def _account_context(notice="", error="", mode="login"):
    from app.ownership import claim_status, current_user_id, profile_owner

    user_id = current_user_id()
    email = user_email(user_id) if user_id is not None else None
    slots = []
    if email:
        for profile_id in (1,):
            owner = profile_owner(profile_id)
            slots.append({
                "id": profile_id,
                "status": claim_status(profile_id),
                "name": _slot_name(profile_id),
                "mine": owner is not None and owner == user_id,
            })
    return {
        "email": email,
        "notice": notice,
        "error": error,
        "slots": slots,
        "csrf_token": issue_csrf_token(),
        "register_url": url_for("account_register"),
        "login_url": url_for("account_login"),
        "logout_url": url_for("account_logout"),
        "claim_url": url_for("account_claim"),
        "adopt_url": url_for("account_adopt"),
        "reset_url": url_for("account_reset"),
        "mode": mode,
    }


def register_account_routes(app):
    init_accounts()

    @app.route("/account", methods=["GET"])
    def account_page():
        notice = ""
        if request.args.get("reset") == "1":
            notice = "पासवर्ड बदल गया। नए पासवर्ड से login करें।"
        return render_template_string(
            ACCOUNT_PAGE, **_account_context(notice=notice)
        )

    @app.route("/account/reset", methods=["GET", "POST"])
    def account_reset():
        if request.method == "GET":
            return render_template_string(
                ACCOUNT_PAGE, **_account_context(mode="reset")
            )
        try:
            if request.form.get("password") != request.form.get("confirm_password"):
                raise ValueError("Password confirmation does not match.")
            reset_password(
                request.form.get("email"),
                request.form.get("password"),
            )
        except ValueError as error:
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error=_hindi_error(error), mode="reset"),
            ), 400
        return redirect(url_for("account_page", reset=1))

    @app.route("/account/register", methods=["GET", "POST"])
    def account_register():
        if request.method == "GET":
            return render_template_string(
                ACCOUNT_PAGE, **_account_context(mode="register")
            )
        try:
            if request.form.get("password") != request.form.get("confirm_password"):
                raise ValueError("Password confirmation does not match.")
            if request.form.get("accept_terms") != "yes":
                raise ValueError("Terms must be accepted.")
            full_name = _clean_name(request.form.get("full_name"))
            if len(full_name) < 2:
                raise ValueError("Full name is required.")
            mobile = _clean_mobile(request.form.get("mobile"))
            if not mobile:
                raise ValueError("Mobile number is not valid.")
            user_id = register_user(
                request.form.get("email"),
                request.form.get("password"),
                full_name,
                mobile,
            )
        except ValueError as error:
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error=_hindi_error(error), mode="register"),
            ), 400
        start_session(user_id)
        return redirect(url_for("home"))

    @app.route("/account/login", methods=["POST"])
    def account_login():
        entered = request.form.get("email")
        if entered and "@" not in str(entered):
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error=_hindi_error("Email is not valid.")),
            ), 400
        user_id = authenticate(
            entered,
            request.form.get("password"),
        )
        if user_id is None:
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error=_hindi_error("Email or password is incorrect.")),
            ), 401
        start_session(user_id)
        return redirect(url_for("home"))

    @app.route("/account/logout", methods=["POST"])
    def account_logout():
        end_session()
        return redirect(url_for("account_page"))

    @app.route("/account/claim", methods=["POST"])
    def account_claim():
        from app.ownership import SlotAccessError, claim_empty_slot

        try:
            profile_id = int(request.form.get("profile_id", ""))
            claim_empty_slot(
                profile_id,
                request.form.get("claim_code"),
                request.form.get("confirm_claim") == "yes",
            )
        except (TypeError, ValueError):
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error="Slot claim was rejected."),
            ), 400
        except SlotAccessError as error:
            return render_template_string(
                ACCOUNT_PAGE, **_account_context(error=str(error))
            ), 403
        return redirect(url_for("account_page"))

    @app.route("/account/adopt", methods=["POST"])
    def account_adopt():
        from app.ownership import SlotAccessError, adopt_legacy_slot

        messages = {
            "Confirm that this old profile is yours.": "पहले टिक करें कि यह आपकी प्रोफाइल है।",
            "Sign in before attaching an old profile.": "पहले login करें।",
            "That profile already belongs to an account.": "यह प्रोफाइल पहले से किसी अकाउंट की है।",
            "That slot has no saved profile to attach.": "इस slot में पुरानी प्रोफाइल नहीं है।",
            "That profile could not be attached.": "प्रोफाइल नहीं जुड़ सकी।",
        }
        try:
            profile_id = int(request.form.get("profile_id", ""))
            adopt_legacy_slot(
                profile_id,
                request.form.get("confirm_adopt") == "yes",
            )
        except (TypeError, ValueError):
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error="प्रोफाइल संख्या सही नहीं है।"),
            ), 400
        except SlotAccessError as error:
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error=messages.get(str(error), str(error))),
            ), 403
        return redirect(url_for("profile_page"))

    @app.post("/api/account/register")
    def account_register_api():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "Invalid or missing JSON data",
            }), 400
        try:
            user_id = register_user(data.get("email"), data.get("password"))
        except ValueError as error:
            return jsonify({"success": False, "error": str(error)}), 400
        start_session(user_id)
        return jsonify({
            "success": True,
            "authenticated_account": True,
            "claimed_slots": [],
        })

    @app.post("/api/account/login")
    def account_login_api():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "Invalid or missing JSON data",
            }), 400
        user_id = authenticate(data.get("email"), data.get("password"))
        if user_id is None:
            return jsonify({
                "success": False,
                "error": "Email or password is incorrect.",
            }), 401
        start_session(user_id)
        return jsonify({"success": True, "authenticated_account": True})

    @app.post("/api/account/logout")
    def account_logout_api():
        end_session()
        return jsonify({"success": True, "authenticated_account": False})

    @app.post("/api/profile/<int:profile_id>/claim")
    def claim_slot_api(profile_id):
        from app.ownership import SlotAccessError, claim_empty_slot

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "Invalid or missing JSON data",
            }), 400
        try:
            result = claim_empty_slot(
                profile_id,
                data.get("claim_code"),
                data.get("confirm_claim") is True,
            )
        except ValueError as error:
            return jsonify({"success": False, "error": str(error)}), 400
        except SlotAccessError as error:
            status = 401 if "Login is required" in str(error) else 403
            return jsonify({"success": False, "error": str(error)}), status
        return jsonify({"success": True, **result})
