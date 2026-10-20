"""
Modular Satellite Provider Protocol and Data Abstractions.
Enforces clean separation between:
1. Provider Configuration & Authentication
2. Metadata Discovery & Provenance
3. Authorized Product Retrieval
4. File Validation & Checksum Verification
5. Calibrated Preprocessing vs Visualization Tile Brokering
"""

import os
import hashlib
import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

class SatelliteMetadata(BaseModel):
    product_id: str
    satellite_name: str
    sensor_name: str
    observation_time: str
    spatial_bounds: Dict[str, float] = Field(
        ..., description="Dict with min_lat, max_lat, min_lon, max_lon"
    )
    channels: List[str]
    resolution_km: float
    format: str
    sha256: Optional[str] = None
    access_level: str = "RESTRICTED"
    provenance: str = "MOSDAC_SAC_ISRO"

class ProviderStatus(BaseModel):
    provider_name: str
    status: str  # OPERATIONAL, PARTIALLY_AVAILABLE, CREDENTIALS_REQUIRED, UNAVAILABLE
    authenticated: bool
    details: str
    retrieval_timestamp: str
    cached_products: int = 0
    endpoint_url: Optional[str] = None

class BaseSatelliteProvider(ABC):
    """
    Abstract Base Class for meteorological satellite data providers.
    """
    def __init__(self, provider_name: str, cache_dir: str):
        self.provider_name = provider_name
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    @abstractmethod
    def get_provider_status(self) -> Dict[str, Any]:
        """Returns honest operational and authentication status."""
        pass

    @abstractmethod
    def discover_metadata(
        self,
        start_time: str,
        end_time: str,
        bounds: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """Queries product metadata within time/spatial window."""
        pass

    @abstractmethod
    def retrieve_product(self, product_id: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves raw data product if authorized."""
        pass

    def compute_checksum(self, filepath: str) -> str:
        """Computes SHA-256 hash for raw file verification."""
        if not os.path.exists(filepath):
            return ""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()

    def validate_file(self, filepath: str, min_bytes: int = 1024) -> bool:
        """Validates that a downloaded file is non-empty and accessible."""
        if not os.path.exists(filepath):
            return False
        return os.path.getsize(filepath) >= min_bytes
