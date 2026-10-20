from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DetectionRequest(BaseModel):
    sample_id: Optional[str] = None # e.g. "biparjoy_20230611_mature.jpg"
    bounds: Optional[Dict[str, float]] = None # min_lat, max_lat, min_lon, max_lon

class ClassificationRequest(BaseModel):
    sample_id: Optional[str] = None

class PredictionRequest(BaseModel):
    storm_id: Optional[str] = None
    trajectory_history: Optional[List[Dict[str, Any]]] = None
    sample_image_id: Optional[str] = None
    bounds: Optional[Dict[str, float]] = None
    current_wind_kts: Optional[float] = 65.0
    current_pressure_hpa: Optional[float] = 975.0

class TrackWaypoint(BaseModel):
    lead_time_hours: int
    lat: float
    lon: float
    method: str
    is_supported: bool = True

class ModelStatusResponse(BaseModel):
    models: List[Dict[str, Any]]
    device: str
    checkpoints_present: bool

class AlertDemoRequest(BaseModel):
    storm_name: str
    estimated_landfall_time: str
    landfall_district: str
    max_sustained_wind_kmh: float
    warning_level: str # RED_ALERT, ORANGE_ALERT, YELLOW_WATCH

class RiskAssessmentRequest(BaseModel):
    storm_id: Optional[str] = None
    forecast_waypoints: Optional[List[Dict[str, Any]]] = None
    current_wind_kts: Optional[float] = 65.0
    custom_lat: Optional[float] = None
    custom_lon: Optional[float] = None
    custom_location_name: Optional[str] = None

