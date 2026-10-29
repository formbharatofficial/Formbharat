"""₹20 FormBharat fill-service fee.

The charge is due after the profile check and before fill assistance.
Government exam fees stay on the official site. This module does not mark
a payment paid unless Razorpay confirms it. A missing UPI VPA or Razorpay
key leaves the order unpaid.
"""

import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone
from urllib import error, parse, request

from app.ownership import current_user_id
from app.profile import _validate_profile_id
from app.runtime_config import database_path
from app.vacancy import get_vacancy

FEE_RUPEES = 20
FEE_PAISE = 2000
CURRENCY = "INR"
PURPOSE = "form_fill_service"


class FillFeeError(ValueError):
    """The fill-service fee cannot be created or confirmed."""


def _db_path():
    return database_path()


def init_fill_fee_db():
    connection = sqlite3.connect(_db_path())
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fill_fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                profile_id INTEGER NOT NULL,
                vacancy_id INTEGER NOT NULL,
                amount_paise INTEGER NOT NULL,
                currency TEXT NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                provider_order_id TEXT NOT NULL DEFAULT '',
                provider_payment_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                paid_at TEXT
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def fee_settings():
    vpa = os.environ.get("FORMBHARAT_UPI_VPA", "").strip()
    key_id = os.environ.get("FORMBHARAT_RAZORPAY_KEY_ID", "").strip()
    secret = os.environ.get("FORMBHARAT_RAZORPAY_KEY_SECRET", "").strip()
    return {
        "rupees": FEE_RUPEES,
        "amount_paise": FEE_PAISE,
        "currency": CURRENCY,
        "purpose": PURPOSE,
        "upi_vpa": vpa,
        "razorpay_enabled": bool(key_id and secret),
        "razorpay_key_id": key_id if key_id and secret else "",
        "collectable": bool(vpa or (key_id and secret)),
    }


def _row(item):
    return {
        "id": item[0],
        "user_id": item[1],
        "profile_id": item[2],
        "vacancy_id": item[3],
        "amount_paise": item[4],
        "currency": item[5],
        "purpose": item[6],
        "status": item[7],
        "method": item[8],
        "provider": item[9],
        "provider_order_id": item[10],
        "provider_payment_id": item[11],
        "created_at": item[12],
        "paid_at": item[13],
        "rupees": FEE_RUPEES,
    }


def get_fee(fee_id):
    init_fill_fee_db()
    connection = sqlite3.connect(_db_path())
    try:
        row = connection.execute(
            "SELECT * FROM fill_fees WHERE id = ?",
            (int(fee_id),),
        ).fetchone()
    finally:
        connection.close()
    return None if row is None else _row(row)


