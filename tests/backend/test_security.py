import pytest
import bcrypt

from app.core.security import hash_password, verify_password

def test_hash_password_returns_different_string():
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0
    assert hashed.startswith("$2")

def test_hash_password_independent_salting():
    password = "MySecurePassword123!"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    assert hash1 != hash2

def test_verify_password_success():
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True

def test_verify_password_failure():
    password = "MySecurePassword123!"
    wrong_password = "WrongPassword123!"
    hashed = hash_password(password)
    
    assert verify_password(wrong_password, hashed) is False

def test_verify_password_malformed_hash():
    password = "MySecurePassword123!"
    malformed_hash = "not-a-valid-bcrypt-hash"
    
    assert verify_password(password, malformed_hash) is False

def test_hash_password_empty_input():
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")

def test_verify_password_empty_input():
    # Creating a valid hash for an empty string using bcrypt directly
    # to ensure our function catches the empty string condition.
    hashed_empty = bcrypt.hashpw(b"", bcrypt.gensalt()).decode("utf-8")
    assert verify_password("", hashed_empty) is False
