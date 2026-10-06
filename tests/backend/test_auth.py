import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.models.user import User

# --- REGISTRATION TESTS ---

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    email = f"test_{uuid.uuid4()}@example.com"
    password = "MySecurePassword123!"
    
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert "password" not in data
    assert "password_hash" not in data
    assert "id" in data
    
    # Check DB
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    
    # password is stored as hash
    assert user.password_hash != password
    assert len(user.password_hash) > 20

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    email = f"dup_{uuid.uuid4()}@example.com"
    password = "Password123"
    
    # Create first
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    
    # Try second
    response2 = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_register_invalid_input(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "bad", "password": "123"} # too short
    )
    assert response.status_code == 422 # FastAPI validation error

# --- LOGIN TESTS ---

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    email = f"login_{uuid.uuid4()}@example.com"
    password = "MySecurePassword123!"
    
    # Seed user
    user = User(email=email, password_hash=hash_password(password), role="user")
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Decode token to verify
    payload = jwt.decode(data["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == str(user.id)

@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session: AsyncSession):
    email = f"login_{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("correct"), role="user")
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "pw"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession):
    email = f"login_{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("pw"), role="user", is_active=False)
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "pw"}
    )
    assert response.status_code == 403
    assert "Inactive user" in response.json()["detail"]

# --- AUTHENTICATION & ME TESTS ---

@pytest.mark.asyncio
async def test_me_success(client: AsyncClient, db_session: AsyncSession):
    email = f"me_{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("pw"), role="user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    token = create_access_token(user_id=str(user.id))
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["id"] == str(user.id)
    assert "password_hash" not in data

@pytest.mark.asyncio
async def test_me_missing_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_me_malformed_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.token"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_me_invalid_signature(client: AsyncClient, db_session: AsyncSession):
    email = f"me_{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("pw"), role="user")
    db_session.add(user)
    await db_session.commit()
    
    payload = {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    bad_token = jwt.encode(payload, "wrong_secret_do_not_use_in_production_key", algorithm=settings.jwt_algorithm)
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_me_expired_token(client: AsyncClient, db_session: AsyncSession):
    email = f"me_{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("pw"), role="user")
    db_session.add(user)
    await db_session.commit()
    
    token = create_access_token(user_id=str(user.id), expires_delta=timedelta(minutes=-1))
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_me_missing_subject(client: AsyncClient):
    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_me_nonexistent_user(client: AsyncClient):
    token = create_access_token(user_id=str(uuid.uuid4()))
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_me_inactive_user(client: AsyncClient, db_session: AsyncSession):
    email = f"me_{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("pw"), role="user", is_active=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    token = create_access_token(user_id=str(user.id))
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

# --- FULL FLOW TEST ---

@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient):
    email = f"flow_{uuid.uuid4()}@example.com"
    password = "MySecurePassword123!"
    
    # 1. Register
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    assert reg_response.status_code == 201
    
    # 2. Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 3. Me
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email
