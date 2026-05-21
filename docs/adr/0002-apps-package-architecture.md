# ADR-0002: Domain apps under the `apps/` package

## Status

Accepted

## Context

The repo has a Django **project** package (`issue_tracker/`) for settings and routing, and **domain** code for users, projects, and issues. Mixing both at the repository root makes the tree noisy and blurs “config vs feature.” Step 1 introduced `apps/users/` and removed the legacy `account/` app.

## Decision

- All feature Django apps live under the **`apps/`** Python package (e.g. `apps.users`).
- **`issue_tracker/`** holds project config only: settings, root URLs, WSGI/ASGI, Celery app (later).
- Each app uses `AppConfig` with `name = 'apps.<app>'` and a short **`label`** (e.g. `users`) for migrations and `AUTH_USER_MODEL`.
- Repo root is on `sys.path` via [`issue_tracker/bootstrap.py`](../../issue_tracker/bootstrap.py), called from `manage.py`, WSGI, and ASGI.

Register apps explicitly, e.g. `'apps.users.apps.UsersConfig'` in `INSTALLED_APPS`.

## Alternatives considered

- **Flat apps at repo root** (`users/`, `projects/`) — common in tutorials, weaker grouping.
- **Keep `account`** — vague name; overlaps mentally with “user account” vs identity.
- **Rename `issue_tracker` project package now** — low value before deploy naming is fixed.

## Consequences

- Imports look like `from apps.users.services import UserService`.
- Future apps: `apps/projects`, `apps/issues`, `apps/common` (shared infra, not a business feature).
- `AUTH_USER_MODEL` will be `'users.User'` (label + model name), not `'apps.users.User'`.
- New developers look in `apps/` for product code and `issue_tracker/` for wiring.

## Tradeoffs

| Gain | Cost |
|------|------|
| Clear separation of config vs domain | Requires `bootstrap.py` / path setup in entrypoints |
| Room to grow many apps without root clutter | Slightly longer app paths (`apps.users` vs `users`) |
| Aligns with approved project plan | Team must use full app names in `INSTALLED_APPS` |

**Learning takeaway:** Django’s “project” is not your product module—**apps are**. The `apps/` folder makes that visible in the tree.
