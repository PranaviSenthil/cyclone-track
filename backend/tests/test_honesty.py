import os
import sys
import asyncio
import pytest
import httpx
import numpy as np

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

def test_model_status_explicit_states_and_no_false_validation():
    """Verify that models use approved explicit states and untrained models are not marked VALIDATED."""
    response = sync_request("GET", "/api/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    
    approved_states = {"UNTRAINED", "TRAINED_NOT_VALIDATED", "VALIDATED_ON_HOLDOUT", "DEMO_ONLY", "ERROR", "UNAVAILABLE"}
    
    for m in data["models"]:
        assert m["status"] in approved_states, f"Model {m['id']} has unapproved status: {m['status']}"
        # Model A, B, D are not fully trained/validated; must not be marked VALIDATED
        if m["id"] in ["model_a_detector", "model_b_classifier", "model_d_intensity"]:
            assert m["status"] == "UNTRAINED"
        if m["id"] in ["model_e_uncertainty", "model_f_multimodal_fusion"]:
            assert m["status"] == "DEMO_ONLY"

def test_no_fabricated_metrics_in_evaluation_api():
    """Verify that fabricated benchmark literals (122.9 km, 7.1 kts, 0.887 F1) are absent from metrics responses."""
    response = sync_request("GET", "/api/models/metrics")
    assert response.status_code == 200
    raw_text = response.text
    
    assert "122.9" not in raw_text, "Found fabricated 122.9 km metric in /api/models/metrics"
    assert "0.887" not in raw_text, "Found fabricated 0.887 F1 score in /api/models/metrics"
    assert "32.6%" not in raw_text, "Found fabricated 32.6% improvement claim in /api/models/metrics"
    
    data = response.json()
    configs = data["fusion_ablation_study"]["configurations"]
    baseline_cfg = next(c for c in configs if "Baseline" in c["name"])
    gru_cfg = next(c for c in configs if "GRU" in c["name"])
    
    # Baseline was measured at 58.6 km at 24h on holdout; GRU was measured at 271.8 km
    assert baseline_cfg["track_error_24h_km"] == 58.6
    assert gru_cfg["track_error_24h_km"] == 271.8

def test_data_sources_status_honesty():
    """Verify that archival IBTrACS is marked HISTORICAL, not LIVE."""
    response = sync_request("GET", "/api/data/sources")
    assert response.status_code == 200
    data = response.json()
    
    ibtracs = next(d for d in data if "IBTrACS" in d["provider"])
    assert ibtracs["status"] == "HISTORICAL", f"Archival IBTrACS should be HISTORICAL, got: {ibtracs['status']}"
    
    # MOSDAC without key must be UNAVAILABLE
    mosdac = next(d for d in data if "MOSDAC" in d["provider"])
    if not os.getenv("MOSDAC_API_KEY"):
        assert mosdac["status"] == "UNAVAILABLE"
        assert mosdac["authenticated"] is False

def test_detector_blank_input_rejection():
    """Verify that uniform/blank images are rejected and cannot report a confirmed cyclone."""
    from ml.models.detector import CycloneDetectorService
    detector = CycloneDetectorService()
    
    # 1. Solid black image
    black_img = np.zeros((256, 256, 3), dtype=np.uint8)
    res_black = detector.predict_image(black_img)
    assert res_black["cyclone_detected"] is False
    assert res_black["detection_confidence"] == 0.0
    assert res_black["quality_flag"] == "REJECTED_BLANK_OR_UNIFORM_INPUT"
    
    # 2. Solid white image
    white_img = np.ones((256, 256, 3), dtype=np.uint8) * 255
    res_white = detector.predict_image(white_img)
    assert res_white["cyclone_detected"] is False
    assert res_white["detection_confidence"] == 0.0
    assert res_white["quality_flag"] == "REJECTED_BLANK_OR_UNIFORM_INPUT"

def test_intensity_predictor_persistence_and_untrained_status():
    """Verify that intensity predictor uses persistence baseline and reports UNTRAINED status."""
    from ml.models.intensity_predictor import IntensityPredictorService
    svc = IntensityPredictorService()
    res = svc.predict_intensity(current_wind_kts=80.0, current_pressure_hpa=960.0)
    
    assert res["model_status"] == "UNTRAINED"
    assert res["forecast_method"] == "PERSISTENCE_BASELINE"
    for f in res["forecasts"]:
        assert f["predicted_wind_kts"] == 80.0
        assert f["predicted_pressure_hpa"] == 960.0
        assert "Persistence Baseline" in f["method"]

def test_invalid_input_and_missing_storm_handling():
    """Verify graceful error handling for missing storms and invalid bounds."""
    # 1. Non-existent storm
    resp_404 = sync_request("GET", "/api/cyclones/UNKNOWN_CYCLONE_XYZ")
    assert resp_404.status_code == 404
    
    # 2. Prediction request with invalid bounds
    payload = {
        "storm_id": "BIPARJOY",
        "bounds": {"min_lat": 25.0, "max_lat": 10.0, "min_lon": 90.0, "max_lon": 80.0} # Inverted bounds
    }
    resp = sync_request("POST", "/api/predict", json_data=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "fused_track" in data
