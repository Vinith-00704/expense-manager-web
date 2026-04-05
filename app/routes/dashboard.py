from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import dashboard_service
from ..utils.response import success

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
def summary():
    uid = int(get_jwt_identity())
    return success({
        "summary": dashboard_service.get_summary(uid),
        "savings_history": dashboard_service.get_savings_history(uid),
        "upcoming": dashboard_service.get_upcoming_expenses(uid),
        "alerts": dashboard_service.get_alerts(uid),
        "category_breakdown": dashboard_service.get_category_breakdown(uid),
    })
