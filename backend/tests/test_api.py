import os
import sys
import asyncio
import pytest
import httpx

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.main import app

def sync_request(method: str, path: str, json_data=None):
    async def _do():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            if method == "GET":
                return await client.get(path)
            elif method == "POST":
                return await client.post(path, json=json_data)
            else:
                raise ValueError(f"Unsupported method {method}")
    return asyncio.run(_do())

def test_health_endpoint():
    response = sync_request("GET", "/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "CYCLOTRACK" in data["service"]

def test_data_sources_status():
    response = sync_request("GET", "/api/data/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    providers = [d["provider"] for d in data]
    assert any("NASA GIBS" in p for p in providers)
    assert any("MOSDAC" in p for p in providers)
    assert any("IBTrACS" in p for p in providers)

def test_satellite_available_layers():
    response = sync_request("GET", "/api/satellite/available")
    assert response.status_code == 200
    data = response.json()
    assert "layers" in data
    assert len(data["layers"]) > 0
    assert "default_layer" in data
    assert "default_date" in data

def test_active_cyclones_empty_or_honest():
    response = sync_request("GET", "/api/cyclones/active")
    assert response.status_code == 200
    data = response.json()
    assert "active_cyclones" in data
    assert "historical_demo_available" in data
    assert data["note"] is not None

def test_historical_cyclones_list():
    response = sync_request("GET", "/api/cyclones/historical")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    names = [s["name"] for s in data]
    assert "BIPARJOY" in names
    assert "AMPHAN" in names
    assert "MOCHA" in names

def test_historical_cyclone_details():
    response = sync_request("GET", "/api/cyclones/BIPARJOY")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["name"] == "BIPARJOY"
    assert len(data["trajectory"]) > 10
    p0 = data["trajectory"][0]
    assert "lat" in p0
    assert "lon" in p0
    assert "wind_kts" in p0

def test_cyclone_not_found():
    response = sync_request("GET", "/api/cyclones/NON_EXISTENT_STORM_999")
    assert response.status_code == 404

def test_model_status():
    response = sync_request("GET", "/api/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) >= 4

def test_model_metrics():
    response = sync_request("GET", "/api/models/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "fusion_ablation_study" in data
    assert "configurations" in data["fusion_ablation_study"]

def test_demo_alert_dispatch():
    payload = {
        "storm_name": "Cyclone BIPARJOY",
        "estimated_landfall_time": "2023-06-15T12:00:00Z",
        "landfall_district": "Kutch District, Gujarat",
        "max_sustained_wind_kmh": 140.0,
        "warning_level": "RED_ALERT"
    }
    response = sync_request("POST", "/api/alerts/demo", json_data=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DEMONSTRATION_DISPATCHED"
    assert "RESEARCH & HACKATHON DEMO" in data["official_disclaimer"]
