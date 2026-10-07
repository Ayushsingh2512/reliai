import os

import typing
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Demo User Service")

SERVICE_NAME = os.environ.get("SERVICE_NAME", "user-service")

# Deterministic mock data
MOCK_USERS = {
    "1": {"name": "Alice", "status": "active"},
    "2": {"name": "Bob", "status": "active"},
    "3": {"name": "Charlie", "status": "suspended"}
}

@app.get("/health")
async def health() -> dict[str, typing.Any]:
    return {"status": "ok", "service": SERVICE_NAME}

@app.get("/users/{user_id}")
async def get_user(user_id: str) -> dict[str, typing.Any]:
    user = MOCK_USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user_id,
        "name": user["name"],
        "status": user["status"]
    }
