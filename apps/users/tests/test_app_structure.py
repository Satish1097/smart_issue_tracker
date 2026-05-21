import pytest
from django.apps import apps


@pytest.mark.django_db
def test_users_app_is_installed():
    app_config = apps.get_app_config('users')
    assert app_config.name == 'apps.users'
    assert app_config.label == 'users'
