from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import trip_service
from ..utils.response import success, error

trips_bp = Blueprint("trips", __name__)


@trips_bp.route("", methods=["GET"])
@jwt_required()
def list_trips():
    uid = int(get_jwt_identity())
    return success(trip_service.list_trips(uid))


@trips_bp.route("", methods=["POST"])
@jwt_required()
def create_trip():
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = trip_service.create_trip(uid, data)
        return success(result, "Trip created", 201)
    except (ValueError, KeyError) as e:
        return error(str(e))


@trips_bp.route("/<int:trip_id>", methods=["GET"])
@jwt_required()
def get_trip(trip_id):
    uid = int(get_jwt_identity())
    return success(trip_service.get_trip(uid, trip_id))


@trips_bp.route("/<int:trip_id>/members", methods=["POST"])
@jwt_required()
def add_member(trip_id):
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = trip_service.add_member(trip_id, data)
        return success(result, "Member added", 201)
    except (ValueError, KeyError) as e:
        return error(str(e))


@trips_bp.route("/<int:trip_id>/expenses", methods=["POST"])
@jwt_required()
def add_expense(trip_id):
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        member_ids = [int(x) for x in data.get("member_ids", [])]
        result = trip_service.add_expense(trip_id, data, member_ids)
        return success(result, "Expense added", 201)
    except (ValueError, KeyError) as e:
        return error(str(e))


@trips_bp.route("/<int:trip_id>/settlements", methods=["GET"])
@jwt_required()
def get_settlements(trip_id):
    uid = int(get_jwt_identity())
    return success(trip_service.get_settlements(trip_id))


@trips_bp.route("/<int:trip_id>", methods=["DELETE"])
@jwt_required()
def delete_trip(trip_id):
    uid = int(get_jwt_identity())
    trip_service.delete_trip(uid, trip_id)
    return success(None, "Trip deleted")
