"""Black-box tests for the Auth Service."""

import pytest

from srmss.models import Administrator, hash_password, make_salt
from srmss.services.auth_service import AuthError


def _add_user(container, username="admin", password="depot123"):
    salt = make_salt()
    container.users.add(Administrator(1, username, hash_password(password, salt), salt))


def test_login_success_returns_token(container):
    _add_user(container)
    token = container.auth.login("admin", "depot123")
    assert isinstance(token, str) and token


def test_login_wrong_password_raises(container):
    _add_user(container)
    with pytest.raises(AuthError):
        container.auth.login("admin", "wrong")


def test_login_unknown_user_raises(container):
    with pytest.raises(AuthError):
        container.auth.login("ghost", "x")


def test_account_locks_after_three_failures(container):
    _add_user(container)
    for _ in range(3):
        with pytest.raises(AuthError):
            container.auth.login("admin", "wrong")
    with pytest.raises(AuthError):           # correct password now refused
        container.auth.login("admin", "depot123")


def test_has_role(container):
    _add_user(container)
    token = container.auth.login("admin", "depot123")
    assert container.auth.has_role(token, "Administrator") is True
    assert container.auth.has_role(token, "Clerk") is False


def test_logout_clears_session(container):
    _add_user(container)
    token = container.auth.login("admin", "depot123")
    container.auth.logout(token)
    assert container.auth.current_user(token) is None
