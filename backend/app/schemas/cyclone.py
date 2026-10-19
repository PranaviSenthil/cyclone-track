from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class TrajectoryPoint(BaseModel):
    time: str
    lat: float
    lon: float
    wind_kts: float
    pressure_hpa: float
    speed_kts: Optional[float] = 8.0
    bearing_deg: Optional[float] = 0.0
    landfall: Optional[int] = 0

class CycloneSummary(BaseModel):
    sid: str
    name: str
    season: int
    basin: str
    subbasin: str
    start_time: str
    end_time: str
    max_wind_kts: float
    min_pressure_hpa: float
    observation_count: int

class CycloneDetail(BaseModel):
    summary: CycloneSummary
    trajectory: List[TrajectoryPoint]
    is_active: bool = False
    status_label: str = "HISTORICAL_RECORD"

class ActiveCycloneResponse(BaseModel):
    active_cyclones: List[CycloneDetail]
    count: int
    data_source: str
    timestamp: str
    note: str