def latest_fee(vacancy_id, profile_id):
    _validate_profile_id(profile_id)
    if get_vacancy(vacancy_id) is None:
        return None
    init_fill_fee_db()
    connection = sqlite3.connect(_db_path())
    try:
        row = connection.execute(
            """
            SELECT * FROM fill_fees
            WHERE vacancy_id = ? AND profile_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(vacancy_id), int(profile_id)),
        ).fetchone()
    finally:
        connection.close()
    return None if row is None else _row(row)


def has_paid_fee(vacancy_id, profile_id):
    fee = latest_fee(vacancy_id, profile_id)
    return fee is not None and fee["status"] == "paid"


def create_fee(vacancy_id, profile_id, method=""):
    if get_vacancy(vacancy_id) is None:
        raise FillFeeError("Vacancy not found")
    _validate_profile_id(profile_id)
    existing = latest_fee(vacancy_id, profile_id)
    if existing is not None and existing["status"] == "paid":
        return existing
    if existing is not None and existing["status"] in {"unpaid", "pending"}:
        if (
            existing["status"] == "unpaid"
            and not existing.get("provider_order_id")
            and int(existing["amount_paise"]) != FEE_PAISE
        ):
            connection = sqlite3.connect(_db_path())
            try:
                connection.execute(
                    """
                    UPDATE fill_fees
                    SET amount_paise = ?
                    WHERE id = ? AND status = 'unpaid' AND provider_order_id = ''
                    """,
                    (FEE_PAISE, existing["id"]),
                )
                connection.commit()
            finally:
                connection.close()
            existing = get_fee(existing["id"])
        return existing
    settings = fee_settings()
    chosen = str(method or "").strip().lower()
    if chosen not in {"", "upi", "card", "netbanking"}:
        raise FillFeeError("Unknown payment method.")
    now = datetime.now(timezone.utc).isoformat()
    init_fill_fee_db()
    connection = sqlite3.connect(_db_path())
    try:
        cursor = connection.execute(
            """
            INSERT INTO fill_fees (
                user_id, profile_id, vacancy_id, amount_paise, currency,
                purpose, status, method, provider, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'unpaid', ?, '', ?)
            """,
            (
                current_user_id(),
                int(profile_id),
                int(vacancy_id),
                FEE_PAISE,
                CURRENCY,
                PURPOSE,
                chosen,
                now,
            ),
        )
        fee_id = cursor.lastrowid
        connection.commit()
    finally:
        connection.close()
    fee = get_fee(fee_id)
    if settings["razorpay_enabled"]:
        return _attach_razorpay_order(fee)
    return fee


def upi_request(note, paise=None):
    vpa = fee_settings()["upi_vpa"]
    if not vpa:
        return ""
    amount_paise = FEE_PAISE if paise is None else int(paise)
    amount = f"{amount_paise / 100:.2f}"
    return (
        "upi://pay?pa="
        + parse.quote(vpa, safe="")
        + "&pn=FormBharat&am="
        + parse.quote(amount, safe="")
        + "&cu=INR&tn="
        + parse.quote(str(note or "FormBharat fill fee"), safe="")
    )


def upi_link(fee):
    if not fee:
        return ""
    return upi_request(
        f"FormBharat fill fee {fee['id']}",
        fee.get("amount_paise") or FEE_PAISE,
    )


def _attach_razorpay_order(fee):
    settings = fee_settings()
    payload = json.dumps({
        "amount": FEE_PAISE,
        "currency": CURRENCY,
        "receipt": f"fb-fill-{fee['id']}",
        "payment_capture": 1,
        "notes": {"purpose": PURPOSE, "fee_id": str(fee["id"])},
    }).encode("utf-8")
    auth = (settings["razorpay_key_id"] + ":" + os.environ.get(
        "FORMBHARAT_RAZORPAY_KEY_SECRET", ""
    ).strip()).encode("utf-8")
    req = request.Request(
        "https://api.razorpay.com/v1/orders",
        data=payload,
        method="POST",
        headers={
            "Authorization": "Basic " + __import__("base64").b64encode(auth).decode("ascii"),
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise FillFeeError("Razorpay order could not be created.") from exc
    order_id = str(body.get("id") or "")
    if not order_id:
        raise FillFeeError("Razorpay order could not be created.")
    connection = sqlite3.connect(_db_path())
    try:
        connection.execute(
            """
            UPDATE fill_fees
            SET provider = 'razorpay', provider_order_id = ?, status = 'pending'
            WHERE id = ? AND status IN ('unpaid', 'pending')
            """,
            (order_id, fee["id"]),
        )
        connection.commit()
    finally:
        connection.close()
    return get_fee(fee["id"])


def confirm_razorpay_payment(order_id, payment_id, signature):
    secret = os.environ.get("FORMBHARAT_RAZORPAY_KEY_SECRET", "").strip()
    if not secret:
        raise FillFeeError("Razorpay is not configured.")
    supplied = "" if signature is None else str(signature)
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if len(supplied) != len(expected) or not hmac.compare_digest(supplied, expected):
        raise FillFeeError("Payment signature was rejected.")
    init_fill_fee_db()
    now = datetime.now(timezone.utc).isoformat()
    connection = sqlite3.connect(_db_path())
    try:
        changed = connection.execute(
            """
            UPDATE fill_fees
            SET status = 'paid',
                provider_payment_id = ?,
                paid_at = ?,
                method = CASE WHEN method = '' THEN 'razorpay' ELSE method END
            WHERE provider_order_id = ? AND status IN ('unpaid', 'pending')
            """,
            (str(payment_id), now, str(order_id)),
        ).rowcount
        connection.commit()
    finally:
        connection.close()
    if changed != 1:
        raise FillFeeError("That payment could not be matched.")
    connection = sqlite3.connect(_db_path())
    try:
        row = connection.execute(
            "SELECT * FROM fill_fees WHERE provider_order_id = ?",
            (str(order_id),),
        ).fetchone()
    finally:
        connection.close()
    return _row(row)
