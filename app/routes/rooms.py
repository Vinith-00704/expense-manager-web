from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import room_service
from ..utils.response import success, error

rooms_bp = Blueprint("rooms", __name__)


@rooms_bp.route("", methods=["GET"])
@jwt_required()
def list_rooms():
    uid = int(get_jwt_identity())
    return success(room_service.list_rooms(uid))


@rooms_bp.route("", methods=["POST"])
@jwt_required()
def create_room():
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = room_service.create_room(uid, data.get("name", "New Room"), data.get("description", ""))
        return success(result, "Room created", 201)
    except ValueError as e:
        return error(str(e))


@rooms_bp.route("/<int:room_id>", methods=["GET"])
@jwt_required()
def get_room(room_id):
    uid = int(get_jwt_identity())
    return success(room_service.get_room(uid, room_id))


@rooms_bp.route("/<int:room_id>/members", methods=["POST"])
@jwt_required()
def add_member(room_id):
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = room_service.add_member_by_username(room_id, uid, data.get("username", ""))
        return success(result, "Member added", 201)
    except ValueError as e:
        return error(str(e))


@rooms_bp.route("/<int:room_id>/expenses", methods=["GET"])
@jwt_required()
def get_ledger(room_id):
    uid = int(get_jwt_identity())
    return success(room_service.get_ledger(room_id))


@rooms_bp.route("/<int:room_id>/expenses", methods=["POST"])
@jwt_required()
def add_expense(room_id):
    try:
        uid = int(get_jwt_identity())
        data = request.get_json(force=True)
        member_ids = [int(x) for x in data.get("member_ids", [])]
        result = room_service.add_room_expense(room_id, uid, data, member_ids)
        return success(result, "Expense added", 201)
    except (ValueError, KeyError) as e:
        return error(str(e))


@rooms_bp.route("/<int:room_id>/settlements", methods=["GET"])
@jwt_required()
def get_settlements(room_id):
    uid = int(get_jwt_identity())
    return success(room_service.get_settlements(room_id))


@rooms_bp.route("/<int:room_id>", methods=["DELETE"])
@jwt_required()
def delete_room(room_id):
    uid = int(get_jwt_identity())
    room_service.delete_room(uid, room_id)
    return success(None, "Room deleted")
