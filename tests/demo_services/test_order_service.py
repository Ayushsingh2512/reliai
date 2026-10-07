import importlib.util
import os
import sys
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def load_app(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

order_service_main = load_app("order_service_main", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../demo-services/order-service/main.py")))
app = order_service_main.app

def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "order-service"}

def test_get_order_cached() -> None:
    with patch("order_service_main.redis_client.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = '{"order_id": "A100", "user_id": "1", "item": "Laptop", "amount": 999.99, "status": "shipped"}'
        with TestClient(app) as client:
            response = client.get("/orders/A100")
            assert response.status_code == 200
            assert response.json()["item"] == "Laptop"

def test_redis_failure() -> None:
    with patch("order_service_main.redis_client.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Redis down")
        with TestClient(app) as client:
            response = client.get("/orders/A100")
            assert response.status_code == 503
            assert response.json()["detail"] == "Redis connection failed"
