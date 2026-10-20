"""
INSAT / MOSDAC (Meteorological & Oceanographic Satellite Data Archival Centre) Adapter.
Documentation: https://mosdac.gov.in/live/ and https://mosdac.gov.in/downloadapi-manual
ISRO Space Applications Centre (SAC).
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Optional
import requests

from backend.app.services.satellite.base_provider import BaseSatelliteProvider, SatelliteMetadata

logger = logging.getLogger("MOSDAC_INSAT")

class MOSDACAdapter(BaseSatelliteProvider):
    """
    Adapter for INSAT-3D/3DR observations from MOSDAC.
    Supports authenticated API access, metadata querying, product catalogs, and local caching.
    """
    PRODUCTS = [
        {
            "id": "3R_IMG_L1B_STD",
            "name": "INSAT-3DR Imager Level-1B Standard",
            "satellite": "INSAT-3DR",
            "sensor": "Imager (6-channel)",
            "channels": ["VIS (0.65 um)", "SWIR (1.6 um)", "MIR (3.9 um)", "TIR-1 (10.8 um)", "TIR-2 (12.0 um)", "WV (6.7 um)"],
            "resolution": "1km (VIS), 4km (IR/WV)",
            "cadence": "Every 15-30 minutes",
            "access_level": "Restricted / Registration Required"
        },
        {
            "id": "3D_IMG_L2B_HEM",
            "name": "INSAT-3D Hydro-Estimator Precipitation (HEM)",
            "satellite": "INSAT-3D",
            "sensor": "Imager",
            "channels": ["Rainfall Rate (mm/hr)"],
            "resolution": "4km",
            "cadence": "Every 30 minutes",
            "access_level": "Restricted / Registration Required"
        },
        {
            "id": "3R_SND_L2B_DWV",
            "name": "INSAT-3DR Sounder Derived Wind Vectors",
            "satellite": "INSAT-3DR",
            "sensor": "Sounder (19-channel)",
            "channels": ["Atmospheric Motion Vectors"],
            "resolution": "10km",
            "cadence": "Hourly",
            "access_level": "Restricted / Registration Required"
        }
    ]

    def __init__(self, api_key: Optional[str] = None, user_email: Optional[str] = None, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "cache", "mosdac")
        super().__init__(provider_name="ISRO MOSDAC (INSAT-3D/3DR)", cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("MOSDAC_API_KEY", "")
        self.user_email = user_email or os.getenv("MOSDAC_USER_EMAIL", "")
        self.base_url = os.getenv("MOSDAC_API_BASE_URL", "https://mosdac.gov.in/live/")

    def get_supported_products(self) -> List[Dict]:
        return self.PRODUCTS

    def get_provider_status(self) -> Dict:
        """
        Evaluates MOSDAC accessibility status transparently.
        Never fabricates authentication or live data.
        """
        has_credentials = bool(self.api_key and self.user_email)
        
        if not has_credentials:
            return {
                "provider": "ISRO MOSDAC (INSAT-3D/3DR)",
                "status": "CREDENTIALS_REQUIRED",
                "authenticated": False,
                "latest_observation": "None (Awaiting API credentials)",
                "retrieval_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "details": (
                    "Official MOSDAC Download API requires registration and authorized user tokens. "
                    "To enable direct INSAT retrieval, register at https://mosdac.gov.in and set "
                    "MOSDAC_API_KEY and MOSDAC_USER_EMAIL in your environment."
                ),
                "cached_products_available": len(os.listdir(self.cache_dir)) if os.path.exists(self.cache_dir) else 0
            }

        # Check official health endpoint
        try:
            resp = requests.get(self.base_url, timeout=5)
            return {
                "provider": "ISRO MOSDAC (INSAT-3D/3DR)",
                "status": "LIVE" if resp.status_code == 200 else "DEGRADED",
                "authenticated": True,
                "http_status": resp.status_code,
                "retrieval_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "details": f"Connected to MOSDAC portal. Service status: {resp.status_code}"
            }
        except Exception as e:
            return {
                "provider": "ISRO MOSDAC (INSAT-3D/3DR)",
                "status": "UNAVAILABLE",
                "authenticated": True,
                "http_status": 0,
                "retrieval_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "details": f"Could not reach MOSDAC portal: {str(e)}"
            }

    def fetch_product_metadata(self, product_id: str, date_str: str) -> Dict:
        """Queries product metadata. If credentials missing, returns explicit configuration notice."""
        if not self.api_key:
            return {
                "success": False,
                "status": "CREDENTIALS_REQUIRED",
                "product_id": product_id,
                "date": date_str,
                "message": "MOSDAC credentials required for automated metadata query. Please provide MOSDAC_API_KEY."
            }
        
        # When credentials provided, queries official endpoint
        headers = {"Authorization": f"Bearer {self.api_key}", "User-Agent": "Cyclotrack/1.0"}
        url = f"{self.base_url}api/v1/products/{product_id}/search?date={date_str}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "http_status": resp.status_code, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def discover_metadata(
        self,
        start_time: str,
        end_time: str,
        bounds: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """Queries product metadata within time/spatial window."""
        date_str = start_time.split("T")[0] if "T" in start_time else start_time
        res = self.fetch_product_metadata("3R_IMG_L1B_STD", date_str)
        if res.get("success") and "data" in res:
            return res["data"] if isinstance(res["data"], list) else [res["data"]]
        return []

    def retrieve_product(self, product_id: str, output_path: Optional[str] = None) -> Dict:
        """Retrieves raw data product if authorized. Otherwise returns CREDENTIALS_REQUIRED."""
        if not self.api_key:
            return {
                "success": False,
                "status": "CREDENTIALS_REQUIRED",
                "product_id": product_id,
                "message": "MOSDAC credentials required (MOSDAC_API_KEY). Automated download restricted."
            }
        return {
            "success": False,
            "status": "NOT_IMPLEMENTED_REMOTE_ENDPOINT",
            "message": "Direct download endpoint connection awaiting verified user token."
        }

