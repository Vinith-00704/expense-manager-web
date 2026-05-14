"""
Model: Budget
Monthly spending limit per category. Compared against actual expenses
to generate overspend alerts and dashboard progress indicators.
"""
from datetime import datetime
from ..extensions import db


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category = db.Column(db.String(50), nullable=False)
    monthly_limit = db.Column(db.Numeric(12, 2), nullable=False)

    # Stored as "YYYY-MM" string for easy filtering
    month = db.Column(db.String(7), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Composite uniqueness: one budget per category per month per user
    __table_args__ = (
        db.UniqueConstraint("user_id", "category", "month", name="uq_budget_user_cat_month"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category,
            "monthly_limit": float(self.monthly_limit),
            "month": self.month,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
