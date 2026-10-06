import bcrypt


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
