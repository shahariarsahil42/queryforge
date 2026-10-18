import json

import pytest
from fastapi.testclient import TestClient

from app import history
from app.main import app


@pytest.fixture
def test_history_db(tmp_path, monkeypatch):
    monkeypatch.setattr(
        history,
        "DB_PATH",
        tmp_path / "test_history.sqlite3",
    )


@pytest.fixture
def client(test_history_db):
    return TestClient(app)


@pytest.fixture
def saved_experiment(test_history_db):
    payload = {
        "rows_per_database": 5000,
        "results": [
            {
                "database": "postgresql",
                "indexed": True,
                "runs": 20,
                "p50_ms": 0.12,
                "p95_ms": 0.20,
                "mean_ms": 0.14,
                "min_ms": 0.10,
                "max_ms": 0.25,
                "sequential_queries_per_sec": 7000,
            }
        ],
    }

    return history.save_experiment(payload, 20)


def test_save_and_load_experiment(saved_experiment):
    result = history.get_experiment(saved_experiment)

    assert result["experiment_id"] == saved_experiment
    assert result["rows_per_database"] == 5000
    assert result["repetitions"] == 20


def test_history_list(saved_experiment):
    results = history.list_experiments()

    assert len(results) == 1
    assert results[0]["id"] == saved_experiment


def test_history_api(client, saved_experiment):
    response = client.get("/api/history")

    assert response.status_code == 200
    assert len(response.json()["experiments"]) == 1


def test_missing_experiment(client):
    response = client.get("/api/history/999")

    assert response.status_code == 404


def test_json_export(client, saved_experiment):
    response = client.get(
        f"/api/history/{saved_experiment}/export?format=json"
    )

    assert response.status_code == 200
    assert response.json()["rows_per_database"] == 5000


def test_csv_export(client, saved_experiment):
    response = client.get(
        f"/api/history/{saved_experiment}/export?format=csv"
    )

    assert response.status_code == 200
    assert "database" in response.text
    assert "postgresql" in response.text


def test_invalid_export_format(client, saved_experiment):
    response = client.get(
        f"/api/history/{saved_experiment}/export?format=xml"
    )

    assert response.status_code == 422