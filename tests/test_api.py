from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_inventory_source_endpoint():
    response = client.get("/api/v1/source/inventory?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) <= 10


def test_pipeline_trigger_and_history():
    run_resp = client.post("/api/v1/pipeline/run", json={"run_type": "INCREMENTAL"})
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["status"] == "SUCCESS"

    hist_resp = client.get("/api/v1/pipeline/history?limit=5")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) > 0


def test_marts_endpoints():
    endpoints = [
        "/api/v1/marts/daily-sales",
        "/api/v1/marts/store-sales",
        "/api/v1/marts/product-sales",
        "/api/v1/marts/average-check",
        "/api/v1/marts/top-products",
        "/api/v1/marts/inventory-balance"
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
