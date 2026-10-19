from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class SatelliteLayerInfo(BaseModel):
    id: str
    name: str
    satellite: str
    format: str
    tile_matrix_set: str
    max_zoom: int
    description: str

class DataSourceStatus(BaseModel):
    provider: str
    status: str # LIVE, HISTORICAL, CACHED, DEMO, UNAVAILABLE, CREDENTIALS_REQUIRED
    observation_timestamp: Optional[str] = None
    retrieval_timestamp: str
    freshness: str
    authenticated: bool
    details: str
    cached_items: Optional[int] = 0

class SatelliteAvailableResponse(BaseModel):
    layers: List[SatelliteLayerInfo]
    default_layer: str
    default_date: str
    wmts_base_url: str
    provider_status: List[DataSourceStatus]

class SatelliteTileTemplateRequest(BaseModel):
    layer_id: str
    date: str
