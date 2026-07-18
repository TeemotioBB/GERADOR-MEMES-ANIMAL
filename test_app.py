from fastapi.testclient import TestClient

from main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_home_loads():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Cretino Factory" in response.text
