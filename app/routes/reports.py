from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import report_service
from ..utils.response import error

reports_bp = Blueprint("reports", __name__)


def _send(buf, mime, ext, name):
    return send_file(buf, mimetype=mime, as_attachment=True, download_name=f"{name}.{ext}")


@reports_bp.route("/expenses", methods=["GET"])
@jwt_required()
def expenses():
    uid = int(get_jwt_identity())
    fmt = request.args.get("format", "csv")
    buf, mime, ext = report_service.expense_report(uid, fmt)
    return _send(buf, mime, ext, "expenses")


@reports_bp.route("/subscriptions", methods=["GET"])
@jwt_required()
def subscriptions():
    uid = int(get_jwt_identity())
    fmt = request.args.get("format", "csv")
    buf, mime, ext = report_service.subscription_report(uid, fmt)
    return _send(buf, mime, ext, "subscriptions")


@reports_bp.route("/cashflow", methods=["GET"])
@jwt_required()
def cashflow():
    uid = int(get_jwt_identity())
    fmt = request.args.get("format", "csv")
    buf, mime, ext = report_service.cashflow_report(uid, fmt)
    return _send(buf, mime, ext, "cashflow")
