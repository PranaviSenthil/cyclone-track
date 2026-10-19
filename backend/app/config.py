import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "CYCLOTRACK — Tropical Cyclone Pattern Analysis & Prediction"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "*"

    # Data Provider configuration
    MOSDAC_API_KEY: str = ""
    MOSDAC_USER_EMAIL: str = ""
    MOSDAC_API_BASE_URL: str = "https://mosdac.gov.in/live/"
    NASA_GIBS_WMTS_URL: str = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

    # Paths
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    HISTORICAL_DATA_PATH: str = os.path.join(BASE_DIR, "ml", "data", "historical", "ibtracs_north_indian_ocean.csv")
    SAMPLE_IMAGERY_DIR: str = os.path.join(BASE_DIR, "ml", "data", "sample_imagery")
    CHECKPOINTS_DIR: str = os.path.join(BASE_DIR, "artifacts", "checkpoints")
    CACHE_DIR: str = os.path.join(BASE_DIR, "cache")

    def get_cors_origins(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
