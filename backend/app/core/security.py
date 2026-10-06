from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError

from app.config import settings


class TokenError(Exception):
    """Base class for token-related errors."""

class TokenExpiredError(TokenError):
    """Raised when the token has expired."""

class TokenValidationError(TokenError):
    """Raised when the token is invalid or malformed."""
def hash_password(password: str) -> str:
    """
    Hashes a plaintext password securely using bcrypt.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    # bcrypt requires bytes
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash.
    """
    if not password:
        return False
        
    try:
        pwd_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except (ValueError, TypeError):
        # ValueError is raised by checkpw if the hash is malformed
        return False

def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """
    Creates a JWT access token for a given user.
    """
    if not user_id:
        raise ValueError("User ID cannot be empty")
        
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT access token.
    Returns the payload if valid.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        
        # Verify 'sub' exists
        if "sub" not in payload or not payload["sub"]:
            raise TokenValidationError("Token is missing 'sub' claim")
            
        return payload
        
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except (InvalidTokenError, PyJWTError):
        raise TokenValidationError("Token is invalid or malformed")
