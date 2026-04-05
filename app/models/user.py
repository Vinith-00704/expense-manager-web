from datetime import datetime
from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    monthly_salary = db.Column(db.Numeric(12, 2), default=0)
    age = db.Column(db.Integer, default=0)
    currency = db.Column(db.String(10), default="₹")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    expenses = db.relationship(
        "Expense", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    subscriptions = db.relationship(
        "Subscription", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    rooms_owned = db.relationship(
        "Room", backref="owner", lazy="dynamic", cascade="all, delete-orphan"
    )
    trips = db.relationship(
        "Trip", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    alerts = db.relationship(
        "Alert", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "monthly_salary": float(self.monthly_salary or 0),
            "age": self.age or 0,
            "currency": self.currency or "₹",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
