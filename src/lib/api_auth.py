from datetime import datetime as dt
from datetime import timedelta, timezone

import jwt
from pwdlib import PasswordHash

JWT_SECRET_KEY = "b49a6058f507e214c0e3c44166280ad5856199c19c03b8dee475a83d2f9fd1d7"
JWT_ALGORITHSM = "HS256"
JWT_EXPIRY = 30

password_hash = PasswordHash.recommended()


def hashMyPassword(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verifyPassword(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def generateToken(user_id: str, email: str | None, expired_delta: timedelta | None = None):
    now = dt.now(timezone.utc)
    expire_at = now + (
        expired_delta if expired_delta is not None else timedelta(minutes=JWT_EXPIRY)
    )

    # build jwt payload
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire_at,
        "type": "access",
        "email": email,
    }

    return jwt.encode(payload=payload, key=JWT_SECRET_KEY, algorithm=JWT_ALGORITHSM)
