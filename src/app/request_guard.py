"""Same-origin checks, form CSRF tokens, and a small in-memory rate limit.

JSON API calls stay usable without a form token. Form and multipart
requests must echo the session token. This is not an account system,
and it does not encrypt stored documents.
"""

import json
import os
import secrets
import time

from flask import jsonify, request, session


_UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def issue_csrf_token():
    token = session.get("csrf_token")
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _tunnel_scheme():
    """Read https only from the local tunnel, not from a network caller."""
    if request.remote_addr not in {"127.0.0.1", "::1"}:
        return ""
    forwarded = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    if forwarded in {"http", "https"}:
        return forwarded
    visitor = request.headers.get("CF-Visitor", "").strip()
    if not visitor:
        return ""
    try:
        scheme = str(json.loads(visitor).get("scheme", "")).lower()
    except (TypeError, ValueError, json.JSONDecodeError):
        return ""
    if scheme in {"http", "https"}:
        return scheme
    return ""


def _tunnel_host_url():
    """The phone page is https. The tunnel delivers it as http on this machine."""
    scheme = _tunnel_scheme()
    if not scheme:
        return ""
    return f"{scheme}://{request.host}/"


def _same_origin():
    origin = request.headers.get("Origin", "").strip().rstrip("/")
    if not origin:
        return True
    allowed = {request.host_url.rstrip("/")}
    tunnel = _tunnel_host_url().rstrip("/")
    if tunnel:
        allowed.add(tunnel)
    return origin in allowed


def _content_type():
    return (request.content_type or "").split(";", 1)[0].strip().lower()


def _json_request():
    return _content_type() == "application/json"


def _form_request():
    """Browser form and file uploads are the requests a page can forge."""
    return _content_type() in {
        "application/x-www-form-urlencoded",
        "multipart/form-data",
    }


def _token_matches():
    expected = session.get("csrf_token")
    supplied = (
        request.headers.get("X-FormBharat-Token", "")
        or request.form.get("csrf_token", "")
    )
    if not isinstance(expected, str) or not isinstance(supplied, str):
        return False
    if len(expected) != len(supplied) or len(expected) < 32:
        return False
    return secrets.compare_digest(expected, supplied)


def _rate_limited(app):
    limit = int(app.config.get("FORMBHARAT_RATE_LIMIT", 120))
    window = float(app.config.get("FORMBHARAT_RATE_WINDOW", 60))
    buckets = app.extensions.setdefault("formbharat_rate_buckets", {})
    key = f"{request.remote_addr}:{request.method}:{request.path}"
    now = time.monotonic()
    recent = [stamp for stamp in buckets.get(key, []) if now - stamp < window]
    if len(recent) >= limit:
        buckets[key] = recent
        return True
    recent.append(now)
    buckets[key] = recent
    return False


def install_request_guard(app):
    """Install the guard once on an application."""
    if app.extensions.get("formbharat_guard"):
        return
    app.extensions["formbharat_guard"] = True

    if not app.secret_key:
        configured = os.environ.get("FORMBHARAT_SECRET_KEY", "").strip()
        app.secret_key = configured or secrets.token_hex(32)
    # Flask already stores these keys, so setdefault would leave SameSite unset.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

    @app.before_request
    def _guard_request():
        if request.method not in _UNSAFE:
            return None
        if not _same_origin():
            return jsonify({
                "success": False,
                "error": "cross-origin request was rejected",
            }), 403
        if _rate_limited(app):
            return jsonify({
                "success": False,
                "error": "too many requests",
            }), 429
        if _form_request() and not _token_matches():
            return jsonify({
                "success": False,
                "error": "csrf token is required",
            }), 403
        return None

    @app.get("/api/csrf")
    def csrf_token():
        return jsonify({"success": True, "token": issue_csrf_token()})


def attach_csrf(client):
    """Add the real session token to unsafe test-client calls.

    The guard still rejects a call that omits the token. This only
    fetches the token the same way the browser page does.
    """
    cached = {"token": ""}

    def token():
        if not cached["token"]:
            body = client.get("/api/csrf").get_json() or {}
            cached["token"] = body.get("token") or ""
        return cached["token"]

    def wrap(method_name):
        original = getattr(client, method_name)

        def wrapped(*args, **kwargs):
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("X-FormBharat-Token", token())
            kwargs["headers"] = headers
            return original(*args, **kwargs)

        return wrapped

    for name in ("post", "put", "patch", "delete"):
        setattr(client, name, wrap(name))
    return client
