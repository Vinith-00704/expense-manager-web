from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import analytics_service
from ..utils.response import success

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/cashflow", methods=["GET"])
@jwt_required()
def cashflow():
    uid = int(get_jwt_identity())
    months = int(request.args.get("months", 12))
    return success(analytics_service.get_cashflow_history(uid, months))


@analytics_bp.route("/categories", methods=["GET"])
@jwt_required()
def categories():
    uid = int(get_jwt_identity())
    months = int(request.args.get("months", 3))
    return success(analytics_service.get_category_breakdown(uid, months))


@analytics_bp.route("/health", methods=["GET"])
@jwt_required()
def health():
    uid = int(get_jwt_identity())
    return success(analytics_service.get_health_score(uid))
