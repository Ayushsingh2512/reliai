import importlib.util
import os
import sys
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import HTTPStatusError, Request, RequestError, Response


def load_app(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

api_gateway_main = load_app("api_gateway_main", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../demo-services/api-gateway/main.py")))
app = api_gateway_main.app

def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "api-gateway"}

def test_get_user_success() -> None:
    with patch("api_gateway_main.http_client.get", new_callable=AsyncMock) as mock_get:
        req = Request("GET", "http://user-service:8000/users/1")
        mock_get.return_value = Response(200, json={"user_id": "1", "name": "Alice"}, request=req)
        with TestClient(app) as client:
            response = client.get("/api/users/1")
            assert response.status_code == 200
            assert response.json() == {"user_id": "1", "name": "Alice"}

def test_get_user_not_found() -> None:
    with patch("api_gateway_main.http_client.get", new_callable=AsyncMock) as mock_get:
        req = Request("GET", "http://user-service:8000/users/999")
        resp = Response(404, text="User not found", request=req)
        mock_get.side_effect = HTTPStatusError("Error", request=req, response=resp)
        with TestClient(app) as client:
            response = client.get("/api/users/999")
            assert response.status_code == 404

def test_get_user_downstream_failure() -> None:
    with patch("api_gateway_main.http_client.get", new_callable=AsyncMock) as mock_get:
        req = Request("GET", "http://user-service:8000/users/1")
        mock_get.side_effect = RequestError("Connection failed", request=req)
        with TestClient(app) as client:
            response = client.get("/api/users/1")
            assert response.status_code == 503

def test_get_order_success() -> None:
    with patch("api_gateway_main.http_client.get", new_callable=AsyncMock) as mock_get:
        req = Request("GET", "http://order-service:8000/orders/A100")
        mock_get.return_value = Response(200, json={"order_id": "A100", "amount": 99.99}, request=req)
        with TestClient(app) as client:
            response = client.get("/api/orders/A100")
            assert response.status_code == 200
            assert response.json() == {"order_id": "A100", "amount": 99.99}
