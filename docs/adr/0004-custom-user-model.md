# ADR-0004: Email-based custom User model

## Status

Accepted

## Context

Django’s default `User` uses `username` as the login identifier. The product requires **email-only** authentication and a lean identity model in `apps.users`. No `users` app migrations have been run yet—this is the last safe moment to choose the user model.

## Decision

- Define a custom **`User`** model in `apps.users` before the first `makemigrations users`.
- Set `USERNAME_FIELD = 'email'` with **unique** email.
- Implement **`UserManager`** in `managers.py` (`create_user`, `create_superuser`).
- Set `AUTH_USER_MODEL = 'users.User'` in settings **before** running migrations.
- Reference users elsewhere only via `settings.AUTH_USER_MODEL` (string), never direct imports of the concrete model in other apps’ models.

Optional `UserProfile` (avatar, timezone) stays separate later so `User` stays small.

## Alternatives considered

- **Default `User` + `Profile` with email** — still tied to username; awkward for email login.
- **Email field on default User** — fighting Django’s assumptions; not recommended.
- **Third-party user packages** — extra dependency and learning curve for little gain in MVP.

## Consequences

- First migration for `users` creates the canonical user table; changing model shape later requires painful migrations or resets.
- JWT login serializers must authenticate with **email**, not username.
- Django admin and `createsuperuser` use email prompts.
- All project/issue FKs use `settings.AUTH_USER_MODEL`.

## Tradeoffs

| Gain | Cost |
|------|------|
| Correct identity model for the product | Must be decided before any `users` migration |
| Clear JWT and API contract (email) | Slightly more setup than default User |
| Avoids dual identifiers (username + email) | Team must not reference `django.contrib.auth.models.User` in FKs |

**Learning takeaway:** Custom user is a **one-way door** in Django—do it early, migrate once, and never hard-code `auth.User` in other apps.
