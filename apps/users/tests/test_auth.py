import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()

REGISTER_URL = reverse('users:auth-register')
LOGIN_URL = reverse('users:auth-login')

VALID_PASSWORD = 'TestPass123!'


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
