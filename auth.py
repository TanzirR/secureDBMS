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

# Argon2id hasher
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=1,
)


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
    )
    db.add(user)
    db.commit()

    return {"message": f"User '{username}' registered successfully."}


def login_user(username: str, password: str, db: Session) -> dict:
    # step 1 — fetch user from DB
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise ValueError("Invalid username or password.")

    # step 2 — verify password against Argon2id hash
    try:
        ph.verify(user.password_hash, password)
    except VerifyMismatchError:
        raise ValueError("Invalid username or password.")

    # step 3 — re-derive KEK and unwrap DEK
    kek = derive_kek(password, user.kek_salt)
    dek = unwrap_dek(user.wrapped_dek, kek)

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


