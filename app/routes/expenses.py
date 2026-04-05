from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import expense_service
from ..utils.response import success, error

expenses_bp = Blueprint("expenses", __name__)


@expenses_bp.route("", methods=["GET"])
@jwt_required()
def list_expenses():
    uid = int(get_jwt_identity())
    rows = expense_service.list_expenses(
        uid,
        entry_type=request.args.get("entry_type"),
        category=request.args.get("category"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        limit=int(request.args.get("limit", 100)),
    )
    return success(rows)


@expenses_bp.route("", methods=["POST"])
@jwt_required()
def add_expense():
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = expense_service.add_expense(uid, data)
        return success(result, "Expense added", 201)
    except (ValueError, KeyError) as e:
        return error(str(e))


@expenses_bp.route("/<int:expense_id>", methods=["GET"])
@jwt_required()
def get_expense(expense_id):
    uid = int(get_jwt_identity())
    exp = expense_service.get_expense(uid, expense_id)
    if not exp:
        return error("Not found", 404)
    return success(exp)


@expenses_bp.route("/<int:expense_id>", methods=["PUT"])
@jwt_required()
def update_expense(expense_id):
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = expense_service.update_expense(uid, expense_id, data)
        return success(result, "Updated")
    except ValueError as e:
        return error(str(e))


@expenses_bp.route("/<int:expense_id>", methods=["DELETE"])
@jwt_required()
def delete_expense(expense_id):
    uid = int(get_jwt_identity())
    expense_service.delete_expense(uid, expense_id)
    return success(None, "Deleted")


@expenses_bp.route("/meta", methods=["GET"])
@jwt_required()
def meta():
    return success({
        "categories": expense_service.get_categories(),
        "payment_modes": expense_service.get_payment_modes(),
    })
