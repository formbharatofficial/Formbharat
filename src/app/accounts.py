"""Local accounts. Registration does not claim any profile slot."""

import re
import sqlite3
from datetime import datetime, timezone

from flask import jsonify, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.profile import MAX_PROFILES, init_db


def _db_path():
    from app import profile
    return profile.DB_PATH
from app.request_guard import issue_csrf_token


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 12

ACCOUNT_PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FormBharat Account</title>
</head>
<body>
<div class="container">
<div class="card">
<h1>Account</h1>
<p>खाता। यह सरकारी फॉर्म का OTP या अंतिम Submit नहीं है।</p>
{% if notice %}<p class="success">{{ notice }}</p>{% endif %}
{% if error %}<p>{{ error }}</p>{% endif %}
{% if email %}
<p>Signed in as {{ email }}</p>
<form method="POST" action="{{ logout_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button type="submit">Log out / लॉग आउट</button>
</form>
<h2>Claim an empty slot</h2>
<p>खाली slot ही claim हो सकता है। पुराने profile, documents या applications अपने-आप किसी account को नहीं मिलते।</p>
<ul>
{% for slot in slots %}
<li>Slot {{ slot.id }}: {{ slot.status }}</li>
{% endfor %}
</ul>
<form method="POST" action="{{ claim_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label>Empty slot number</label>
<input name="profile_id" type="number" min="1" max="5" required>
<label>Claim code</label>
<input name="claim_code" type="password" autocomplete="off">
<label><input name="confirm_claim" type="checkbox" value="yes"> I confirm this claim</label>
<button type="submit">Claim empty slot</button>
</form>
{% else %}
<h2>Create account</h2>
<form method="POST" action="{{ register_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label>Email</label>
<input name="email" type="email" autocomplete="username" required>
<label>Password</label>
<input name="password" type="password" autocomplete="new-password" required>
<button type="submit">Create account / खाता बनाएँ</button>
</form>
<h2>Log in</h2>
<form method="POST" action="{{ login_url }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label>Email</label>
<input name="email" type="email" autocomplete="username" required>
<label>Password</label>
<input name="password" type="password" autocomplete="current-password" required>
<button type="submit">Log in / लॉग इन</button>
</form>
{% endif %}
</div>
</div>
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
                created_at TEXT NOT NULL
            )
            """
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
        raise ValueError("Password must be at least 12 characters.")
    return value


def register_user(email, password):
    clean_email = _clean_email(email)
    clean_password = _clean_password(password)
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
            INSERT INTO users (email, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (
                clean_email,
                generate_password_hash(clean_password),
                datetime.now(timezone.utc).isoformat(),
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


def _account_context(notice="", error=""):
    from app.ownership import claim_status, current_user_id

    user_id = current_user_id()
    email = user_email(user_id) if user_id is not None else None
    slots = [
        {"id": profile_id, "status": claim_status(profile_id)}
        for profile_id in range(1, MAX_PROFILES + 1)
    ] if email else []
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
    }


def register_account_routes(app):
    init_accounts()

    @app.route("/account", methods=["GET"])
    def account_page():
        return render_template_string(ACCOUNT_PAGE, **_account_context())

    @app.route("/account/register", methods=["POST"])
    def account_register():
        try:
            user_id = register_user(
                request.form.get("email"),
                request.form.get("password"),
            )
        except ValueError as error:
            return render_template_string(
                ACCOUNT_PAGE, **_account_context(error=str(error))
            ), 400
        start_session(user_id)
        return redirect(url_for("account_page"))

    @app.route("/account/login", methods=["POST"])
    def account_login():
        user_id = authenticate(
            request.form.get("email"),
            request.form.get("password"),
        )
        if user_id is None:
            return render_template_string(
                ACCOUNT_PAGE,
                **_account_context(error="Email or password is incorrect."),
            ), 401
        start_session(user_id)
        return redirect(url_for("account_page"))

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
