from datetime import datetime, timedelta, timezone
import uuid

import jwt
import pytest

from app.config import settings
from app.core.security import (
    TokenExpiredError,
    TokenValidationError,
    create_access_token,
    decode_access_token,
)


def test_create_access_token_valid():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    
    assert isinstance(token, str)
    assert len(token) > 0

    # Manually decode to check claims
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    
    assert "sub" in payload
    assert payload["sub"] == user_id
    assert "exp" in payload
    assert "iat" in payload
    
    # Check that expiration is in the future
    exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    assert exp_time > datetime.now(timezone.utc)

def test_decode_access_token_success():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    
    payload = decode_access_token(token)
    assert payload["sub"] == user_id

def test_invalid_signature_rejected():
    user_id = str(uuid.uuid4())
    # Sign with a different secret
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    token = jwt.encode(payload, "wrong_secret_do_not_use_in_production_key", algorithm=settings.jwt_algorithm)
    
    with pytest.raises(TokenValidationError):
        decode_access_token(token)

def test_expired_token_rejected():
    user_id = str(uuid.uuid4())
    # Create an expired token by setting delta to negative
    token = create_access_token(user_id, expires_delta=timedelta(minutes=-1))
    
    with pytest.raises(TokenExpiredError):
        decode_access_token(token)

def test_malformed_token_rejected():
    with pytest.raises(TokenValidationError):
        decode_access_token("not.a.valid.jwt")

def test_missing_sub_claim_rejected():
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    with pytest.raises(TokenValidationError):
        decode_access_token(token)

def test_empty_user_id_rejected():
    with pytest.raises(ValueError):
        create_access_token("")

def test_no_sensitive_data_in_token():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    payload = decode_access_token(token)
    
    # Ensure it only has the 3 required claims
    assert set(payload.keys()) == {"sub", "exp", "iat"}
    
    # Specifically ensure no password data is implicitly leaked
    assert "password" not in payload
    assert "password_hash" not in payload
