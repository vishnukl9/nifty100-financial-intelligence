from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_get_companies():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "company_name" in data[0]

def test_get_company_profile():
    response = client.get("/api/v1/companies/RELIANCE")
    assert response.status_code == 200
    data = response.json()
    assert "company" in data
    assert data["company"]["id"] == "RELIANCE"
    assert "sector" in data
    assert "latest_kpis" in data

def test_get_company_not_found():
    response = client.get("/api/v1/companies/INVALID_TICKER")
    assert response.status_code == 404
