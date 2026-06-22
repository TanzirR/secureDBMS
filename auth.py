"""
1. register_user()  → hash password + generate crypto material + store in DB
2. login_user()     → verify password + recover DEK + issue JWT
3. verify_token()   → validate JWT + extract user_id, username, DEK
"""

import uuid
import base64
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from cryptography.exceptions import InvalidTag

from encryption import generate_kek_salt, derive_kek, generate_dek, wrap_dek, unwrap_dek
from model import User

# JWT config
JWT_SECRET = "change-this-to-a-long-random-secret-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 1
LOGIN_FAILURE_LIMIT = 3
LOGIN_COOLDOWN = timedelta(minutes=2)

# Argon2id hasher
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
)


class LoginCooldownError(ValueError):
    def __init__(self, message: str, retry_after_seconds: int):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def register_user(username: str, password: str, db: Session) -> dict:
    # step 1 — check if username already exists
    if db.query(User).filter(User.username == username).first():
        raise ValueError(f"Username '{username}' already taken.")

    # step 2 — hash password with Argon2id
    password_hash = ph.hash(password)

    # step 3 — generate crypto material
    kek_salt    = generate_kek_salt()
    kek         = derive_kek(password, kek_salt)
    dek         = generate_dek()
    wrapped_dek = wrap_dek(dek, kek)

    # step 4 — store user in DB
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=password_hash,
        kek_salt=kek_salt,
        wrapped_dek=wrapped_dek,
        failed_login_attempts=0,
        failed_login=0,
        lockout_until=None,
    )
    db.add(user)
    db.commit()

    return {"message": f"User '{username}' registered successfully."}


def login_user(username: str, password: str, db: Session) -> dict:
    # step 1 — fetch user from DB
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise ValueError("Invalid username or password.")

    now = datetime.utcnow()
    if user.lockout_until is not None:
        if user.lockout_until > now:
            remaining_seconds = max(1, int((user.lockout_until - now).total_seconds()))
            raise LoginCooldownError(
                "Too many failed login attempts. Please wait 2 minutes before trying again.",
                remaining_seconds,
            )

        user.failed_login_attempts = 0
        user.failed_login = 0
        user.lockout_until = None
        db.commit()

    # step 2 — verify password against Argon2id hash
    try:
        ph.verify(user.password_hash, password)
    except VerifyMismatchError:
        user.failed_login_attempts += 1
        user.failed_login += 1
        if user.failed_login_attempts >= LOGIN_FAILURE_LIMIT:
            user.failed_login_attempts = 0
            user.failed_login = 0
            user.lockout_until = now + LOGIN_COOLDOWN
            db.commit()
            raise LoginCooldownError(
                "Too many failed login attempts. Please wait 2 minutes before trying again.",
                int(LOGIN_COOLDOWN.total_seconds()),
            )

        db.commit()
        raise ValueError("Invalid username or password.")

    # step 3 — re-derive KEK and unwrap DEK
    kek = derive_kek(password, user.kek_salt)
    dek = unwrap_dek(user.wrapped_dek, kek)

    user.failed_login_attempts = 0
    user.failed_login = 0
    user.lockout_until = None
    db.commit()

    # step 4 — issue JWT with DEK embedded
    payload = {
        "sub": user.id,
        "username": user.username,
        "dek": base64.b64encode(dek).decode("utf-8"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"access_token": token}


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        dek = base64.b64decode(payload["dek"])
        return {
            "user_id": payload["sub"],
            "username": payload["username"],
            "dek": dek,
        }
    except JWTError as e:
        raise ValueError(f"Invalid or expired token: {e}")


