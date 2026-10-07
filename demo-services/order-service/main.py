import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import typing
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SERVICE_NAME = os.environ.get("SERVICE_NAME", "order-service")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://reliai:password@postgres:5432/reliai")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS demo_orders (
                id VARCHAR(50) PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                item VARCHAR(255) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(50) NOT NULL
            )
        """))
        
        result = await conn.execute(text("SELECT count(*) FROM demo_orders"))
        if result.scalar() == 0:
            await conn.execute(text("""
                INSERT INTO demo_orders (id, user_id, item, amount, status) VALUES
                ('A100', '1', 'Laptop', 999.99, 'shipped'),
                ('A101', '1', 'Mouse', 49.99, 'processing'),
                ('B200', '2', 'Keyboard', 89.99, 'delivered')
            """))

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        await init_db()
    except Exception as e:  # noqa: BLE001
        print(f"Failed to initialize database: {e}")
        
    yield
    
    await engine.dispose()
    await redis_client.aclose()

app = FastAPI(title="Demo Order Service", lifespan=lifespan)

@app.get("/health")
async def health() -> dict[str, typing.Any]:
    return {"status": "ok", "service": SERVICE_NAME}

@app.get("/health/dependencies")
async def health_dependencies() -> dict[str, typing.Any]:
    db_status = "ok"
    redis_status = "ok"
    
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_status = "error"
        
    try:
        await redis_client.ping()
    except Exception:  # noqa: BLE001
        redis_status = "error"
        
    return {
        "status": "ok" if (db_status == "ok" and redis_status == "ok") else "degraded",
        "database": db_status,
        "redis": redis_status
    }

@app.get("/orders/{order_id}")
async def get_order(order_id: str) -> dict[str, typing.Any]:
    try:
        cached_order = await redis_client.get(f"order:{order_id}")
        if cached_order:
            return typing.cast(dict[str, typing.Any], json.loads(cached_order))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Redis connection failed")
        
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT id, user_id, item, amount, status FROM demo_orders WHERE id = :order_id"),
                {"order_id": order_id}
            )
            row = result.mappings().fetchone()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order = {
        "order_id": row["id"],
        "user_id": row["user_id"],
        "item": row["item"],
        "amount": float(row["amount"]),
        "status": row["status"]
    }
    
    try:
        await redis_client.setex(f"order:{order_id}", 3600, json.dumps(order))
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Redis connection failed")
        
    return order
