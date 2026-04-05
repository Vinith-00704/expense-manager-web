from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import auth_service
from ..models.user import User
from ..utils.response import success, error

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json(force=True)
        result = auth_service.register_user(data)
        return success(result, "Account created successfully", 201)
    except ValueError as e:
        return error(str(e))


@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json(force=True)
        # Accept 'identifier' (username or email) or legacy 'username' key
        identifier = data.get("identifier") or data.get("username", "")
        result = auth_service.login_user(identifier, data.get("password", ""))
        return success(result)
    except ValueError as e:
        return error(str(e), 401)


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return success(user.to_dict())


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(force=True)
        result = auth_service.update_profile(user_id, data)
        return success(result, "Profile updated")
    except ValueError as e:
        return error(str(e))


@auth_bp.route("/password", methods=["PUT"])
@jwt_required()
def change_password():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(force=True)
        auth_service.change_password(user_id, data.get("old_password", ""), data.get("new_password", ""))
        return success(None, "Password changed")
    except ValueError as e:
        return error(str(e))
