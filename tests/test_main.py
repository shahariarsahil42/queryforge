from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert "QueryForge" in response.text


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_setup_validation():
    response = client.post("/api/setup", json={"rows": 50})
    assert response.status_code == 422


def test_benchmark_requires_setup():
    response = client.post("/api/benchmark", json={"repetitions": 20})
    assert response.status_code == 400
