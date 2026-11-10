"""Local-first browser authentication using opaque, revocable PostgreSQL sessions."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import text
from .db import SessionLocal

router = APIRouter(prefix="/auth", tags=["auth"])
passwords = PasswordHash.recommended()
COOKIE = "atlas_session"
CSRF_COOKIE = "atlas_csrf"
SESSION_HOURS = 12

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)

def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def secure(request: Request) -> bool:
    return request.url.scheme == "https" or os.getenv("COOKIE_SECURE", "").lower() == "true"

def cookie_options(request: Request) -> dict:
    return {"secure": secure(request), "samesite": "lax", "path": "/"}

def set_session(response: Response, request: Request, user: dict) -> None:
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    with SessionLocal.begin() as db:
        db.execute(text("""INSERT INTO browser_sessions(token_hash, user_id, csrf_hash, expires_at)
                           VALUES (:token, :user, :csrf, :expires)"""),
                   {"token": digest(token), "user": user["id"], "csrf": digest(csrf), "expires": expires})
    response.set_cookie(COOKIE, token, httponly=True, max_age=SESSION_HOURS * 3600, **cookie_options(request))
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, max_age=SESSION_HOURS * 3600, **cookie_options(request))

def clear_session(response: Response, request: Request) -> None:
    response.delete_cookie(COOKIE, httponly=True, **cookie_options(request))
    response.delete_cookie(CSRF_COOKIE, httponly=False, **cookie_options(request))

def browser_identity(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with SessionLocal() as db:
        row = db.execute(text("""SELECT u.id, u.email, u.tenant_id, s.csrf_hash
            FROM browser_sessions s JOIN app_users u ON u.id = s.user_id
            WHERE s.token_hash = :token AND s.expires_at > now()"""),
            {"token": digest(token)}).mappings().first()
    if not row:
        return None
    return {"subject": str(row["id"]), "tenant": str(UUID(str(row["tenant_id"]))),
            "email": row["email"], "csrf_hash": row["csrf_hash"]}


def throttle(email: str, request: Request) -> None:
    # Never trust forwarded headers from arbitrary clients.
    remote = request.client.host if request.client else "unknown"
    key = digest(remote + "|" + email)
    with SessionLocal.begin() as db:
        row = db.execute(text("""
          INSERT INTO auth_attempts(identity_hash, attempts, window_start)
          VALUES (:key, 1, now())
          ON CONFLICT (identity_hash) DO UPDATE
          SET attempts = CASE WHEN auth_attempts.window_start < now() - interval '15 minutes'
                              THEN 1 ELSE auth_attempts.attempts + 1 END,
              window_start = CASE WHEN auth_attempts.window_start < now() - interval '15 minutes'
                                  THEN now() ELSE auth_attempts.window_start END
          RETURNING attempts
        """), {"key": key}).scalar_one()
    if row > 10:
        raise HTTPException(429, "Too many login attempts; retry later")

def validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    from urllib.parse import urlsplit
    parsed = urlsplit(origin)
    if (parsed.scheme, parsed.netloc) != (request.url.scheme, request.url.netloc):
        raise HTTPException(403, "Invalid request origin")

def require_csrf(request: Request, identity: dict) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    validate_origin(request)
    token = request.headers.get("x-csrf-token", "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not token or not cookie or not secrets.compare_digest(token, cookie) or not secrets.compare_digest(digest(token), identity["csrf_hash"]):
        raise HTTPException(403, "CSRF token required")

def limited_registration() -> str:
    # Registration must never be open to arbitrary users in this portfolio demo.
    return os.getenv("ATLAS_BOOTSTRAP_EMAIL", "").strip().lower()

@router.post("/register", status_code=201)
def register(body: Credentials, request: Request, response: Response):
    validate_origin(request)
    email = body.email.lower()
    throttle(email, request)
    if not limited_registration() or email != limited_registration():
        raise HTTPException(403, "Self-registration disabled")
    with SessionLocal.begin() as db:
        existing = db.execute(text("SELECT 1 FROM app_users LIMIT 1")).first()
        if existing:
            raise HTTPException(403, "Initial account already registered")
        tenant = db.execute(text("SELECT id FROM tenants ORDER BY id LIMIT 1")).scalar()
        if not tenant:
            raise HTTPException(503, "No tenant configured")
        user = db.execute(text("""INSERT INTO app_users(tenant_id,email,password_hash)
              VALUES (:tenant,:email,:password) RETURNING id, email, tenant_id"""),
              {"tenant": tenant, "email": email, "password": passwords.hash(body.password)}).mappings().one()
        identity = dict(user)
    set_session(response, request, identity)
    return {"email": identity["email"], "tenant": str(identity["tenant_id"])}

@router.post("/login")
def login(body: Credentials, request: Request, response: Response):
    validate_origin(request)
    throttle(body.email.lower(), request)
    # Same response for unknown account and incorrect password.
    with SessionLocal() as db:
        row = db.execute(text("SELECT id,email,tenant_id,password_hash FROM app_users WHERE email=:email"),
                         {"email": body.email.lower()}).mappings().first()
    if not row or not passwords.verify(body.password, row["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    set_session(response, request, dict(row))
    return {"email": row["email"], "tenant": str(row["tenant_id"])}

@router.get("/me")
def me(request: Request):
    identity = browser_identity(request)
    if not identity:
        raise HTTPException(401, "Not authenticated")
    return {"email": identity["email"], "tenant": identity["tenant"], "subject": identity["subject"]}

@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    identity = browser_identity(request)
    if identity:
        require_csrf(request, identity)
    token = request.cookies.get(COOKIE)
    if token:
        with SessionLocal.begin() as db:
            db.execute(text("DELETE FROM browser_sessions WHERE token_hash=:token"), {"token": digest(token)})
    clear_session(response, request)
