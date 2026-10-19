import os
import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, Dict, Any

from backend.app.schemas.cyclone import ActiveCycloneResponse
from backend.app.schemas.satellite import SatelliteAvailableResponse
from backend.app.schemas.prediction import DetectionRequest, ClassificationRequest, PredictionRequest, AlertDemoRequest
from backend.app.services.cyclone_service import cyclone_service
from backend.app.services.satellite_service import satellite_service
from backend.app.services.ml_service import ml_service
from backend.app.config import settings

api_router = APIRouter()

@api_router.get("/health")
def get_health():
    """Health check endpoint confirming API readiness and system status."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "environment": settings.ENVIRONMENT
    }

@api_router.get("/data/sources")
def get_data_sources():
    """Data-source transparency panel returning real status of satellite & historical providers."""
    return satellite_service.get_data_sources_status()

@api_router.get("/satellite/available", response_model=SatelliteAvailableResponse)
def get_available_satellite():
    """Returns available satellite layers (NASA GIBS WMTS, INSAT products, and verified benchmarks)."""
    return satellite_service.get_available_layers()

@api_router.get("/satellite/latest")
def get_latest_satellite():
    """Returns metadata for the most recently cataloged observation."""
    layers_data = satellite_service.get_available_layers()
    sample = layers_data.get("sample_benchmarks", [{}])[0] if layers_data.get("sample_benchmarks") else {}
    return {
        "provider": "NASA GIBS / Verified Satellites",
        "latest_observation_time": sample.get("observation_time", "2023-06-11T12:00:00Z"),
        "layer": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
        "tile_template": satellite_service.get_tile_template("VIIRS_SNPP_CorrectedReflectance_TrueColor", "2023-06-11"),
        "sample": sample
    }

@api_router.get("/cyclones/active")
def get_active_cyclones():
    """
    Returns active tropical cyclones in the North Indian Ocean basin.
    When none are active, truthfully reports 0 storms and links verified demonstration storm.
    """
    return cyclone_service.get_active_cyclones()

@api_router.get("/cyclones/historical")
def get_historical_cyclones():
    """Returns catalog of historical North Indian Ocean cyclones from verified IBTrACS records."""
    return cyclone_service.get_historical_cyclones()

@api_router.get("/cyclones/{storm_id}")
def get_cyclone_details(storm_id: str):
    """Returns full trajectory, central pressures, wind speeds, and translation metrics for a storm."""
    res = cyclone_service.get_cyclone_by_id(storm_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Cyclone '{storm_id}' not found in historical archive.")
    return res

@api_router.post("/detect")
def detect_cyclone(req: DetectionRequest):
    """
    Model A: Cyclone Detection & Center Localization Network.
    Returns detection probability, pixel center, and georeferenced coordinates if bounds provided.
    """
    return ml_service.detect_cyclone(sample_id=req.sample_id, bounds=req.bounds)

@api_router.post("/classify")
def classify_cyclone(req: ClassificationRequest):
    """
    Model B: Cyclone Structure and Intensity Stage Classifier.
    Returns class probabilities across 5 meteorological categories and entropy/OOD indicator.
    """
    return ml_service.classify_structure(sample_id=req.sample_id)

@api_router.post("/predict")
def predict_cyclone(req: PredictionRequest):
    """
    Multi-source track and intensity prediction engine:
    Runs Motion Baseline vs Deep GRU vs Multi-source Fusion, along with 80% and 95% uncertainty cones.
    """
    return ml_service.predict_future(
        storm_id=req.storm_id,
        trajectory_history=req.trajectory_history,
        sample_image_id=req.sample_image_id,
        bounds=req.bounds,
        current_wind_kts=req.current_wind_kts or 65.0,
        current_pressure_hpa=req.current_pressure_hpa or 975.0
    )

@api_router.get("/models/status")
def get_models_status():
    """Returns deployment status, architecture descriptions, and checkpoint integrity for all models."""
    return ml_service.get_models_status()

@api_router.get("/models/metrics")
def get_models_metrics():
    """Returns authentic benchmark evaluation metrics and ablation study results."""
    return ml_service.get_evaluation_metrics()

@api_router.post("/fusion/evaluate")
def evaluate_fusion_ablation():
    """Returns ablation comparison between baseline, track-only, satellite-only, and fused models."""
    return ml_service.fusion_service.run_benchmark_ablation()

@api_router.post("/alerts/demo")
def generate_demo_alert(req: AlertDemoRequest):
    """
    Demonstration early warning bulletin workflow.
    Explicitly marked as DEMONSTRATION WORKFLOW — not an official government bulletin.
    """
    return {
        "status": "DEMONSTRATION_DISPATCHED",
        "bulletin_id": f"CYCLOTRACK-DEMO-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "official_disclaimer": "RESEARCH & HACKATHON DEMO: Not an official IMD/RSMC meteorological bulletin. For operational warnings consult mausam.imd.gov.in.",
        "storm": req.storm_name,
        "warning_level": req.warning_level,
        "landfall_target": req.landfall_district,
        "estimated_impact_time": req.estimated_landfall_time,
        "projected_peak_wind_kmh": req.max_sustained_wind_kmh,
        "recommended_actions": [
            "Total suspension of fishing operations in deep sea and coastal sectors.",
            "Evacuation of residents in low-lying coastal surge zones.",
            "Pre-positioning of NDRF/SDRF disaster response teams.",
            "Securing telecommunications, power lines, and harbor craft."
        ],
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
