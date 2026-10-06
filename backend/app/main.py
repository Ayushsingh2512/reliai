from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

app = FastAPI(title="ReliAI API")

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}

@app.get("/health/db")
async def health_db_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:  # noqa: B008
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="Database connection failed")
