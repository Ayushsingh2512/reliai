import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import typing
from fastapi import FastAPI, HTTPException

USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://user-service:8000")
ORDER_SERVICE_URL = os.environ.get("ORDER_SERVICE_URL", "http://order-service:8000")

http_client = httpx.AsyncClient(timeout=3.0)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await http_client.aclose()

app = FastAPI(title="Demo API Gateway", lifespan=lifespan)

@app.get("/health")
async def health() -> dict[str, typing.Any]:
    return {"status": "ok", "service": "api-gateway"}

@app.get("/api/users/{user_id}")
async def get_user(user_id: str) -> dict[str, typing.Any]:
    try:
        response = await http_client.get(f"{USER_SERVICE_URL}/users/{user_id}")
        response.raise_for_status()
        return typing.cast(dict[str, typing.Any], response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="User Service unavailable")

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str) -> dict[str, typing.Any]:
    try:
        response = await http_client.get(f"{ORDER_SERVICE_URL}/orders/{order_id}")
        response.raise_for_status()
        return typing.cast(dict[str, typing.Any], response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Order Service unavailable")
