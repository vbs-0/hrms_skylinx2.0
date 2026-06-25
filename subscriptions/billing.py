"""
Razorpay billing — no SDK, just the REST API + HMAC signature check (stdlib).

Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in the environment to enable live
checkout. When unset, `configured()` is False and the plan page falls back to
"contact owner to activate" (the owner can still set plans manually from the
console). India / INR, since pricing is in ₹.
"""

import hashlib
import hmac
import os

KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
# separate secret set in the Razorpay dashboard when configuring the webhook
WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")


def configured() -> bool:
    return bool(KEY_ID and KEY_SECRET)


def create_order(amount_rupees, receipt: str) -> dict:
    """Create a Razorpay order; returns the order dict (contains 'id')."""
    import requests

    resp = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(KEY_ID, KEY_SECRET),
        json={
            "amount": int(round(float(amount_rupees) * 100)),  # paise
            "currency": "INR",
            "receipt": receipt[:40],
            "payment_capture": 1,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify a Razorpay checkout callback signature."""
    if not (KEY_SECRET and order_id and payment_id and signature):
        return False
    expected = hmac.new(
        KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook(raw_body: bytes, signature: str) -> bool:
    """Verify a Razorpay webhook POST (server-to-server, gap #5).

    Signature = HMAC-SHA256 of the raw request body with the webhook secret.
    """
    if not (WEBHOOK_SECRET and raw_body and signature):
        return False
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
