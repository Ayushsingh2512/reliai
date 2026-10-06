from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import pytest
import uuid
from app.database import engine, AsyncSessionLocal
from app.models.user import User

@pytest.mark.asyncio
async def test_database_connectivity():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        val = result.scalar()
        assert val is not None
        assert val == 1
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_model_and_migration():
    async with AsyncSessionLocal() as session:
        # Just query the users table to see if it exists (migration worked)
        result = await session.execute(text("SELECT count(id) FROM users"))
        count = result.scalar()
        assert count is not None
        assert count >= 0
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_creation_and_defaults():
    async with AsyncSessionLocal() as session:
        # Create user with required fields
        new_user = User(
            email=f"test_{uuid.uuid4()}@example.com",
            password_hash="hashed_pw",
            role="admin"
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        assert new_user.id is not None
        assert new_user.is_active is True  # default
        assert new_user.created_at is not None
        assert new_user.updated_at is not None
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_email_uniqueness():
    async with AsyncSessionLocal() as session:
        email = f"unique_{uuid.uuid4()}@example.com"
        user1 = User(email=email, password_hash="pw1", role="user")
        session.add(user1)
        await session.commit()
        
        user2 = User(email=email, password_hash="pw2", role="user")
        session.add(user2)
        with pytest.raises(IntegrityError):
            await session.commit()
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_required_fields():
    async with AsyncSessionLocal() as session:
        # Missing password_hash and role
        incomplete_user = User(email=f"fail_{uuid.uuid4()}@example.com")
        session.add(incomplete_user)
        with pytest.raises(IntegrityError):
            await session.commit()
    await engine.dispose()
