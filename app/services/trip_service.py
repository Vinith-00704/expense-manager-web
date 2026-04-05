from datetime import date, datetime
from typing import List, Optional

from ..extensions import db
from ..models.trip import Trip, TripMember, TravelExpense, TravelExpenseParticipant
from ..models.user import User


def create_trip(user_id: int, data: dict) -> dict:
    from ..utils.validators import validate_amount, validate_date
    trip = Trip(
        user_id=user_id,
        destination=data["destination"].strip(),
        total_budget=validate_amount(data["total_budget"]),
        start_date=validate_date(data["start_date"]),
        end_date=validate_date(data["end_date"]),
        notes=data.get("notes", ""),
        status=data.get("status", "planning"),
    )
    db.session.add(trip)
    db.session.commit()
    return trip.to_dict()


def list_trips(user_id: int) -> List[dict]:
    user_trips = Trip.query.filter_by(user_id=user_id).all()
    member_trips = (
        Trip.query.join(TripMember, TripMember.trip_id == Trip.id)
        .filter(TripMember.user_id == user_id, Trip.user_id != user_id)
        .all()
    )
    all_trips = {t.id: t for t in user_trips + member_trips}
    result = []
    for trip in sorted(all_trips.values(), key=lambda t: t.start_date):
        d = trip.to_dict()
        d.update(_budget_status(trip))
        result.append(d)
    return result


def get_trip(user_id: int, trip_id: int) -> dict:
    trip = _assert_access(user_id, trip_id)
    d = trip.to_dict()
    d.update(_budget_status(trip))
    d["members"] = [m.to_dict() for m in trip.members]
    d["expenses"] = _trip_expenses(trip_id)
    return d


def _budget_status(trip: Trip) -> dict:
    total_spent = sum(float(e.amount) for e in trip.travel_expenses)
    total_days = max((trip.end_date - trip.start_date).days + 1, 1)
    daily_budget = float(trip.total_budget) / total_days
    today = date.today()
    days_elapsed = max((min(today, trip.end_date) - trip.start_date).days + 1, 1)
    allowed = daily_budget * min(days_elapsed, total_days)
    overspend = max(total_spent - allowed, 0)
    return {
        "total_spent": round(total_spent, 2),
        "daily_budget": round(daily_budget, 2),
        "overspend": round(overspend, 2),
        "remaining": round(float(trip.total_budget) - total_spent, 2),
    }


def add_member(trip_id: int, data: dict) -> dict:
    member = TripMember(trip_id=trip_id, member_name=data["member_name"].strip(), contact=data.get("contact"))
    db.session.add(member)
    db.session.commit()
    return member.to_dict()


def add_expense(trip_id: int, data: dict, member_ids: List[int]) -> dict:
    from ..utils.validators import validate_amount, validate_date
    amount = validate_amount(data["amount"])
    exp = TravelExpense(
        trip_id=trip_id,
        paid_by_member_id=data.get("paid_by_member_id"),
        expense_date=validate_date(data["expense_date"]),
        description=data["description"],
        amount=amount,
    )
    db.session.add(exp)
    db.session.flush()
    if member_ids:
        count = len(member_ids)
        base = round(amount / count, 2)
        remainder = round(amount - base * count, 2)
        for i, mid in enumerate(member_ids):
            share = base + (remainder if i == 0 else 0)
            db.session.add(TravelExpenseParticipant(travel_expense_id=exp.id, member_id=mid, share_amount=share))
    db.session.commit()
    return exp.to_dict()


def get_settlements(trip_id: int) -> List[dict]:
    members = TripMember.query.filter_by(trip_id=trip_id).all()
    if not members:
        return []
    member_ids = [m.id for m in members]
    name_map = {m.id: m.member_name for m in members}

    paid = {mid: 0.0 for mid in member_ids}
    for e in TravelExpense.query.filter_by(trip_id=trip_id).all():
        if e.paid_by_member_id:
            paid[e.paid_by_member_id] = paid.get(e.paid_by_member_id, 0) + float(e.amount)

    owed = {mid: 0.0 for mid in member_ids}
    for p in TravelExpenseParticipant.query.join(
        TravelExpense, TravelExpense.id == TravelExpenseParticipant.travel_expense_id
    ).filter(TravelExpense.trip_id == trip_id).all():
        owed[p.member_id] = owed.get(p.member_id, 0) + float(p.share_amount)

    from .room_service import _settle
    net = {mid: paid.get(mid, 0) - owed.get(mid, 0) for mid in member_ids}
    return _settle(net, name_map)


def _trip_expenses(trip_id: int) -> List[dict]:
    expenses = TravelExpense.query.filter_by(trip_id=trip_id).order_by(TravelExpense.expense_date.desc()).all()
    result = []
    for e in expenses:
        d = e.to_dict()
        if e.paid_by_member_id:
            m = TripMember.query.get(e.paid_by_member_id)
            d["payer_name"] = m.member_name if m else "Unknown"
        else:
            d["payer_name"] = "—"
        result.append(d)
    return result


def delete_trip(user_id: int, trip_id: int) -> None:
    trip = Trip.query.filter_by(id=trip_id, user_id=user_id).first_or_404()
    db.session.delete(trip)
    db.session.commit()


def _assert_access(user_id: int, trip_id: int) -> Trip:
    trip = Trip.query.get_or_404(trip_id)
    is_owner = trip.user_id == user_id
    is_member = TripMember.query.filter_by(trip_id=trip_id, user_id=user_id).first() is not None
    if not is_owner and not is_member:
        from flask import abort; abort(403)
    return trip
