import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()

REGISTER_URL = reverse('users:auth-register')
LOGIN_URL = reverse('users:auth-login')
LOGOUT_URL = reverse('users:auth-logout')
REFRESH_URL = reverse('users:auth-refresh')
ME_URL = reverse('users:users-me')
PASSWORD_CHANGE_URL = reverse('users:auth-password-change')

VALID_PASSWORD = 'TestPass123!'
VALID_NEW_PASSWORD = 'NewPass456@'


def _register_payload(**overrides):
    payload = {
        'email': 'newuser@example.com',
        'password': VALID_PASSWORD,
        'confirm_password': VALID_PASSWORD,
        'first_name': 'Ada',
        'last_name': 'Lovelace',
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestRegisterAPI:
    def test_register_success_returns_201_and_envelope(self, api_client):
        response = api_client.post(REGISTER_URL, _register_payload(), format='json')

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body['success'] is True
        assert body['message'] == 'User registered successfully.'
        data = body['data']
        assert data['email'] == 'newuser@example.com'
        assert data['first_name'] == 'Ada'
        assert data['last_name'] == 'Lovelace'
        assert data['role'] == User.Role.USER
        assert data['is_active'] is True
        assert 'id' in data
        assert 'created_at' in data

    def test_register_persists_user_in_database(self, api_client):
        api_client.post(REGISTER_URL, _register_payload(), format='json')

        user = User.objects.get(email='newuser@example.com')
        assert user.first_name == 'Ada'
        assert user.last_name == 'Lovelace'
        assert user.check_password(VALID_PASSWORD)

    def test_register_duplicate_email_returns_400(self, api_client):
        payload = _register_payload()
        api_client.post(REGISTER_URL, payload, format='json')

        response = api_client.post(REGISTER_URL, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.json()

    def test_register_password_mismatch_returns_400(self, api_client):
        response = api_client.post(
            REGISTER_URL,
            _register_payload(confirm_password='DifferentPass123!'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'confirm_password' in response.json()

    def test_register_missing_email_returns_400(self, api_client):
        payload = _register_payload()
        del payload['email']

        response = api_client.post(REGISTER_URL, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.json()


@pytest.mark.django_db
class TestLoginAPI:
    @pytest.fixture
    def registered_user(self, api_client):
        payload = _register_payload(email='loginuser@example.com')
        api_client.post(REGISTER_URL, payload, format='json')
        return payload

    def test_login_success_returns_tokens_and_user(self, api_client, registered_user):
        response = api_client.post(
            LOGIN_URL,
            {
                'email': registered_user['email'],
                'password': registered_user['password'],
            },
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body['success'] is True
        assert body['message'] == 'Login successful.'
        data = body['data']
        assert data['access']
        assert data['refresh']
        assert data['user']['email'] == 'loginuser@example.com'

    def test_login_wrong_password_returns_400(self, api_client, registered_user):
        response = api_client.post(
            LOGIN_URL,
            {
                'email': registered_user['email'],
                'password': 'WrongPass123!',
            },
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'non_field_errors' in response.json()

    def test_login_unknown_email_returns_400(self, api_client):
        response = api_client.post(
            LOGIN_URL,
            {
                'email': 'nobody@example.com',
                'password': VALID_PASSWORD,
            },
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'non_field_errors' in response.json()

    def test_login_inactive_user_returns_400(self, api_client, registered_user):
        User.objects.filter(email=registered_user['email']).update(is_active=False)

        response = api_client.post(
            LOGIN_URL,
            {
                'email': registered_user['email'],
                'password': registered_user['password'],
            },
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'non_field_errors' in response.json()

    def test_login_missing_password_returns_400(self, api_client):
        response = api_client.post(
            LOGIN_URL,
            {'email': 'loginuser@example.com'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.json()


# ---------------------------------------------------------------------------
# Shared helpers for authenticated test classes
# ---------------------------------------------------------------------------

def _password_change_payload(**overrides):
    payload = {
        'old_password': VALID_PASSWORD,
        'new_password': VALID_NEW_PASSWORD,
        'confirm_password': VALID_NEW_PASSWORD,
    }
    payload.update(overrides)
    return payload


def _obtain_tokens(api_client, email):
    """Register *email* and return the JWT payload dict (access, refresh, user)."""
    payload = _register_payload(email=email)
    api_client.post(REGISTER_URL, payload, format='json')
    resp = api_client.post(
        LOGIN_URL,
        {'email': email, 'password': VALID_PASSWORD},
        format='json',
    )
    return resp.json()['data']


# ---------------------------------------------------------------------------
# Logout API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLogoutAPI:
    @pytest.fixture
    def user_with_tokens(self, api_client):
        tokens = _obtain_tokens(api_client, 'logoutuser@example.com')
        user = User.objects.get(email='logoutuser@example.com')
        return {'user': user, 'refresh': tokens['refresh']}

    def test_logout_success_returns_200_and_envelope(self, api_client, user_with_tokens):
        api_client.force_authenticate(user=user_with_tokens['user'])
        response = api_client.post(
            LOGOUT_URL,
            {'refresh': user_with_tokens['refresh']},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body['success'] is True
        assert body['message'] == 'Logged out successfully.'
        assert body['data'] == {}

    def test_logout_invalid_token_still_returns_200(self, api_client, user_with_tokens):
        """Service swallows TokenError for invalid tokens — logout is idempotent."""
        api_client.force_authenticate(user=user_with_tokens['user'])
        response = api_client.post(
            LOGOUT_URL,
            {'refresh': 'not.a.valid.token'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True

    def test_logout_already_blacklisted_token_returns_200(self, api_client, user_with_tokens):
        """Calling logout twice with the same token must remain idempotent."""
        api_client.force_authenticate(user=user_with_tokens['user'])
        refresh = user_with_tokens['refresh']
        api_client.post(LOGOUT_URL, {'refresh': refresh}, format='json')

        response = api_client.post(LOGOUT_URL, {'refresh': refresh}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['success'] is True

    def test_logout_missing_refresh_returns_400(self, api_client, user_with_tokens):
        api_client.force_authenticate(user=user_with_tokens['user'])
        response = api_client.post(LOGOUT_URL, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'refresh' in response.json()

    def test_logout_unauthenticated_returns_401(self, api_client, user_with_tokens):
        response = api_client.post(
            LOGOUT_URL,
            {'refresh': user_with_tokens['refresh']},
            format='json',
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Token Refresh API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTokenRefreshAPI:
    @pytest.fixture
    def refresh_token(self, api_client):
        return _obtain_tokens(api_client, 'refreshuser@example.com')['refresh']

    def test_refresh_success_returns_200_and_envelope(self, api_client, refresh_token):
        response = api_client.post(REFRESH_URL, {'refresh': refresh_token}, format='json')

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body['success'] is True
        assert body['message'] == 'Token refreshed successfully.'
        # ROTATE_REFRESH_TOKENS=True → both access and refresh are returned
        assert 'access' in body['data']
        assert 'refresh' in body['data']

    def test_refresh_requires_no_authentication_header(self, api_client, refresh_token):
        """TokenRefreshView is AllowAny; no Authorization header must be needed."""
        # api_client has no credentials set — request must still succeed
        response = api_client.post(REFRESH_URL, {'refresh': refresh_token}, format='json')

        assert response.status_code == status.HTTP_200_OK

    def test_refresh_invalid_token_returns_401(self, api_client):
        response = api_client.post(
            REFRESH_URL,
            {'refresh': 'completely.invalid.token'},
            format='json',
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_missing_refresh_field_returns_400(self, api_client):
        response = api_client.post(REFRESH_URL, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_used_token_returns_401(self, api_client, refresh_token):
        """ROTATE_REFRESH_TOKENS=True blacklists a token after one use."""
        api_client.post(REFRESH_URL, {'refresh': refresh_token}, format='json')

        response = api_client.post(REFRESH_URL, {'refresh': refresh_token}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Profile / Me API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserMeAPI:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            email='meuser@example.com',
            password=VALID_PASSWORD,
            first_name='Jane',
            last_name='Doe',
        )

    def test_get_me_success_returns_200_and_user_fields(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get(ME_URL)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body['success'] is True
        data = body['data']
        assert data['email'] == 'meuser@example.com'
        assert data['first_name'] == 'Jane'
        assert data['last_name'] == 'Doe'
        assert data['is_active'] is True
        for field in ('id', 'role', 'created_at', 'updated_at'):
            assert field in data

    def test_get_me_unauthenticated_returns_401(self, api_client):
        response = api_client.get(ME_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_me_updates_name_fields(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.patch(
            ME_URL,
            {'first_name': 'Janet', 'last_name': 'Smith'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body['success'] is True
        assert body['message'] == 'Profile updated successfully.'
        assert body['data']['first_name'] == 'Janet'
        assert body['data']['last_name'] == 'Smith'

    def test_patch_me_partial_update_preserves_other_fields(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.patch(ME_URL, {'first_name': 'Partial'}, format='json')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()['data']
        assert data['first_name'] == 'Partial'
        assert data['last_name'] == 'Doe'

    def test_patch_me_readonly_email_is_silently_ignored(self, api_client, user):
        """Read-only fields sent in PATCH must be ignored, not rejected."""
        api_client.force_authenticate(user=user)
        response = api_client.patch(
            ME_URL,
            {'email': 'hacked@example.com'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()['data']['email'] == 'meuser@example.com'

    def test_patch_me_unauthenticated_returns_401(self, api_client):
        response = api_client.patch(ME_URL, {'first_name': 'X'}, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Password Change API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPasswordChangeAPI:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            email='pwduser@example.com',
            password=VALID_PASSWORD,
        )

    def test_password_change_success_returns_200_and_envelope(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            PASSWORD_CHANGE_URL,
            _password_change_payload(),
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body['success'] is True
        assert body['message'] == 'Password changed successfully.'
        assert body['data'] == {}

    def test_password_change_updates_hash_in_db(self, api_client, user):
        api_client.force_authenticate(user=user)
        api_client.post(PASSWORD_CHANGE_URL, _password_change_payload(), format='json')

        user.refresh_from_db()
        assert user.check_password(VALID_NEW_PASSWORD)
        assert not user.check_password(VALID_PASSWORD)

    def test_password_change_wrong_old_password_returns_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            PASSWORD_CHANGE_URL,
            _password_change_payload(old_password='WrongOld999!'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'old_password' in response.json()

    def test_password_change_new_same_as_old_returns_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            PASSWORD_CHANGE_URL,
            _password_change_payload(
                new_password=VALID_PASSWORD,
                confirm_password=VALID_PASSWORD,
            ),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password' in response.json()

    def test_password_change_confirm_mismatch_returns_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            PASSWORD_CHANGE_URL,
            _password_change_payload(confirm_password='Mismatched999@'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'confirm_password' in response.json()

    def test_password_change_weak_new_password_returns_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            PASSWORD_CHANGE_URL,
            _password_change_payload(new_password='123', confirm_password='123'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_change_missing_fields_returns_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(PASSWORD_CHANGE_URL, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_change_unauthenticated_returns_401(self, api_client):
        response = api_client.post(
            PASSWORD_CHANGE_URL,
            _password_change_payload(),
            format='json',
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
