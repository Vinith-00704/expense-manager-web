"""
app/routes/devices.py
Blueprint for /api/devices/* — Android device registration and management.
"""
from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..extensions import db
from ..models.registered_device import RegisteredDevice
from ..utils.response import success, error
from ..utils.audit import log_action

devices_bp = Blueprint("devices", __name__)


@devices_bp.post("/register")
@jwt_required()
def register():
    """
    POST /api/devices/register
    Body: { "device_id": "...", "device_name": "Pixel 7", "device_type": "android" }
    """
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}

    device_id   = body.get("device_id", "").strip()
    device_name = body.get("device_name", "Unknown Device")
    device_type = body.get("device_type", "android")

    if not device_id:
        return error("device_id is required.", 400)

    # Check for existing registration
    existing = RegisteredDevice.query.filter_by(device_id=device_id).first()
    if existing:
        if existing.user_id != user_id:
            return error("Device already registered to another account.", 403)
        # Re-activate if previously revoked
        existing.status = "active"
        existing.device_name = device_name
        db.session.commit()
        log_action(user_id, "device_register", "registered_device", existing.id)
        return success(existing.to_dict(), "Device re-activated.")

    device = RegisteredDevice(
        user_id=user_id,
        device_id=device_id,
        device_name=device_name,
        device_type=device_type if device_type in ("android", "ios", "other") else "android",
    )
    db.session.add(device)
    db.session.commit()

    log_action(user_id, "device_register", "registered_device", device.id, {
        "device_name": device_name, "device_type": device_type,
    })
    return success(device.to_dict(), "Device registered successfully.", 201)


@devices_bp.get("/")
@jwt_required()
def list_devices():
    """GET /api/devices/ — list all devices for the current user."""
    user_id = int(get_jwt_identity())
    devices = RegisteredDevice.query.filter_by(user_id=user_id).order_by(
        RegisteredDevice.created_at.desc()
    ).all()
    return success([d.to_dict() for d in devices])


@devices_bp.delete("/<string:device_id>")
@jwt_required()
def revoke(device_id: str):
    """DELETE /api/devices/<device_id> — revoke a device."""
    user_id = int(get_jwt_identity())
    device  = RegisteredDevice.query.filter_by(
        device_id=device_id, user_id=user_id
    ).first()
    if not device:
        return error("Device not found.", 404)

    device.status = "revoked"
    db.session.commit()
    log_action(user_id, "device_revoke", "registered_device", device.id)
    return success({"device_id": device_id}, "Device revoked.")


@devices_bp.post("/<string:device_id>/ping")
@jwt_required()
def sync_ping(device_id: str):
    """POST /api/devices/<device_id>/ping — update last_sync_at timestamp."""
    user_id = int(get_jwt_identity())
    device  = RegisteredDevice.query.filter_by(
        device_id=device_id, user_id=user_id, status="active"
    ).first()
    if not device:
        return error("Active device not found.", 404)

    device.last_sync_at = datetime.utcnow()
    db.session.commit()
    return success({"last_sync_at": device.last_sync_at.isoformat()})
