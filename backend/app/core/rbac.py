"""
Role-based access control.

Roles
-----
- admin    — manages customers and users; can do anything an analyst can
- analyst  — runs recalculations, exports reports, manages alert settings
- viewer   — read-only access to dashboards and reports

Use the `require_role` dependency factory in route definitions:

    @router.post("/recalculate", dependencies=[Depends(require_role("analyst", "admin"))])
    def recalculate(...): ...

Tenant isolation is enforced separately via `get_current_user` + the SQLAlchemy
session — every tenant-scoped query MUST filter by `customer_id`.
"""
from enum import Enum
from typing import Iterable

from fastapi import Depends, HTTPException, status


class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


# Hierarchy: a higher role implies the lower ones for permission checks
_HIERARCHY = {
    Role.ADMIN: 3,
    Role.ANALYST: 2,
    Role.VIEWER: 1,
}


def role_satisfies(have: str, need: str) -> bool:
    """Return True if `have` is at least as privileged as `need`."""
    try:
        return _HIERARCHY[Role(have)] >= _HIERARCHY[Role(need)]
    except (KeyError, ValueError):
        return False


def require_role(*allowed: str):
    """
    FastAPI dependency factory. Allows the request only if the current user's
    role is in `allowed` OR satisfies one of them via hierarchy.
    """
    # Late import to avoid circular: deps imports rbac, this module is imported by routes
    from app.deps import get_current_user

    def _checker(current_user=Depends(get_current_user)):
        if any(role_satisfies(current_user.role, r) for r in allowed):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this action",
        )

    return _checker


def require_admin():
    return require_role(Role.ADMIN.value)


def require_analyst():
    return require_role(Role.ANALYST.value, Role.ADMIN.value)


def require_viewer():
    return require_role(Role.VIEWER.value, Role.ANALYST.value, Role.ADMIN.value)
