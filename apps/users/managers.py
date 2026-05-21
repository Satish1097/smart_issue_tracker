from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Create and query User instances; normalize email at the persistence boundary."""

    def create_user(self, email, password=None, **extra_fields):
        email = (email or '').strip()
        if not email:
            raise ValueError('The email address must be set.')

        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', self.model.Role.USER)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields['role'] = self.model.Role.ADMIN

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
