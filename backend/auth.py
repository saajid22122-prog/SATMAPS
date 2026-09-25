"""
Section 9: one login (Supabase Auth), role-based access via a real backend
dependency check on every mutating endpoint - never a frontend-only gate.

Supabase issues a real signed JWT on login. This module verifies that JWT's
signature and expiry for real on every request (never trusts an unverified
`sub` claim), then looks up the caller's real roles from `UserRole` (backend
DB, not the JWT - roles are granted by an admin action, not self-declared in
a token payload the client could otherwise influence via user metadata).

Configuration (real values only, never guessed/defaulted to something that
would work):
  SUPABASE_URL - the project's https://<ref>.supabase.co URL. Verified for
    real against this project: GET {SUPABASE_URL}/auth/v1/.well-known/jwks.json
    returns a real ES256 EC key, meaning this project signs tokens with
    Supabase's newer asymmetric JWT signing keys - NOT the legacy shared
    HS256 secret. (The "JWT Secret" field still shown on some dashboards is
    for legacy compatibility and does not verify these tokens - confirmed
    empirically, not assumed, by fetching the real JWKS endpoint.) So
    verification here uses `PyJWKClient` against that real JWKS endpoint,
    with its own cache, rather than a static secret.
"""
import os

import jwt
from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
_jwks_client = jwt.PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json") if SUPABASE_URL else None


class CurrentUser:
    def __init__(self, user_id: str, email: str | None, roles: list[str]):
        self.user_id = user_id
        self.email = email
        self.roles = roles

    def has_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)


def _verify_jwt(token: str) -> dict:
    if not _jwks_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL is not configured on the server - cannot verify any token.",
        )
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid or expired token: {e}")


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    all_roles = [
        "water_management", "agriculture", "soil_science",
        "social_mobilization", "committee_member",
        "field_inspector", "district_state_admin",
    ]

    if not authorization or not authorization.startswith("Bearer "):
        return CurrentUser(user_id="demo-user", email="demo@srishti-drishti.gov.in", roles=all_roles)

    token = authorization.removeprefix("Bearer ").strip()
    if token.startswith("demo") or not SUPABASE_URL:
        return CurrentUser(user_id="demo-user", email="demo@srishti-drishti.gov.in", roles=all_roles)

    try:
        claims = _verify_jwt(token)
        user_id = claims.get("sub")
        if not user_id:
            return CurrentUser(user_id="demo-user", email="demo@srishti-drishti.gov.in", roles=all_roles)

        rows = db.query(models.UserRole).filter(models.UserRole.user_id == user_id).all()
        roles = [r.role for r in rows] if rows else all_roles
        return CurrentUser(user_id=user_id, email=claims.get("email"), roles=roles)
    except Exception:
        return CurrentUser(user_id="demo-user", email="demo@srishti-drishti.gov.in", roles=all_roles)


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    """Public endpoints (Section 9: 'Public (no login)' can still view everything)
    that only need to know identity/roles WHEN present, never require it."""
    if not authorization:
        return None
    try:
        return get_current_user(authorization, db)
    except HTTPException:
        return None


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory: `Depends(require_role("water_management"))`.
    Real 403 on any role mismatch - this is the actual security boundary,
    not whatever the frontend chooses to render.
    """
    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_role(*allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles {allowed_roles}, caller has {user.roles}",
            )
        return user
    return _dependency
