"""
Service layer for user-related operations.

Views validate input via serializers, call these methods, and map results
to HTTP. Business rules live here so they are reusable from tests, Celery,
and management commands (ADR-0003).
"""

from __future__ import annotations

from typing import Any, Mapping

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserServiceError(Exception):
    """Base for user-domain failures; views translate to HTTP status codes."""


class RegistrationError(UserServiceError):
    """User could not be registered (e.g. duplicate email)."""


class AuthenticationError(UserServiceError):
    """Login failed (invalid credentials or inactive account)."""


class PasswordChangeError(UserServiceError):
    """Password could not be changed (e.g. wrong old password)."""


class UserService:
    """User identity and authentication operations."""

    @staticmethod
    def _normalize_email(email: str) -> str:
        return (email or '').strip().lower()

    @classmethod
    def register_user(cls, validated_data: Mapping[str, Any]) -> User:
        """
        Create a user from RegisterSerializer.validated_data.

        Caller must run serializer validation first. Password hashing and
        email normalization happen via UserManager.create_user.
        """
        email = cls._normalize_email(validated_data['email'])
        password = validated_data['password']
        role = validated_data.get('role', User.Role.USER)

        try:
            return User.objects.create_user(
                email=email,
                password=password,
                role=role,
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
            )
        except IntegrityError as exc:
            raise RegistrationError(
                'A user with this email already exists.',
            ) from exc

    @classmethod
    def authenticate_user(cls, *, email: str, password: str) -> User:
        """
        Authenticate by email and password. Returns the user on success.

        Uses Django's authenticate() with USERNAME_FIELD=email. Raises
        AuthenticationError with a generic message on failure (no account
        enumeration).
        """
        normalized_email = cls._normalize_email(email)
        user = authenticate(username=normalized_email, password=password)

        if user is None:
            raise AuthenticationError('Invalid email or password.')

        if not user.is_active:
            raise AuthenticationError('User account is disabled.')

        return user

    @classmethod
    def login_user(cls, *, email: str, password: str) -> dict[str, Any]:
        """
        Authenticate by email/password and issue a JWT access + refresh pair.
        """
        user = cls.authenticate_user(email=email, password=password)
        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    @staticmethod
    def change_password(
        user: User,
        *,
        old_password: str,
        new_password: str,
    ) -> User:
        """
        Replace the user's password after verifying the current one.

        Caller may validate via PasswordChangeSerializer first; this method
        re-checks old_password so the service stays safe when called without
        a serializer (e.g. tests or tasks).
        """
        if not user.check_password(old_password):
            raise PasswordChangeError('Old password is incorrect.')

        user.set_password(new_password)
        user.save(update_fields=['password'])
        return user

    @staticmethod
    def update_profile(user: User, *, validated_data: Mapping[str, Any]) -> User:
        """Update writable profile fields from UserMeSerializer.validated_data."""
        update_fields = []
        for field in ('first_name', 'last_name'):
            if field in validated_data:
                setattr(user, field, validated_data[field])
                update_fields.append(field)
        if update_fields:
            user.save(update_fields=update_fields)
        return user

    @staticmethod
    def logout_user(refresh_token: str) -> bool:
        """
        Blacklist a refresh token so it cannot mint new access tokens.

        Returns True if the token was blacklisted, False if the token was
        missing or invalid (idempotent logout — safe to call with stale tokens).
        """
        if not refresh_token or not str(refresh_token).strip():
            return False

        try:
            RefreshToken(str(refresh_token).strip()).blacklist()
        except TokenError:
            return False

        return True
