import importlib.util
import os
import sys

from fastapi.testclient import TestClient


def load_app(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

user_service_main = load_app("user_service_main", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../demo-services/user-service/main.py")))
app = user_service_main.app

def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "user-service"}

def test_valid_user() -> None:
    with TestClient(app) as client:
        response = client.get("/users/1")
        assert response.status_code == 200
        assert response.json() == {"user_id": "1", "name": "Alice", "status": "active"}

def test_missing_user() -> None:
    with TestClient(app) as client:
        response = client.get("/users/999")
        assert response.status_code == 404
        assert response.json() == {"detail": "User not found"}
