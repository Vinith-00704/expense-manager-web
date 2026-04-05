from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import subscription_service
from ..utils.response import success, error

subscriptions_bp = Blueprint("subscriptions", __name__)


@subscriptions_bp.route("", methods=["GET"])
@jwt_required()
def list_subscriptions():
    uid = int(get_jwt_identity())
    return success(subscription_service.list_subscriptions(uid))


@subscriptions_bp.route("", methods=["POST"])
@jwt_required()
def add_subscription():
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = subscription_service.add_subscription(uid, data)
        return success(result, "Subscription added", 201)
    except (ValueError, KeyError) as e:
        return error(str(e))


@subscriptions_bp.route("/<int:sub_id>", methods=["PUT"])
@jwt_required()
def update_subscription(sub_id):
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = subscription_service.update_subscription(uid, sub_id, data)
        return success(result, "Updated")
    except ValueError as e:
        return error(str(e))


@subscriptions_bp.route("/<int:sub_id>", methods=["DELETE"])
@jwt_required()
def delete_subscription(sub_id):
    uid = int(get_jwt_identity())
    subscription_service.delete_subscription(uid, sub_id)
    return success(None, "Deleted")


@subscriptions_bp.route("/monthly-total", methods=["GET"])
@jwt_required()
def monthly_total():
    uid = int(get_jwt_identity())
    return success({"monthly_total": subscription_service.get_monthly_total(uid)})
