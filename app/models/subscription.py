from datetime import datetime
from ..extensions import db

BILLING_CYCLES = ["monthly", "quarterly", "yearly"]
CYCLE_MONTHS = {"monthly": 1, "quarterly": 3, "yearly": 12}


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    billing_cycle = db.Column(
        db.Enum("monthly", "quarterly", "yearly"), nullable=False, default="monthly"
    )
    last_paid_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), default="Other")
    notes = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_renewal=False):
        d = {
            "id": self.id,
            "name": self.name,
            "amount": float(self.amount),
            "billing_cycle": self.billing_cycle,
            "last_paid_date": self.last_paid_date.isoformat() if self.last_paid_date else None,
            "category": self.category,
            "notes": self.notes,
            "is_active": self.is_active,
        }
        if include_renewal:
            from dateutil.relativedelta import relativedelta
            months = CYCLE_MONTHS.get(self.billing_cycle, 1)
            next_renewal = self.last_paid_date + relativedelta(months=months)
            days_left = (next_renewal - datetime.utcnow().date()).days
            d["next_renewal"] = next_renewal.isoformat()
            d["days_left"] = days_left
        return d
