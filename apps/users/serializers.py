from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """
    Registration input schema. Validates shape and rules only;
    user creation belongs in UserService (ADR-0003).
    """

    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False, default='')
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False, default='')
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        default=User.Role.USER,
        required=False,
    )

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate_role(self, value: str) -> str:
        if value != User.Role.USER:
            raise serializers.ValidationError('Registration is only allowed with the user role.')
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'},
            )
        attrs.pop('confirm_password', None)
        return attrs


class LogoutSerializer(serializers.Serializer):
    """Logout input schema: refresh token to blacklist."""

    refresh = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    """
    Login input schema. Validates shape only; credential check is in UserService.
    """

    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class UserMeSerializer(serializers.ModelSerializer):
    """
    Safe representation of the authenticated user for GET/PATCH /me.
    Only first_name and last_name are writable.
    """

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'email',
            'role',
            'is_active',
            'created_at',
            'updated_at',
        )


class PasswordChangeSerializer(serializers.Serializer):
    """
    Password change input schema. Validates credentials and new password rules;
    persisting the new hash belongs in UserService (ADR-0003).
    """

    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_old_password(self, value: str) -> str:
        user = self._get_user()
        if user is None or not user.is_authenticated:
            raise serializers.ValidationError('Authentication required.')
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def _get_user(self):
        user = self.context.get('user')
        if user is None:
            request = self.context.get('request')
            user = getattr(request, 'user', None) if request else None
        return user

    def validate_new_password(self, value: str) -> str:
        validate_password(value, user=self._get_user())
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'},
            )
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': 'New password must differ from the old password.'},
            )
        attrs.pop('confirm_password', None)
        return attrs
