"""
Model: FinancialGoal
Represents a savings or purchase target the user is working toward.
Progress is calculated dynamically from linked expense/income entries.
"""
from datetime import datetime, date
from ..extensions import db


GOAL_STATUSES = ["active", "achieved", "cancelled"]
GOAL_CATEGORIES = [
    "Emergency Fund", "Vacation", "Vehicle", "Gadget",
    "Home", "Education", "Investment", "Other"
]


class FinancialGoal(db.Model):
    __tablename__ = "financial_goals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), default="Other")

    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    # current_amount is updated manually or computed via savings tracking
    current_amount = db.Column(db.Numeric(12, 2), default=0)

    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(
        db.Enum(*GOAL_STATUSES), nullable=False, default="active", index=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def progress_pct(self) -> float:
        """Return completion percentage (0–100)."""
        if not self.target_amount or float(self.target_amount) == 0:
            return 0.0
        pct = float(self.current_amount or 0) / float(self.target_amount) * 100
        return round(min(pct, 100.0), 1)

    @property
    def days_remaining(self) -> int | None:
        if self.deadline:
            return max(0, (self.deadline - date.today()).days)
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "target_amount": float(self.target_amount),
            "current_amount": float(self.current_amount or 0),
            "progress_pct": self.progress_pct,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "days_remaining": self.days_remaining,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
