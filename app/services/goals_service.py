"""
app/services/goals_service.py
CRUD and progress tracking for financial goals.
"""
from datetime import date
from decimal import Decimal

from ..extensions import db
from ..models.financial_goal import FinancialGoal


def create_goal(user_id: int, data: dict) -> FinancialGoal:
    goal = FinancialGoal(
        user_id        = user_id,
        name           = data["name"],
        description    = data.get("description"),
        category       = data.get("category", "Other"),
        target_amount  = Decimal(str(data["target_amount"])),
        current_amount = Decimal(str(data.get("current_amount", 0))),
        deadline       = _parse_date(data.get("deadline")),
    )
    db.session.add(goal)
    db.session.commit()
    return goal


def list_goals(user_id: int) -> list[dict]:
    goals = FinancialGoal.query.filter_by(user_id=user_id).order_by(
        FinancialGoal.created_at.desc()
    ).all()
    return [g.to_dict() for g in goals]


def update_goal(goal_id: int, user_id: int, data: dict) -> FinancialGoal | None:
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return None
    for field in ("name", "description", "category", "status"):
        if field in data:
            setattr(goal, field, data[field])
    if "target_amount" in data:
        goal.target_amount = Decimal(str(data["target_amount"]))
    if "current_amount" in data:
        goal.current_amount = Decimal(str(data["current_amount"]))
        # Auto-achieve if target reached
        if goal.current_amount >= goal.target_amount:
            goal.status = "achieved"
    if "deadline" in data:
        goal.deadline = _parse_date(data["deadline"])
    db.session.commit()
    return goal


def delete_goal(goal_id: int, user_id: int) -> bool:
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return False
    db.session.delete(goal)
    db.session.commit()
    return True


def _parse_date(val) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(val)).date()
    except (ValueError, TypeError):
        return None
