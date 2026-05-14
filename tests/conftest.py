"""
tests/conftest.py
Pytest fixtures shared across all test modules.
"""
import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create a test Flask app using an in-memory SQLite DB."""
    test_app = create_app("testing")
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    })
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()
