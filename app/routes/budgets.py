"""
app/routes/budgets.py  —  /api/budgets/*
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.response import success, error
from ..services import budget_service as svc

budgets_bp = Blueprint("budgets", __name__)


@budgets_bp.post("/")
@jwt_required()
def set_budget():
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}
    if not body.get("category") or not body.get("monthly_limit"):
        return error("category and monthly_limit are required.", 400)
    budget = svc.set_budget(
        user_id, body["category"], body["monthly_limit"], body.get("month")
    )
    return success(budget.to_dict(), "Budget saved.")


@budgets_bp.get("/")
@jwt_required()
def list_budgets():
    user_id = int(get_jwt_identity())
    month   = request.args.get("month")
    return success(svc.list_budgets(user_id, month))


@budgets_bp.get("/status")
@jwt_required()
def status():
    """GET /api/budgets/status?month=2026-05 — spend vs limit per category."""
    user_id = int(get_jwt_identity())
    month   = request.args.get("month")
    return success(svc.get_monthly_status(user_id, month))


@budgets_bp.delete("/<int:budget_id>")
@jwt_required()
def delete(budget_id: int):
    user_id = int(get_jwt_identity())
    if not svc.delete_budget(budget_id, user_id):
        return error("Budget not found.", 404)
    return success(None, "Budget deleted.")
