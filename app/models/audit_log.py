"""
Model: AuditLog
Immutable append-only log of every significant action in the system.
Provides fintech-grade traceability for imports, confirmations, deletions, logins.
"""
import json
from datetime import datetime
from ..extensions import db


# Supported action types — extend as needed
AUDIT_ACTIONS = [
    "login",
    "logout",
    "import_upload",
    "import_confirm",
    "import_reject",
    "expense_create",
    "expense_edit",
    "expense_delete",
    "sms_sync",
    "device_register",
    "device_revoke",
    "goal_create",
    "goal_update",
    "budget_create",
    "budget_update",
]


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=True)   # e.g. "expense", "import"
    entity_id = db.Column(db.Integer, nullable=True)        # PK of the affected row

    # Arbitrary JSON extra data — stored as TEXT for portability
    extra_json = db.Column("metadata_json", db.Text, nullable=True)

    ip_address = db.Column(db.String(45), nullable=True)    # IPv4 or IPv6
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # ── Helpers ────────────────────────────────────────────────────────────

    @property
    def extra(self) -> dict:
        if self.extra_json:
            try:
                return json.loads(self.extra_json)
            except (ValueError, TypeError):
                return {}
        return {}

    @extra.setter
    def extra(self, value: dict):
        self.extra_json = json.dumps(value) if value else None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "metadata": self.extra,
            "ip_address": self.ip_address,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
