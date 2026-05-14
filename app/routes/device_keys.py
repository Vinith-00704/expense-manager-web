"""
app/routes/device_keys.py
Blueprint for /api/device-keys/* — permanent device API key management.

These keys allow MacroDroid / Tasker / SMS forwarder apps to POST
SMS messages without needing a JWT token (which expires).
"""
from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.device_api_key import DeviceApiKey
from ..utils.response import success, error
from ..utils.audit import log_action

device_keys_bp = Blueprint("device_keys", __name__)


@device_keys_bp.post("/generate")
@jwt_required()
def generate():
    """
    POST /api/device-keys/generate
    Body: { "label": "My Pixel 8" }
    Creates a new permanent API key for the current user.
    Returns the plaintext key ONCE — it cannot be recovered later.
    """
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}
    label   = body.get("label", "My Device").strip()[:120]

    # Limit: max 10 active keys per user
    active_count = DeviceApiKey.query.filter_by(
        user_id=user_id, status="active"
    ).count()
    if active_count >= 10:
        return error("Maximum 10 active device keys allowed. Revoke old ones first.", 400)

    plaintext, hashed = DeviceApiKey.generate()

    key = DeviceApiKey(
        user_id    = user_id,
        label      = label,
        key_hash   = hashed,
        key_prefix = plaintext[:8],
    )
    db.session.add(key)
    db.session.commit()

    log_action(user_id, "device_key_generate", "device_api_key", key.id, {"label": label})

    # Return plaintext token ONCE — never retrievable again
    return success({
        **key.to_dict(),
        "token": plaintext,   # ← shown once, then gone
        "warning": "Copy this token now. It will NOT be shown again.",
    }, "Device key generated.", 201)


@device_keys_bp.get("/")
@jwt_required()
def list_keys():
    """GET /api/device-keys/ — list all device keys for the current user."""
    user_id = int(get_jwt_identity())
    keys = DeviceApiKey.query.filter_by(user_id=user_id).order_by(
        DeviceApiKey.created_at.desc()
    ).all()
    return success([k.to_dict() for k in keys])


@device_keys_bp.delete("/<int:key_id>")
@jwt_required()
def revoke(key_id: int):
    """DELETE /api/device-keys/<id> — permanently revoke a key."""
    user_id = int(get_jwt_identity())
    key = DeviceApiKey.query.filter_by(id=key_id, user_id=user_id).first()
    if not key:
        return error("Key not found.", 404)

    key.status = "revoked"
    db.session.commit()
    log_action(user_id, "device_key_revoke", "device_api_key", key_id)
    return success({"id": key_id}, "Key revoked. Any automation using it will stop working.")


@device_keys_bp.get("/status")
@jwt_required()
def status():
    """
    GET /api/device-keys/status
    Returns count of pending SMS transactions as a notification indicator.
    Used by the frontend notification bell (polls every 30 seconds).
    """
    user_id = int(get_jwt_identity())

    from ..models.imported_transaction import ImportedTransaction
    from datetime import timedelta

    # Count pending SMS transactions
    pending_sms = ImportedTransaction.query.filter_by(
        user_id=user_id, source_type="sms", status="pending"
    ).count()

    # Count new SMS in last 5 minutes (for real-time alert)
    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
    recent_sms = ImportedTransaction.query.filter(
        ImportedTransaction.user_id == user_id,
        ImportedTransaction.source_type == "sms",
        ImportedTransaction.created_at >= recent_cutoff,
    ).count()

    # All pending (any source)
    total_pending = ImportedTransaction.query.filter_by(
        user_id=user_id, status="pending"
    ).count()

    return success({
        "pending_sms":   pending_sms,
        "recent_sms":    recent_sms,    # new in last 5 min → triggers bell
        "total_pending": total_pending,
        "has_new":       recent_sms > 0,
    })
