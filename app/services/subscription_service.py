from datetime import date
from typing import List, Optional
from dateutil.relativedelta import relativedelta

from ..extensions import db
from ..models.subscription import Subscription, CYCLE_MONTHS


def add_subscription(user_id: int, data: dict) -> dict:
    from ..utils.validators import validate_amount, validate_date
    sub = Subscription(
        user_id=user_id,
        name=data["name"].strip(),
        amount=validate_amount(data["amount"]),
        billing_cycle=data.get("billing_cycle", "monthly"),
        last_paid_date=validate_date(data["last_paid_date"]),
        category=data.get("category", "Other"),
        notes=data.get("notes", ""),
    )
    db.session.add(sub)
    db.session.commit()
    return sub.to_dict(include_renewal=True)


def list_subscriptions(user_id: int) -> List[dict]:
    subs = Subscription.query.filter_by(user_id=user_id).order_by(Subscription.name).all()
    return [s.to_dict(include_renewal=True) for s in subs]


def get_subscription(user_id: int, sub_id: int) -> Optional[dict]:
    sub = Subscription.query.filter_by(id=sub_id, user_id=user_id).first()
    return sub.to_dict(include_renewal=True) if sub else None


def update_subscription(user_id: int, sub_id: int, data: dict) -> dict:
    from ..utils.validators import validate_amount, validate_date
    sub = Subscription.query.filter_by(id=sub_id, user_id=user_id).first_or_404()
    if "name" in data:
        sub.name = data["name"].strip()
    if "amount" in data:
        sub.amount = validate_amount(data["amount"])
    if "billing_cycle" in data:
        sub.billing_cycle = data["billing_cycle"]
    if "last_paid_date" in data:
        sub.last_paid_date = validate_date(data["last_paid_date"])
    if "category" in data:
        sub.category = data["category"]
    if "notes" in data:
        sub.notes = data["notes"]
    if "is_active" in data:
        sub.is_active = bool(data["is_active"])
    db.session.commit()
    return sub.to_dict(include_renewal=True)


def delete_subscription(user_id: int, sub_id: int) -> None:
    sub = Subscription.query.filter_by(id=sub_id, user_id=user_id).first_or_404()
    db.session.delete(sub)
    db.session.commit()


def get_monthly_total(user_id: int) -> float:
    """Sum of all active subscriptions normalised to monthly cost."""
    subs = Subscription.query.filter_by(user_id=user_id, is_active=True).all()
    total = 0.0
    for s in subs:
        monthly_factor = {1: 1, 3: 1 / 3, 12: 1 / 12}.get(CYCLE_MONTHS.get(s.billing_cycle, 1), 1)
        total += float(s.amount) * monthly_factor
    return round(total, 2)
