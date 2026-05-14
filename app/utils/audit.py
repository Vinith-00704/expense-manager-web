"""
app/utils/audit.py
Utility helper for writing to the audit_logs table.
Import this and call log_action() from any route or service.
"""
from flask import request
from ..extensions import db
from ..models.audit_log import AuditLog


def log_action(
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Append an immutable audit record.

    Args:
        user_id:     ID of the acting user (None for system actions).
        action:      Action verb from AuditLog.AUDIT_ACTIONS (or any string).
        entity_type: Model name the action was performed on (e.g. "expense").
        entity_id:   Primary key of the affected record.
        metadata:    Arbitrary extra context stored as JSON.
    """
    ip = None
    try:
        ip = request.remote_addr
    except RuntimeError:
        pass  # outside request context (e.g. background tasks)

    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip,
    )
    if metadata:
        entry.extra = metadata

    db.session.add(entry)
    # Commit separately so a rollback in the main transaction
    # does not swallow the audit record.
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()
