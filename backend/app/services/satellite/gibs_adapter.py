"""
NASA GIBS (Global Imagery Browse Services) Provider Adapter.
Documentation: https://nasa-gibs.github.io/gibs-api-docs/
Provides high-resolution satellite imagery tiles across multiple instruments (MODIS, VIIRS, GPM).
"""

import os
import logging
import datetime
from typing import Dict, List, Optional
import requests

logger = logging.getLogger("NASA_GIBS")

class NASAGIBSAdapter:
    """
    Adapter for NASA GIBS WMTS and WMS imagery services.
    Enables true real-world satellite viewing for any cyclone observation date.
    """
    AVAILABLE_LAYERS = [
        {
            "id": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
            "name": "VIIRS SNPP True Color (Corrected Reflectance)",
            "satellite": "Suomi NPP",
            "format": "image/jpeg",
            "tile_matrix_set": "GoogleMapsCompatible_Level9",
            "max_zoom": 9,
            "description": "High-detail visible imagery showing tropical cyclone eye structures and feeder bands."
        },
        {
            "id": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "name": "MODIS Terra True Color",
            "satellite": "Terra",
            "format": "image/jpeg",
            "tile_matrix_set": "GoogleMapsCompatible_Level9",
            "max_zoom": 9,
            "description": "Morning visible spectrum pass capturing cyclone convection."
        },
        {
            "id": "MODIS_Aqua_CorrectedReflectance_TrueColor",
            "name": "MODIS Aqua True Color",
            "satellite": "Aqua",
            "format": "image/jpeg",
            "tile_matrix_set": "GoogleMapsCompatible_Level9",
            "max_zoom": 9,
            "description": "Afternoon visible pass capturing rapid eyewall development."
        },
        {
            "id": "AIRS_Precipitation_Day",
            "name": "AIRS Daytime Precipitation Rate",
            "satellite": "Aqua",
            "format": "image/png",
            "tile_matrix_set": "GoogleMapsCompatible_Level6",
            "max_zoom": 6,
            "description": "Atmospheric Infrared Sounder daily precipitation estimates."
        },
        {
            "id": "IMERG_Precipitation_Rate",
            "name": "GPM IMERG Early Precipitation Rate",
            "satellite": "GPM Constellation",
            "format": "image/png",
            "tile_matrix_set": "GoogleMapsCompatible_Level6",
            "max_zoom": 6,
            "description": "Global Precipitation Measurement multi-satellite precipitation estimate."
        }
    ]

    BASE_WMTS_URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "cache", "gibs")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_layer_catalog(self) -> List[Dict]:
        return self.AVAILABLE_LAYERS

    def get_tile_url_template(self, layer_id: str, date_str: str) -> str:
        """
        Returns Leaflet/WebMap tile URL template for a specific layer and date.
        Example: https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/2023-06-12/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg
        """
        layer_meta = next((l for l in self.AVAILABLE_LAYERS if l["id"] == layer_id), self.AVAILABLE_LAYERS[0])
        ext = "png" if "png" in layer_meta["format"] else "jpg"
        tms = layer_meta["tile_matrix_set"]
        return f"{self.BASE_WMTS_URL}/{layer_id}/default/{date_str}/{tms}/{{z}}/{{y}}/{{x}}.{ext}"

    def check_layer_availability(self, layer_id: str, date_str: str) -> Dict:
        """
        Probes a representative tile over the North Indian Ocean (z=4, x=11, y=7) to verify live response.
        Does not substitute dates or fabricate success.
        """
        test_url = f"{self.BASE_WMTS_URL}/{layer_id}/default/{date_str}/GoogleMapsCompatible_Level9/4/7/11.jpg"
        try:
            resp = requests.head(test_url, timeout=5)
            if resp.status_code == 200:
                return {
                    "provider": "NASA GIBS",
                    "layer": layer_id,
                    "date": date_str,
                    "status": "LIVE",
                    "http_status": 200,
                    "content_type": resp.headers.get("Content-Type", "image/jpeg"),
                    "details": "Live GIBS WMTS service responding with valid imagery."
                }
            elif resp.status_code == 404:
                return {
                    "provider": "NASA GIBS",
                    "layer": layer_id,
                    "date": date_str,
                    "status": "UNAVAILABLE",
                    "http_status": 404,
                    "details": f"No imagery granule available for {layer_id} on date {date_str}."
                }
            else:
                return {
                    "provider": "NASA GIBS",
                    "layer": layer_id,
                    "date": date_str,
                    "status": "UNAVAILABLE",
                    "http_status": resp.status_code,
                    "details": f"GIBS service returned status code {resp.status_code}."
                }
        except Exception as e:
            return {
                "provider": "NASA GIBS",
                "layer": layer_id,
                "date": date_str,
                "status": "UNAVAILABLE",
                "http_status": 0,
                "details": f"Network connection to GIBS endpoint failed: {str(e)}"
            }
