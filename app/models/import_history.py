"""
Model: ImportHistory
One row per uploaded statement file. Tracks parsing statistics and the
filename so the user can see what they uploaded and when.
"""
from datetime import datetime
from ..extensions import db


class ImportHistory(db.Model):
    __tablename__ = "import_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File metadata
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(
        db.Enum("csv", "xlsx", "pdf", "sms"), nullable=False, default="csv"
    )
    bank_detected = db.Column(db.String(50), nullable=True)  # e.g. "HDFC", "SBI"

    # Parsing statistics
    imported_count = db.Column(db.Integer, default=0)   # rows extracted
    success_count = db.Column(db.Integer, default=0)    # pending rows created
    failed_count = db.Column(db.Integer, default=0)     # rows that failed to parse
    duplicate_count = db.Column(db.Integer, default=0)  # rows detected as duplicates

    # Optional error summary JSON stored as text
    error_summary = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to pending transactions in this batch
    transactions = db.relationship(
        "ImportedTransaction",
        backref="import_batch",
        lazy="dynamic",
        foreign_keys="ImportedTransaction.import_batch_id",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "bank_detected": self.bank_detected,
            "imported_count": self.imported_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "duplicate_count": self.duplicate_count,
            "error_summary": self.error_summary,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }
