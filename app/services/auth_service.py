import bcrypt
from flask import current_app
from flask_jwt_extended import create_access_token

from ..extensions import db
from ..models.user import User


def _pepper(password: str) -> str:
    return password + current_app.config["PASSWORD_PEPPER"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pepper(password).encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(_pepper(password).encode(), password_hash.encode())


def register_user(data: dict) -> dict:
    username = data.get("username", "").strip().lower()
    full_name = data.get("full_name", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip() or None
    phone = data.get("phone", "").strip() or None

    if not username or not full_name or not password:
        raise ValueError("username, full_name and password are required")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if User.query.filter_by(username=username).first():
        raise ValueError("Username already taken")
    if email and User.query.filter_by(email=email).first():
        raise ValueError("Email already registered")
    if phone and User.query.filter_by(phone=phone).first():
        raise ValueError("Phone already registered")

    user = User(
        username=username,
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        currency=data.get("currency", "₹"),
        monthly_salary=float(data.get("monthly_salary", 0) or 0),
    )
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return {"user": user.to_dict(), "token": token}


def login_user(identifier: str, password: str) -> dict:
    """Accept username or email as the login identifier."""
    identifier = identifier.strip()
    # Try username first, then email
    user = User.query.filter_by(username=identifier.lower()).first()
    if not user and "@" in identifier:
        user = User.query.filter_by(email=identifier.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid username/email or password")
    token = create_access_token(identity=str(user.id))
    return {"user": user.to_dict(), "token": token}


def update_profile(user_id: int, data: dict) -> dict:
    user = User.query.get_or_404(user_id)
    user.full_name = data.get("full_name", user.full_name).strip()
    user.email = data.get("email", user.email)
    user.phone = data.get("phone", user.phone)
    user.monthly_salary = float(data.get("monthly_salary", user.monthly_salary) or 0)
    user.age = int(data.get("age", user.age) or 0)
    user.currency = data.get("currency", user.currency) or "₹"
    db.session.commit()
    return user.to_dict()


def change_password(user_id: int, old_password: str, new_password: str) -> None:
    user = User.query.get_or_404(user_id)
    if not verify_password(old_password, user.password_hash):
        raise ValueError("Current password is incorrect")
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters")
    user.password_hash = hash_password(new_password)
    db.session.commit()
