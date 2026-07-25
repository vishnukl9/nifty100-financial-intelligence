from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db_row_counts" in data
    assert data["db_row_counts"]["companies"] > 0
    assert data["uptime_seconds"] >= 0
