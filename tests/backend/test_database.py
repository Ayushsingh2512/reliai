import pytest
from sqlalchemy import text
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
