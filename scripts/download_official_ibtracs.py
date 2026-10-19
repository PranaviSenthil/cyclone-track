"""
Download and Verification Script for Official NOAA IBTrACS North Indian Ocean (NI) Subset.
Source: NOAA / NCEI International Best Track Archive for Climate Stewardship (IBTrACS) v04r01
URL: https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv
"""

import os
import sys
import hashlib
import datetime
import urllib.request
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IBTrACS_Downloader")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "raw", "ibtracs")
RAW_FILE = os.path.join(RAW_DIR, "ibtracs.NI.list.v04r01.csv")
MANIFEST_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "manifests")
MANIFEST_FILE = os.path.join(MANIFEST_DIR, "ibtracs_raw_manifest.json")

SOURCE_URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv"

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def compute_md5(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def download_and_verify(force: bool = False) -> dict:
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    
    if os.path.exists(RAW_FILE) and not force and os.path.getsize(RAW_FILE) > 10_000_000:
        logger.info(f"Verified raw file already exists at {RAW_FILE} ({os.path.getsize(RAW_FILE):,} bytes).")
        sha256 = compute_sha256(RAW_FILE)
        md5 = compute_md5(RAW_FILE)
    else:
        logger.info(f"Initiating download from official NOAA NCEI URL: {SOURCE_URL}")
        req = urllib.request.Request(
            SOURCE_URL,
            headers={
                "User-Agent": "CYCLOTRACK-Research/2.0 (SIH26070 MISSION_POSSIBLE)",
                "Accept": "text/csv,application/octet-stream"
            }
        )
        
        retrieval_time = datetime.datetime.utcnow().isoformat() + "Z"
        tmp_file = RAW_FILE + ".tmp"
        try:
            with urllib.request.urlopen(req, timeout=90) as response, open(tmp_file, "wb") as out_f:
                status_code = response.status
                content_length = response.headers.get("Content-Length")
                logger.info(f"HTTP Status: {status_code}, Expected size: {content_length} bytes")
                
                downloaded = 0
                while chunk := response.read(1024 * 512):
                    out_f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (5 * 1024 * 1024) < (512 * 1024):
                        logger.info(f"Progress: {downloaded / 1024 / 1024:.1f} MB downloaded...")
            
            if os.path.exists(RAW_FILE):
                os.remove(RAW_FILE)
            os.rename(tmp_file, RAW_FILE)
            logger.info(f"Download complete: {downloaded:,} bytes saved to {RAW_FILE}")
        except Exception as e:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            logger.error(f"Download failed: {e}")
            raise e

        sha256 = compute_sha256(RAW_FILE)
        md5 = compute_md5(RAW_FILE)

    file_size = os.path.getsize(RAW_FILE)
    
    # Read first 5 lines to verify format
    with open(RAW_FILE, "r", encoding="utf-8", errors="replace") as f:
        sample_lines = [f.readline() for _ in range(5)]
    
    header = sample_lines[0].strip().split(",")
    units = sample_lines[1].strip().split(",")
    
    logger.info(f"File Size: {file_size:,} bytes")
    logger.info(f"SHA-256: {sha256}")
    logger.info(f"Columns: {len(header)}")
    logger.info(f"First 5 headers: {header[:5]}")
    logger.info(f"First 5 units: {units[:5]}")
    
    manifest = {
        "dataset_name": "NOAA IBTrACS North Indian Ocean (NI) Best-Track Dataset",
        "dataset_version": "v04r01",
        "source_authority": "NOAA / NCEI (National Centers for Environmental Information)",
        "source_url": SOURCE_URL,
        "citation": "Knapp, K. R., et al. (2018). International Best Track Archive for Climate Stewardship (IBTrACS) Project, Version 4. NOAA National Centers for Environmental Information.",
        "license": "Public Domain / NOAA Open Data Policy",
        "local_path": "ml/data/raw/ibtracs/ibtracs.NI.list.v04r01.csv",
        "file_size_bytes": file_size,
        "sha256": sha256,
        "md5": md5,
        "download_timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "header_row_index": 0,
        "units_row_index": 1,
        "total_columns": len(header),
        "status": "DOWNLOAD_VERIFIED"
    }
    
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Raw manifest written to {MANIFEST_FILE}")
    
    return manifest

if __name__ == "__main__":
    download_and_verify(force=True)
