from datetime import datetime
from ..extensions import db

CATEGORIES = [
    "Food & Dining", "Transportation", "Shopping", "Entertainment",
    "Healthcare", "Bills & Utilities", "Education", "Travel",
    "Personal Care", "Home & Rent", "Investments", "Salary",
    "Freelance", "Business", "Gift", "Other",
]

PAYMENT_MODES = ["Cash", "UPI", "Card", "Net Banking", "Wallet", "Other"]


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, index=True)
    payment_mode = db.Column(db.String(50), default="Cash")
    notes = db.Column(db.String(255))
    entry_type = db.Column(
        db.Enum("expense", "income"), nullable=False, default="expense"
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "amount": float(self.amount),
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "payment_mode": self.payment_mode,
            "notes": self.notes,
            "entry_type": self.entry_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
