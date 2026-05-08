"""Authentication: password hashing, JWT, Google ID token verification."""
import os
import jwt
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from tracker.db import query_one, insert_returning_id, execute

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_EXPIRY_DAYS = 30
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


class User(UserMixin):
    def __init__(self, row: dict):
        self.id = row["id"]
        self.email = row["email"]
        self.name = row.get("name") or row["email"].split("@")[0]
        self.avatar_url = row.get("avatar_url")
        self.google_id = row.get("google_id")
        self.created_at = row.get("created_at")

    def get_id(self):
        return str(self.id)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
        }


# ── User lookup ────────────────────────────────────────────────────────────────

def get_user_by_id(user_id):
    row = query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    return User(row) if row else None


def get_user_by_email(email):
    row = query_one("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    return row


def get_user_by_google_id(google_id):
    row = query_one("SELECT * FROM users WHERE google_id = ?", (google_id,))
    return row


# ── Signup / Login ─────────────────────────────────────────────────────────────

def create_user(email, password, name=None):
    email = email.lower().strip()
    pw_hash = generate_password_hash(password)
    return insert_returning_id(
        "INSERT INTO users (email, password_hash, name, created_at) VALUES (?,?,?,?)",
        (email, pw_hash, name or email.split("@")[0], datetime.now(timezone.utc).isoformat()),
    )


def create_google_user(email, google_id, name=None, avatar_url=None):
    email = email.lower().strip()
    return insert_returning_id(
        "INSERT INTO users (email, google_id, name, avatar_url, created_at) VALUES (?,?,?,?,?)",
        (email, google_id, name, avatar_url, datetime.now(timezone.utc).isoformat()),
    )


def verify_password(email, password):
    row = get_user_by_email(email)
    if not row or not row.get("password_hash"):
        return None
    if check_password_hash(row["password_hash"], password):
        execute("UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), row["id"]))
        return User(row)
    return None


# ── JWT (for mobile API) ───────────────────────────────────────────────────────

def make_jwt(user_id):
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


# ── Google ID token verification (for mobile + web) ────────────────────────────

def verify_google_token(id_token_str: str):
    """Verify a Google ID token. Returns dict with email/sub/name/picture, or None."""
    if not GOOGLE_CLIENT_ID:
        return None
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as g_requests
        info = id_token.verify_oauth2_token(id_token_str, g_requests.Request(), GOOGLE_CLIENT_ID)
        return {
            "google_id": info["sub"],
            "email": info["email"],
            "name": info.get("name"),
            "avatar_url": info.get("picture"),
        }
    except Exception:
        return None


def login_or_create_google_user(google_info):
    """Find or create user from verified Google info. Returns User."""
    existing = get_user_by_google_id(google_info["google_id"])
    if existing:
        execute("UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), existing["id"]))
        return User(existing)

    by_email = get_user_by_email(google_info["email"])
    if by_email:
        execute("UPDATE users SET google_id = ?, avatar_url = COALESCE(?, avatar_url), last_login = ? WHERE id = ?",
                (google_info["google_id"], google_info.get("avatar_url"),
                 datetime.now(timezone.utc).isoformat(), by_email["id"]))
        return User(get_user_by_email(google_info["email"]))

    user_id = create_google_user(
        google_info["email"], google_info["google_id"],
        google_info.get("name"), google_info.get("avatar_url"),
    )
    return get_user_by_id(user_id)
