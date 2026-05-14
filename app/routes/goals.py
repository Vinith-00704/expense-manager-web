"""
app/routes/goals.py  —  /api/goals/*
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.response import success, error
from ..services import goals_service as svc

goals_bp = Blueprint("goals", __name__)


@goals_bp.post("/")
@jwt_required()
def create():
    user_id = int(get_jwt_identity())
    body = request.get_json(silent=True) or {}
    if not body.get("name") or not body.get("target_amount"):
        return error("name and target_amount are required.", 400)
    goal = svc.create_goal(user_id, body)
    return success(goal.to_dict(), "Goal created.", 201)


@goals_bp.get("/")
@jwt_required()
def list_goals():
    user_id = int(get_jwt_identity())
    return success(svc.list_goals(user_id))


@goals_bp.put("/<int:goal_id>")
@jwt_required()
def update(goal_id: int):
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}
    goal    = svc.update_goal(goal_id, user_id, body)
    if not goal:
        return error("Goal not found.", 404)
    return success(goal.to_dict(), "Goal updated.")


@goals_bp.delete("/<int:goal_id>")
@jwt_required()
def delete(goal_id: int):
    user_id = int(get_jwt_identity())
    if not svc.delete_goal(goal_id, user_id):
        return error("Goal not found.", 404)
    return success(None, "Goal deleted.")
