from datetime import datetime
from ..extensions import db


class Trip(db.Model):
    __tablename__ = "trips"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    destination = db.Column(db.String(120), nullable=False)
    total_budget = db.Column(db.Numeric(12, 2), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String(255))
    status = db.Column(
        db.Enum("planning", "active", "completed"), default="planning"
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship(
        "TripMember", backref="trip", lazy="dynamic", cascade="all, delete-orphan"
    )
    travel_expenses = db.relationship(
        "TravelExpense", backref="trip", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "destination": self.destination,
            "total_budget": float(self.total_budget),
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TripMember(db.Model):
    __tablename__ = "trip_members"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(
        db.Integer, db.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    member_name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(120))
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "member_name": self.member_name,
            "contact": self.contact,
            "user_id": self.user_id,
        }


class TravelExpense(db.Model):
    __tablename__ = "travel_expenses"

    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(
        db.Integer, db.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    paid_by_member_id = db.Column(
        db.Integer,
        db.ForeignKey("trip_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    expense_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participants = db.relationship(
        "TravelExpenseParticipant",
        backref="travel_expense",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "paid_by_member_id": self.paid_by_member_id,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "description": self.description,
            "amount": float(self.amount),
        }


class TravelExpenseParticipant(db.Model):
    __tablename__ = "travel_expense_participants"

    id = db.Column(db.Integer, primary_key=True)
    travel_expense_id = db.Column(
        db.Integer,
        db.ForeignKey("travel_expenses.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id = db.Column(
        db.Integer,
        db.ForeignKey("trip_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    share_amount = db.Column(db.Numeric(12, 2), nullable=False)
