"""
services/auth_service.py — Auth Service (Tier 2).

Maps to the "Login" use case and the User.login() operation. Handles password
verification (salted PBKDF2 hashes via the model), session tokens, role checks,
and account lockout after repeated failures.
"""

from __future__ import annotations

import secrets
from typing import Dict, Optional

from srmss.data.repositories import UserRepository
from srmss.models import User

MAX_FAILED_ATTEMPTS = 3


class AuthError(Exception):
    """Raised on any failed login (unknown user, bad password, locked)."""


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users
        self._sessions: Dict[str, str] = {}     # token -> username
        self._failed: Dict[str, int] = {}        # username -> failed count
        self._locked: set[str] = set()

    def login(self, username: str, password: str) -> str:
        """Return a session token on success; raise AuthError otherwise."""
        if username in self._locked:
            raise AuthError("Account is locked")

        user = self.users.get_by_username(username)
        if user is None:
            raise AuthError("Unknown username")

        if user.login(password):                 # User.login() from the model
            self._failed[username] = 0
            token = secrets.token_hex(16)
            self._sessions[token] = username
            return token

        self._failed[username] = self._failed.get(username, 0) + 1
        if self._failed[username] >= MAX_FAILED_ATTEMPTS:
            self._locked.add(username)
        raise AuthError("Invalid credentials")

    def current_user(self, token: str) -> Optional[User]:
        username = self._sessions.get(token)
        return self.users.get_by_username(username) if username else None

    def has_role(self, token: str, role: str) -> bool:
        user = self.current_user(token)
        return user is not None and user.role == role

    def logout(self, token: str) -> None:
        self._sessions.pop(token, None)
