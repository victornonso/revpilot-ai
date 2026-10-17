"""OIDC JWT verification and database-authoritative organisation membership."""

from contextvars import ContextVar
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient
from sqlalchemy import text

from .db import DEMO_ORG, engine, settings

tenant: ContextVar[UUID] = ContextVar("tenant", default=DEMO_ORG)
role: ContextVar[str] = ContextVar("role", default="demo_operator")


@lru_cache(maxsize=4)
def keys(issuer):
    import httpx

    response = httpx.get(
        issuer.rstrip("/") + "/.well-known/openid-configuration", timeout=10
    )
    response.raise_for_status()
    metadata = response.json()
    if metadata["issuer"].rstrip("/") != issuer.rstrip("/"):
        raise ValueError("OIDC issuer mismatch")
    if not metadata["jwks_uri"].startswith("https://"):
        raise ValueError("OIDC keys require HTTPS")
    return PyJWKClient(
        metadata["jwks_uri"], cache_jwk_set=True, lifespan=300, timeout=10
    )


def authenticate(request):
    if settings.public_demo_mode:
        access = request.cookies.get("revpilot_access", "")
        if access and settings.private_access_key:
            try:
                claims = jwt.decode(
                    access,
                    settings.session_secret,
                    algorithms=["HS256"],
                    audience="revpilot-owner",
                    options={"require": ["exp", "aud", "sub"]},
                )
                if claims["sub"] == "owner":
                    return DEMO_ORG, "demo_owner"
            except jwt.InvalidTokenError:
                pass
        return DEMO_ORG, "demo_viewer"
    header = request.headers.get("authorization", "")
    if not header:
        if settings.demo_mode:
            return DEMO_ORG, "demo_operator"
        raise HTTPException(401, "An authenticated OIDC session is required.")
    if not settings.oidc_issuer or not settings.oidc_audience:
        raise HTTPException(503, "OIDC issuer and audience are not configured.")
    try:
        token = header.removeprefix("Bearer ")
        signing_key = keys(settings.oidc_issuer).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        org = UUID(request.headers.get("x-organisation-id", ""))
        with engine.begin() as conn:
            conn.execute(
                text("SELECT set_config('app.org_id',:org,true)"), {"org": str(org)}
            )
            membership = conn.execute(
                text(
                    "SELECT payload->>'role' FROM identity.membership WHERE status='active' AND payload->>'subject'=:subject AND payload->>'issuer'=:issuer"
                ),
                {"subject": claims["sub"], "issuer": claims["iss"]},
            ).scalar()
        if not membership:
            raise ValueError("No membership")
        return org, membership
    except Exception as exc:
        raise HTTPException(
            401, "Token or organisation membership is invalid."
        ) from exc


def permitted(path, method):
    current = role.get()
    if settings.public_demo_mode:
        if path in ("/api/v1/access/unlock", "/api/v1/access/lock"):
            return True
        if path.startswith("/api/v1/investigations"):
            return current == "demo_owner"
        if method in ("GET", "HEAD", "OPTIONS"):
            return True
        return current == "demo_owner" and path in (
            "/api/v1/reports",
            "/api/v1/rules/simulate",
            "/api/v1/scenarios",
        )
    if method in ("GET", "HEAD", "OPTIONS"):
        return True
    if current in ("demo_operator", "owner", "administrator", "revenue_operations"):
        return True
    if "/approvals/" in path:
        return current in ("sales_manager", "finance_analyst")
    if path.startswith("/api/v1/proposals"):
        return current in ("sales_manager", "sales_representative")
    if path.startswith("/api/v1/reports"):
        return current in ("sales_manager", "finance_analyst", "executive")
    if path.startswith("/api/v1/investigations"):
        return current in ("sales_manager", "finance_analyst", "executive")
    return False
