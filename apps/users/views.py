"""
HTTP layer for the users app.

Keep views thin: validate with serializers, delegate to services, format responses.
"""

from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView as _JWTTokenRefreshView

from apps.users.serializers import (
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
    UserMeSerializer,
)
from apps.users.services import (
    AuthenticationError,
    PasswordChangeError,
    UserService,
)


class RegisterView(APIView):
    """POST /api/v1/auth/register/ — create a new user (public, no JWT)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserService.register_user(serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError(
                {'email': ['A user with this email already exists.']},
            ) from exc

        return Response(
            {
                'success': True,
                'message': 'User registered successfully.',
                'data': UserMeSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/v1/auth/login/ — email login, returns JWT pair + user."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = UserService.login_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
            )
        except AuthenticationError as exc:
            raise ValidationError({'non_field_errors': [str(exc)]}) from exc

        return Response(
            {
                'success': True,
                'message': 'Login successful.',
                'data': {
                    'access': result['access'],
                    'refresh': result['refresh'],
                    'user': UserMeSerializer(result['user']).data,
                },
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(_JWTTokenRefreshView):
    """
    POST /api/v1/auth/refresh/ — new access token (and refresh when rotation is on).
    Uses SimpleJWT serializer: rotation + blacklist from settings.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response(
            {
                'success': True,
                'message': 'Token refreshed successfully.',
                'data': response.data,
            },
            status=response.status_code,
        )


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — blacklist refresh token (authenticated)."""

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        UserService.logout_user(serializer.validated_data['refresh'])
        return Response(
            {
                'success': True,
                'message': 'Logged out successfully.',
                'data': {},
            },
            status=status.HTTP_200_OK,
        )


class UserMeView(APIView):
    """GET/PATCH /api/v1/users/me/ — current user profile (authenticated)."""

    def get(self, request):
        return Response(
            {
                'success': True,
                'message': '',
                'data': UserMeSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        serializer = UserMeSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = UserService.update_profile(
            request.user,
            validated_data=serializer.validated_data,
        )
        return Response(
            {
                'success': True,
                'message': 'Profile updated successfully.',
                'data': UserMeSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class PasswordChangeView(APIView):
    """POST /api/v1/auth/password/change/ — change password (authenticated)."""

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request, 'user': request.user},
        )
        serializer.is_valid(raise_exception=True)

        try:
            UserService.change_password(
                request.user,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password'],
            )
        except PasswordChangeError as exc:
            raise ValidationError({'old_password': [str(exc)]}) from exc

        return Response(
            {
                'success': True,
                'message': 'Password changed successfully.',
                'data': {},
            },
            status=status.HTTP_200_OK,
        )
