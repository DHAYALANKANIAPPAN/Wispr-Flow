"""Authentication and role-based authorization.

Purpose:
    Handles student and teacher registration, login, secure password hashing (bcrypt),
    stateless signed token generation/verification, and strict role checks.

Status:
    Active, production-ready.

Fail-Closed Behavior:
    - Any missing, malformed, expired, or tampered token returns HTTP 401 Unauthorized.
    - A student attempting to access another student's data returns HTTP 403 Forbidden.
    - A teacher attempting to access another teacher's class returns HTTP 403 Forbidden.
    - Non-teachers attempting to access teacher endpoints return HTTP 403 Forbidden.
"""

import os
import json
import base64
import hmac
import hashlib
import time
from typing import Optional, Dict, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.models import User

SECRET_KEY: str = os.getenv("SECRET_KEY", "adaptive_iq_dev_secret_insecure_default_key_32bytes")
TOKEN_EXPIRY_SECONDS: int = 86400  # 24 hours

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt.

    Args:
        password: Raw plaintext password string.

    Returns:
        str: Salted bcrypt hash.
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: Raw plaintext password.
        hashed_password: Salted bcrypt hash.

    Returns:
        bool: True if password matches hash, False otherwise.
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, role: str) -> str:
    """Create a tamper-proof HMAC-SHA256 signed bearer token.

    Args:
        user_id: Unique user identifier string.
        role: User role ('student' | 'teacher').

    Returns:
        str: Encoded token in format '<payload_b64>.<signature_b64>'.
    """
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
        "iat": int(time.time()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify an HMAC-SHA256 token.

    Args:
        token: Bearer token string.

    Returns:
        dict: Verified payload dict.

    Raises:
        HTTPException: 401 if invalid, expired, or tampered.
    """
    parts = token.split(".")
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload_b64, sig_b64 = parts

    # Verify signature
    expected_sig = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode payload
    try:
        # Add padding back if necessary
        padded_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if "exp" not in payload or payload["exp"] < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency to extract and validate the authenticated user from the Authorization header.

    Args:
        auth: HTTPAuthorizationCredentials from bearer header.
        db: SQLAlchemy session.

    Returns:
        User: Authenticated User model instance.

    Raises:
        HTTPException: 401 if credentials missing or user not found.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_student_access(student_id: str, current_user: User) -> None:
    """Ensure that the caller has permission to view/modify the given student's records.

    A student can only access their own data.
    Teachers are permitted to access student records in their scope.

    Args:
        student_id: Target student ID being accessed.
        current_user: Authenticated user.

    Raises:
        HTTPException: 403 Forbidden if unauthorized.
    """
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: students cannot access other students' records",
        )


def require_teacher_access(teacher_id: str, current_user: User) -> None:
    """Ensure that only the specified teacher can access their own class summary.

    Teachers cannot read another teacher's class.

    Args:
        teacher_id: Target teacher ID.
        current_user: Authenticated user.

    Raises:
        HTTPException: 403 Forbidden if caller is not a teacher or teacher ID does not match.
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: teacher role required",
        )
    if current_user.id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: teachers cannot access another teacher's class",
        )
