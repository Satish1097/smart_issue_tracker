# ADR-0005: JWT authentication via SimpleJWT

## Status

Accepted

## Context

Smart Issue Tracker is a **backend-only REST API** (see [ADR-0001](0001-modular-monolith.md)). Clients (web, mobile, scripts) call JSON endpoints; there is no server-rendered HTML or Django session cookies in scope.

Identity uses an **email-based custom `User`** ([ADR-0004](0004-custom-user-model.md)). Auth endpoints (register, login, refresh, logout, password change, `/me`) must work for any client that can send `Authorization` headers.

We need authentication that is **stateless on the server** for normal API requests: no session store lookup per request, no reliance on `django.contrib.sessions` for API auth.

## Decision

Use **JSON Web Tokens (JWT)** issued and validated by **`djangorestframework-simplejwt`** (SimpleJWT) with Django REST Framework.

| Choice | Detail |
|--------|--------|
| **Transport** | `Authorization: Bearer <access_token>` on protected routes |
| **Login identifier** | Email + password (aligned with `USERNAME_FIELD = 'email'`) |
| **Token pair** | Short-lived **access** token + longer-lived **refresh** token |
| **Session auth** | **Not used** for the API — no `SessionAuthentication` on DRF defaults |
| **Logout** | Refresh token **blacklist** (SimpleJWT blacklist app) so refresh cannot mint new access tokens after logout |
| **Where logic lives** | Thin views + serializers; credential checks and user creation in `apps.users` services ([ADR-0003](0003-thin-views-service-layer.md)) |

### Why JWT over session auth

| Session (cookie) | JWT (Bearer) |
|------------------|--------------|
| Server stores session; each request hits session backend | Server verifies signature; no session row for routine requests |
| Cookie + CSRF story for browser SPAs | Header-based; fits mobile, CLI, and multi-origin API clients |
| Tied to Django’s session middleware | Fits a **pure API** contract: credentials in, tokens out |

Sessions are a strong default for same-site Django apps with templates. This project is API-first; clients hold tokens and send them explicitly.

### Why SimpleJWT

- **DRF-native** — same stack as serializers and permissions; less glue than hand-rolling JWT in views.
- **Maintained, documented** — standard lifetimes, rotation hooks, blacklist integration.
- **Teachable** — maps cleanly to “login returns two strings, middleware validates one string.”
- **Production path** — signing keys, lifetimes, rotation, and blacklist are configurable without custom crypto.

Alternatives like rolling our own JWT encode/decode or using non-DRF libraries add security and maintenance cost with little benefit for MVP.

### Access vs refresh tokens

| Token | Purpose | Lifetime (default direction) | Sent when |
|-------|---------|------------------------------|-----------|
| **Access** | Proves identity for API calls; embedded user id (`user_id` claim) | Short (e.g. minutes) | Every protected request |
| **Refresh** | Obtains a new access token without re-entering password | Longer (e.g. days) | Only to `/auth/refresh/` (and stored client-side until logout) |

**Rule:** Access tokens are validated on every protected request; refresh tokens are used rarely and must never be treated as a substitute for access on arbitrary endpoints.

Optional **refresh rotation** (new refresh on each refresh call) plus blacklist on rotation reduces window if a refresh token leaks.

### Stateless authentication

- **Stateless for access:** Validating an access JWT does not require a DB read of session state (only signature, expiry, and claim checks). Horizontal scaling of web workers does not require sticky sessions.
- **Not fully stateless for refresh/logout:** Blacklisting refresh tokens (and optional rotation) uses the database — a deliberate trade for **revocation** without abandoning JWT for the hot path.

### Security implications (production-minded)

| Topic | Implication |
|-------|-------------|
| **HTTPS** | Tokens in headers still must travel over TLS in production; never log tokens. |
| **Storage (client)** | Out of scope for this ADR; clients must avoid localStorage when XSS is a concern; httpOnly cookies are a client architecture choice, not session auth on the server. |
| **Short access TTL** | Limits damage if an access token is stolen; refresh flow re-authenticates identity. |
| **Refresh protection** | Longer-lived; blacklist on logout; throttle login/refresh; consider rotation. |
| **Signing key** | `SECRET_KEY` (or dedicated JWT signing key) must be strong and secret; rotation requires a planned key rollover. |
| **No sensitive data in payload** | JWTs are signed, not encrypted — put only `user_id` (and standard claims), never passwords or PII blobs. |
| **Password checks** | Still use Django’s password hashers at login; JWT does not replace secure password storage. |
| **Inactive users** | `is_active=False` must reject login; access validation should align with user state where applicable. |
| **Throttling** | Apply DRF throttles on login, register, and refresh to slow credential stuffing. |

Implementation details (exact lifetimes, rotation flags, URL paths) belong in settings and the auth module plan—not in this ADR.

## Alternatives considered

- **Django session + `SessionAuthentication`** — simple for admin-style apps; poor fit for token-based mobile/SPA/CLI clients and adds session store coupling on every request.
- **API keys only** — fine for machine-to-machine; weak for interactive login and password flows.
- **OAuth2 / social login only** — out of MVP scope; can layer later without changing the email+password + JWT core.
- **Custom JWT implementation** — unnecessary crypto and bug surface; SimpleJWT is the maintained default for DRF.
- **Opaque tokens + DB lookup every request** — revocable and simple mentally, but not stateless; higher DB load at scale than signed access JWTs.

## Consequences

- DRF `DEFAULT_AUTHENTICATION_CLASSES` uses JWT authentication only (no session auth on API).
- `INSTALLED_APPS` includes SimpleJWT and the **token blacklist** app for logout semantics.
- Auth API returns access + refresh on login/register; clients manage storage and refresh timing.
- Protected views use `IsAuthenticated` and read `request.user` from the validated access token.
- Logout is “invalidate refresh” (blacklist), not “delete server session.”
- Ops must configure lifetimes, `SECRET_KEY`, HTTPS, and throttles per environment.

## Tradeoffs

| Gain | Cost |
|------|------|
| Stateless access validation; easy horizontal scaling | Cannot revoke a stolen **access** token until it expires (mitigate with short TTL) |
| Clear API contract for any HTTP client | Clients must implement refresh and secure storage |
| SimpleJWT + DRF ecosystem | Blacklist/rotation adds DB writes on refresh/logout |
| No session middleware on API hot path | JWT size slightly larger than opaque session id |
| Aligns with email login and modular monolith | Team must understand access vs refresh and not leak refresh tokens |

**Learning takeaway:** JWT auth separates **proving identity** (short access token, checked without session store) from **renewing identity** (refresh token, guarded and revocable). SimpleJWT implements that split for DRF; sessions remain the wrong tool for a backend-only, multi-client API.
