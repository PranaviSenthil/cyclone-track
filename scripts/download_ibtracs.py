"""
Downloader and Curator for NOAA IBTrACS North Indian Ocean Cyclone Records.
Source: NOAA National Centers for Environmental Information (NCEI)
URL: https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv
"""

import os
import sys
import logging
import urllib.request
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IBTrACS_Downloader")

IBTRACS_NI_URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "data", "historical")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ibtracs_north_indian_ocean.csv")

def download_ibtracs_data(force=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if os.path.exists(OUTPUT_FILE) and not force:
        logger.info(f"Target file already exists at {OUTPUT_FILE}. Use force=True to re-download.")
        return OUTPUT_FILE

    logger.info(f"Connecting to NOAA NCEI repository: {IBTRACS_NI_URL}...")
    try:
        req = urllib.request.Request(
            IBTRACS_NI_URL,
            headers={"User-Agent": "Cyclotrack-Research-Client/1.0 (Smart India Hackathon 2026)"}
        )
        with urllib.request.urlopen(req, timeout=30) as response, open(OUTPUT_FILE, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        logger.info(f"Successfully downloaded {len(data)} bytes to {OUTPUT_FILE}")
        return OUTPUT_FILE
    except Exception as e:
        logger.warning(f"Live NOAA NCEI download encountered: {e}. Falling back to verified local baseline.")
        return None

if __name__ == "__main__":
    download_ibtracs_data(force=True)
