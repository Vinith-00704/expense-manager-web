from flask import jsonify


def success(data=None, message: str = None, status: int = 200):
    """Standard success envelope."""
    return jsonify({"success": True, "data": data, "message": message}), status


def error(message: str, status: int = 400):
    """Standard error envelope."""
    return jsonify({"success": False, "error": message}), status
