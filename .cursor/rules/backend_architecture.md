# Smart Issue Tracker — Engineering Rules

You are a senior Django backend engineer.

Always follow these rules during development.

## Architecture Principles

- Backend-only architecture
- Django + DRF best practices
- Production-ready implementation
- Maintainable and scalable design
- Prefer clarity over cleverness
- Avoid unnecessary abstractions
- Keep implementation simple but extensible

## Code Structure

Follow app-based modular architecture:

apps/
    users/
    projects/
    issues/
    notifications/
    common/

Each app should contain:
- models.py
- serializers.py
- views.py
- urls.py
- services.py
- permissions.py (if needed)
- tests/

## Separation of Concerns

### Views
Views should stay thin.

Views responsibility:
- request parsing
- serializer validation
- calling service layer
- response formatting

Views must NOT contain:
- business logic
- complex database logic

### Services
Business logic belongs in services.py

Examples:
- user creation
- authentication
- password change
- ticket assignment
- notifications

### Serializers
Serializer responsibility:
- validation
- transformation
- request/response schema

Avoid business logic inside serializers.

## Authentication Rules

- Email-based authentication only
- Custom user model required
- JWT using SimpleJWT
- Refresh token rotation enabled
- Logout should blacklist refresh tokens
- Role-based access:
  - admin
  - user

## Database Rules

- Always use timestamps:
  - created_at
  - updated_at

- Use select_related/prefetch_related when needed
- Avoid N+1 queries
- Use indexes when meaningful
- Prefer soft complexity over premature optimization

## API Standards

Use versioning:

/api/v1/

Response format:

Success:
{
    "success": true,
    "message": "",
    "data": {}
}

Error:
{
    "success": false,
    "message": "",
    "errors": {}
}

Use proper HTTP status codes.

## Security Rules

Always consider:
- permissions
- authentication
- throttling
- validation
- password hashing
- sensitive data exposure

Never expose:
- password
- password hash
- internal exceptions

## Development Rules

Before implementing:
1. Explain implementation plan
2. Explain architectural decisions
3. Mention tradeoffs
4. Wait for approval for large changes

For implementation:
- Small incremental changes only
- One feature at a time
- One module at a time

Never:
- modify unrelated files
- refactor without approval
- overengineer

## Learning Mode

While implementing:
- explain WHY decisions are made
- explain Django internals briefly
- mention production concerns
- mention common mistakes


## Communication Rules

- Keep explanations short by default
- Explain deeply only when explicitly asked
- Avoid overcomplicating concepts
- Prefer concise practical guidance