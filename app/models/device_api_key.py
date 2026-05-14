"""
Model: DeviceApiKey
A permanent, non-expiring API key tied to a user's device.
Used by MacroDroid / Tasker / SMS forwarder apps to push SMS
without needing to refresh JWT tokens.

Security:
  - 64-char cryptographically random hex token
  - Stored as SHA-256 hash in DB (key shown to user only once)
  - Scoped to a single user — cannot access other users' data
  - Can be revoked instantly from the Device Sync page
"""
import secrets
import hashlib
from datetime import datetime
from ..extensions import db


class DeviceApiKey(db.Model):
    __tablename__ = "device_api_keys"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable label, e.g. "My Pixel 8", "MacroDroid"
    label = db.Column(db.String(120), nullable=False, default="My Device")

    # SHA-256 hash of the actual token (never store plaintext)
    key_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Prefix (first 8 chars) — shown in UI to identify the key
    key_prefix = db.Column(db.String(8), nullable=False)

    # Tracking
    last_used_at = db.Column(db.DateTime, nullable=True)
    total_requests = db.Column(db.Integer, default=0)
    status = db.Column(db.String(16), default="active", index=True)  # active | revoked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate() -> tuple[str, str]:
        """
        Generate a new token.
        Returns (plaintext_token, hashed_token).
        The plaintext is shown to the user ONCE and never stored.
        """
        token = secrets.token_hex(32)          # 64-char hex = 256-bit entropy
        hashed = hashlib.sha256(token.encode()).hexdigest()
        return token, hashed

    @staticmethod
    def verify(token: str) -> "DeviceApiKey | None":
        """Look up a key by the raw token. Returns the key object or None."""
        hashed = hashlib.sha256(token.encode()).hexdigest()
        key = DeviceApiKey.query.filter_by(key_hash=hashed, status="active").first()
        if key:
            key.last_used_at = datetime.utcnow()
            key.total_requests += 1
            db.session.commit()
        return key

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "key_prefix": self.key_prefix + "...",   # never expose full hash
            "status": self.status,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "total_requests": self.total_requests,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
