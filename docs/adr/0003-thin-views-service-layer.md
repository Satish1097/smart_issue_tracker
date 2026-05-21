# ADR-0003: Thin views and a `services.py` layer

## Status

Accepted

## Context

DRF views and serializers are easy places to dump business logic. That makes endpoints hard to test and impossible to reuse from Celery tasks or management commands. The project already defines [`apps/users/services.py`](../../apps/users/services.py) as the home for user-domain operations.

## Decision

| Layer | Responsibility |
|-------|----------------|
| **Views** | Parse request, permissions, call serializer + service, return HTTP status/response |
| **Serializers** | Input validation, output shape, field-level errors — no business rules |
| **services.py** | Business logic: create user, change password, assign issue, enforce rules |
| **models.py** | Fields, constraints, simple model methods — not multi-step workflows |

Views stay thin; if a flow needs more than a few lines of orchestration, it belongs in a service.

## Alternatives considered

- **Fat views** — all logic in `APIView` / viewsets (fast to write, hard to maintain).
- **Fat serializers** — `create()` / `update()` hold domain rules (blurs validation vs behavior).
- **Separate `domain/` package** — heavier; defer unless services outgrow apps.

## Consequences

- Unit tests can target `UserService.register(...)` without `APIClient`.
- Celery tasks call the same services as HTTP endpoints (no duplicated logic).
- Slightly more files and indirection for trivial CRUD.
- Each app that has non-trivial behavior should have `services.py` (and `permissions.py` when needed).

## Tradeoffs

| Gain | Cost |
|------|------|
| Testability and reuse | Extra layer to navigate when learning Django |
| Consistent place for “what can happen” | Risk of over-abstracting one-liner operations |
| Clear review focus: views = HTTP, services = rules | Discipline required; easy to cheat under time pressure |

**Learning takeaway:** Serializers answer “is this input valid?” Services answer “what should the system do?” Views answer “what HTTP status do we return?”
