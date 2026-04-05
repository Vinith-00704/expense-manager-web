from datetime import datetime
from ..extensions import db


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship(
        "RoomMember", backref="room", lazy="dynamic", cascade="all, delete-orphan"
    )
    expenses = db.relationship(
        "RoomExpense", backref="room", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RoomMember(db.Model):
    __tablename__ = "room_members"
    __table_args__ = (db.UniqueConstraint("room_id", "user_id", name="uq_room_user"),)

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = db.Column(db.Enum("owner", "member"), default="member")
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)


class RoomExpense(db.Model):
    __tablename__ = "room_expenses"

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(
        db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    paid_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    split_type = db.Column(db.Enum("equal"), default="equal")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participants = db.relationship(
        "RoomExpenseParticipant",
        backref="expense",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "paid_by": self.paid_by,
            "description": self.description,
            "amount": float(self.amount),
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "split_type": self.split_type,
        }


class RoomExpenseParticipant(db.Model):
    __tablename__ = "room_expense_participants"

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(
        db.Integer,
        db.ForeignKey("room_expenses.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    share_amount = db.Column(db.Numeric(12, 2), nullable=False)
