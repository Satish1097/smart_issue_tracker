"""
URL routes for the users app.

Mount under the API version prefix in the project urlconf, e.g.:

    path('api/v1/', include('apps.users.urls')),
"""

from django.urls import path

from apps.users.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    RegisterView,
    TokenRefreshView,
    UserMeView,
)

app_name = 'users'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/password/change/', PasswordChangeView.as_view(), name='auth-password-change'),
    path('users/me/', UserMeView.as_view(), name='users-me'),
]
