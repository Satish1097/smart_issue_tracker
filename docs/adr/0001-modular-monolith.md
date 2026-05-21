# ADR-0001: Modular monolith as the deployment unit

## Status

Accepted

## Context

Smart Issue Tracker is a backend-only Django API. We need a structure that supports learning, fast iteration, and a credible path to production without operating many services on day one.

## Decision

Deploy **one Django application** (modular monolith). Domain areas (`users`, `projects`, `issues`, etc.) are separate **apps** inside the same codebase and process. Long-running work (e.g. AI summaries) runs in **Celery workers**, not in separate HTTP microservices for MVP.

## Alternatives considered

- **Microservices** — separate auth, issues, and AI services with network boundaries.
- **Single “god” app** — all models and views in one Django app with no module boundaries.
- **Serverless per endpoint** — functions for each API operation.

## Consequences

- One Dockerfile, one migration stream, one place to debug request flows.
- Scaling starts with more web workers and Celery workers, not more repos.
- Team discipline is required: apps must not become tightly coupled; use clear imports and FK direction.
- Extracting a service later is possible but should be driven by measured pain, not upfront guesswork.

## Tradeoffs

| Gain | Cost |
|------|------|
| Simpler deploy, test, and onboarding | Cannot scale one domain independently without later split |
| Shared DB transactions where needed | Blast radius of bugs spans the monolith |
| Matches team size and MVP scope | Risk of sloppy boundaries if apps ignore separation rules |

**Learning takeaway:** A monolith is not “no architecture”—boundaries live in **packages and apps**, not in HTTP hops.
