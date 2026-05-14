"""
Model: ImportedTransaction
Represents a transaction parsed from a bank statement, SMS, or OCR receipt
that is sitting in the pending review queue before being confirmed into expenses.
"""
from datetime import datetime
from ..extensions import db


# Allowed source types for imported transactions
SOURCE_TYPES = ["manual", "sms", "statement", "ocr"]

# Allowed statuses in the pending workflow
IMPORT_STATUSES = ["pending", "confirmed", "rejected", "duplicate"]


class ImportedTransaction(db.Model):
    __tablename__ = "imported_transactions"

    id = db.Column(db.Integer, primary_key=True)

    # Owner
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source metadata
    source_type = db.Column(
        db.Enum(*SOURCE_TYPES), nullable=False, default="statement"
    )
    import_batch_id = db.Column(
        db.Integer,
        db.ForeignKey("import_history.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Raw content (preserved for audit / re-parsing)
    raw_text = db.Column(db.Text, nullable=True)

    # Parsed / normalised fields
    merchant = db.Column(db.String(255), nullable=True)
    normalized_merchant = db.Column(db.String(255), nullable=True, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_direction = db.Column(
        db.Enum("debit", "credit"), nullable=False, default="debit"
    )
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    category = db.Column(db.String(50), default="Other")
    payment_method = db.Column(db.String(50), default="Other")
    description = db.Column(db.String(255), nullable=True)

    # Quality signals
    confidence_score = db.Column(db.Float, default=0.0)   # 0.0 – 1.0

    # Deduplication — SHA-256 of (user_id + norm_merchant + amount + date)
    transaction_hash = db.Column(db.String(64), nullable=True, index=True)

    # Workflow status
    status = db.Column(
        db.Enum(*IMPORT_STATUSES), nullable=False, default="pending", index=True
    )

    # If confirmed, points to the resulting expense row
    confirmed_expense_id = db.Column(
        db.Integer,
        db.ForeignKey("expenses.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_type": self.source_type,
            "import_batch_id": self.import_batch_id,
            "raw_text": self.raw_text,
            "merchant": self.merchant,
            "normalized_merchant": self.normalized_merchant,
            "amount": float(self.amount),
            "transaction_direction": self.transaction_direction,
            "transaction_date": (
                self.transaction_date.isoformat() if self.transaction_date else None
            ),
            "category": self.category,
            "payment_method": self.payment_method,
            "description": self.description,
            "confidence_score": self.confidence_score,
            "transaction_hash": self.transaction_hash,
            "status": self.status,
            "confirmed_expense_id": self.confirmed_expense_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
