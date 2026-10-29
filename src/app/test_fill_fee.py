from flask import Flask

from app import fill_fee, vacancy
from app.fill_fee import FEE_PAISE, FillFeeError, create_fee, has_paid_fee, latest_fee


def _app(monkeypatch, tmp_path):
    database = tmp_path / "formbharat.db"
    monkeypatch.setattr(vacancy, "DB_PATH", database)
    monkeypatch.setattr(fill_fee, "_db_path", lambda: database)
    vacancy.init_vacancy_db()
    fill_fee.init_fill_fee_db()
    vacancy.create_vacancy(
        title="Local Notice",
        organization="SSC",
        official_link="https://ssc.gov.in/",
    )
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


def test_create_fee_stays_unpaid_without_a_gateway(monkeypatch, tmp_path):
    monkeypatch.delenv("FORMBHARAT_UPI_VPA", raising=False)
    monkeypatch.delenv("FORMBHARAT_RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("FORMBHARAT_RAZORPAY_KEY_SECRET", raising=False)
    app = _app(monkeypatch, tmp_path)
    with app.test_request_context("/"):
        fee = create_fee(1, 1, "upi")
    assert fee["amount_paise"] == FEE_PAISE
    assert fee["status"] == "unpaid"
    assert has_paid_fee(1, 1) is False
    assert latest_fee(1, 1)["id"] == fee["id"]


def test_upi_link_asks_for_the_current_fee_and_stays_unpaid(monkeypatch, tmp_path):
    monkeypatch.setenv("FORMBHARAT_UPI_VPA", "user@ybl")
    monkeypatch.delenv("FORMBHARAT_RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("FORMBHARAT_RAZORPAY_KEY_SECRET", raising=False)
    app = _app(monkeypatch, tmp_path)
    with app.test_request_context("/"):
        fee = create_fee(1, 1, "upi")
    link = fill_fee.upi_link(fee)
    assert fee["amount_paise"] == FEE_PAISE
    assert "am=20.00" in link
    assert "pa=user%40ybl" in link
    assert fee["status"] == "unpaid"
    assert has_paid_fee(1, 1) is False

    connection = __import__("sqlite3").connect(tmp_path / "formbharat.db")
    connection.execute(
        "UPDATE fill_fees SET amount_paise = 1500 WHERE id = ?",
        (fee["id"],),
    )
    connection.commit()
    connection.close()
    with app.test_request_context("/"):
        again = create_fee(1, 1, "upi")
    assert again["id"] == fee["id"]
    assert again["amount_paise"] == FEE_PAISE
    assert again["status"] == "unpaid"


def test_razorpay_confirm_rejects_a_bad_signature(monkeypatch, tmp_path):
    _app(monkeypatch, tmp_path)
    monkeypatch.setenv("FORMBHARAT_RAZORPAY_KEY_SECRET", "super-secret")
    try:
        fill_fee.confirm_razorpay_payment("order_1", "pay_1", "bad")
    except FillFeeError as error:
        assert str(error) == "Payment signature was rejected."
    else:
        raise AssertionError("bad signature was accepted")
