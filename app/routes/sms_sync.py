"""
app/routes/sms_sync.py
Blueprint for /api/sms/* — Android SMS sync endpoints.

Authentication: accepts either:
  1. JWT Bearer token  (standard login sessions)
  2. X-Device-Key header  (permanent device API keys — never expire)

The X-Device-Key method is designed for MacroDroid / Tasker / SMS forwarder
apps that need to run 24/7 without token refresh.
"""
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models.imported_transaction import ImportedTransaction
from ..models.registered_device import RegisteredDevice
from ..models.device_api_key import DeviceApiKey
from ..services.sms_parsers import parse_sms
from ..services.merchant_normalizer_service import normalize as norm_merchant
from ..services.categorization_service import categorize
from ..services.deduplication_service import compute_hash, check_duplicate
from ..utils.response import success, error
from ..utils.audit import log_action

sms_sync_bp = Blueprint("sms_sync", __name__)


def _get_user_id() -> tuple[int | None, str | None]:
    """
    Resolve user identity from either JWT or X-Device-Key header.
    Returns (user_id, error_message).
    """
    # Try Device API Key first (header: X-Device-Key)
    device_key = request.headers.get("X-Device-Key", "").strip()
    if device_key:
        key_obj = DeviceApiKey.verify(device_key)
        if not key_obj:
            return None, "Invalid or revoked device key."
        return key_obj.user_id, None

    # Fall back to JWT
    try:
        verify_jwt_in_request()
        return int(get_jwt_identity()), None
    except Exception:
        return None, "Authentication required. Provide JWT token or X-Device-Key header."


@sms_sync_bp.post("/raw")
def raw_sms():
    """
    POST /api/sms/raw
    Submit a single raw SMS string for server-side parsing.

    Auth: JWT Bearer OR X-Device-Key header
    Body: { "sms_text": "...", "device_id": "..." (optional) }
    """
    user_id, err = _get_user_id()
    if err:
        return error(err, 401)

    body     = request.get_json(silent=True) or {}
    sms_text = body.get("sms_text", "").strip()

    if not sms_text:
        return error("sms_text is required.", 400)

    parsed = parse_sms(sms_text)
    if not parsed:
        return error("Could not parse SMS — unsupported format.", 422)

    norm    = norm_merchant(parsed.get("merchant", ""))
    cat, conf = categorize(norm, parsed.get("amount", 0), parsed.get("direction", "debit"))
    tx_date = parsed.get("date") or datetime.today().date()
    amount  = parsed.get("amount", 0)

    tx_hash = compute_hash(user_id, norm, amount, tx_date)
    dup     = check_duplicate(user_id, tx_hash, amount, tx_date)
    status  = "duplicate" if dup["is_duplicate"] else "pending"

    tx = ImportedTransaction(
        user_id               = user_id,
        source_type           = "sms",
        raw_text              = sms_text,
        merchant              = parsed.get("merchant"),
        normalized_merchant   = norm,
        amount                = Decimal(str(amount)),
        transaction_direction = parsed.get("direction", "debit"),
        transaction_date      = tx_date,
        category              = cat,
        payment_method        = parsed.get("payment_method", "UPI"),
        confidence_score      = conf,
        transaction_hash      = tx_hash,
        status                = status,
    )
    db.session.add(tx)
    db.session.commit()

    log_action(user_id, "sms_sync", "imported_transaction", tx.id, {
        "parser": parsed.get("parser"),
        "auth": "device_key" if request.headers.get("X-Device-Key") else "jwt",
    })
    return success(tx.to_dict(), "SMS parsed and queued for review.")


@sms_sync_bp.post("/sync")
def sync_batch():
    """
    POST /api/sms/sync
    Submit a batch of pre-parsed SMS transactions from Android app.

    Auth: JWT Bearer OR X-Device-Key header
    Body: {
        "device_id": "...",
        "transactions": [
            { "merchant": "Swiggy", "amount": 250, "direction": "debit",
              "date": "2026-05-08", "payment_method": "UPI", "raw_text": "..." }
        ]
    }
    Idempotent — duplicates are detected via transaction_hash.
    """
    user_id, err = _get_user_id()
    if err:
        return error(err, 401)

    body      = request.get_json(silent=True) or {}
    device_id = body.get("device_id")
    items     = body.get("transactions", [])

    if not items:
        return error("No transactions provided.", 400)

    device = None
    if device_id:
        device = RegisteredDevice.query.filter_by(
            device_id=device_id, user_id=user_id, status="active"
        ).first()

    queued = 0
    dupes  = 0
    failed = []

    for item in items:
        try:
            raw_merchant = item.get("merchant", "")
            norm    = norm_merchant(raw_merchant)
            amount  = float(item.get("amount", 0))
            direction = item.get("direction", "debit")
            raw_date  = item.get("date")

            if isinstance(raw_date, str):
                tx_date = datetime.fromisoformat(raw_date).date()
            else:
                tx_date = datetime.today().date()

            cat, conf = categorize(norm, amount, direction)
            tx_hash   = compute_hash(user_id, norm, amount, tx_date)
            dup       = check_duplicate(user_id, tx_hash, amount, tx_date)
            status    = "duplicate" if dup["is_duplicate"] else "pending"

            if dup["is_duplicate"]:
                dupes += 1

            tx = ImportedTransaction(
                user_id               = user_id,
                source_type           = "sms",
                raw_text              = item.get("raw_text", ""),
                merchant              = raw_merchant,
                normalized_merchant   = norm,
                amount                = Decimal(str(amount)),
                transaction_direction = direction,
                transaction_date      = tx_date,
                category              = cat,
                payment_method        = item.get("payment_method", "UPI"),
                confidence_score      = conf,
                transaction_hash      = tx_hash,
                status                = status,
            )
            db.session.add(tx)
            queued += 1

        except Exception as exc:
            failed.append({"item": item.get("merchant", "?"), "error": str(exc)})

    if device:
        device.last_sync_at = datetime.utcnow()
        device.total_synced += queued

    db.session.commit()
    log_action(user_id, "sms_sync_batch", None, None, {
        "device_id": device_id, "queued": queued, "dupes": dupes,
        "auth": "device_key" if request.headers.get("X-Device-Key") else "jwt",
    })

    return success({
        "queued": queued, "duplicates": dupes,
        "failed": len(failed), "errors": failed[:5],
    }, f"{queued} transaction(s) queued for review.")


@sms_sync_bp.get("/status")
def status():
    """
    GET /api/sms/status — sync stats + connected devices.
    Auth: JWT or Device Key.
    """
    user_id, err = _get_user_id()
    if err:
        return error(err, 401)

    devices   = RegisteredDevice.query.filter_by(user_id=user_id, status="active").all()
    total_sms = ImportedTransaction.query.filter_by(
        user_id=user_id, source_type="sms"
    ).count()

    return success({
        "total_sms_imported": total_sms,
        "devices": [d.to_dict() for d in devices],
    })
