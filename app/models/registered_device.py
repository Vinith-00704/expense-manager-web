"""
Model: RegisteredDevice
Tracks Android (or other) devices that are authorised to push SMS
transactions to FinanceOS via the /api/sms/sync endpoint.
"""
from datetime import datetime
from ..extensions import db


DEVICE_STATUSES = ["active", "revoked"]
DEVICE_TYPES = ["android", "ios", "other"]


class RegisteredDevice(db.Model):
    __tablename__ = "registered_devices"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Unique identifier sent by the Android app (e.g. Firebase instance ID)
    device_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    device_name = db.Column(db.String(120), nullable=True)   # e.g. "Pixel 7"
    device_type = db.Column(
        db.Enum(*DEVICE_TYPES), nullable=False, default="android"
    )

    # Sync tracking
    last_sync_at = db.Column(db.DateTime, nullable=True)
    total_synced = db.Column(db.Integer, default=0)

    # Reference to the JWT jti used at registration (for revocation checks)
    auth_token_ref = db.Column(db.String(255), nullable=True)

    status = db.Column(
        db.Enum(*DEVICE_STATUSES), nullable=False, default="active", index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "last_sync_at": (
                self.last_sync_at.isoformat() if self.last_sync_at else None
            ),
            "total_synced": self.total_synced,
            "status": self.status,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
