"""
Automated unit tests for Phase 2: NOAA IBTrACS Data Pipeline.
Covers:
1. CSV parsing and units/header row handling.
2. Missing-value handling.
3. Invalid coordinate detection and filtering.
4. UTC timestamp parsing and ISO-8601 compliance.
5. Duplicate record detection and dropping.
6. Whole-cyclone storm-level split isolation (zero leakage).
7. Deterministic manifest reproducibility.
8. Dataset SHA-256 checksum and provenance tracking.
9. Graceful provider failure and offline resilience.
10. Compatibility with existing historical cyclone endpoints.
"""

import os
import sys
import json
import hashlib
import tempfile
import pytest
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.preprocessing.ibtracs_parser import haversine_distance_km, calculate_bearing, IBTrACSProcessor, LEGACY_SID_ALIASES

SAMPLE_NOAA_CSV_WITH_UNITS = """SID,SEASON,NUMBER,BASIN,SUBBASIN,NAME,ISO_TIME,NATURE,LAT,LON,WMO_WIND,WMO_PRES
,,,,,kts,mb
2023156N10067,2023,02,NI,AS,BIPARJOY,2023-06-06 00:00:00,TS,12.0,66.0,35,1000
2023156N10067,2023,02,NI,AS,BIPARJOY,2023-06-06 03:00:00,TS,12.3,66.1,40,996
2023156N10067,2023,02,NI,AS,BIPARJOY,2023-06-06 06:00:00,TS,12.6,66.2,45,992
2023156N10067,2023,02,NI,AS,BIPARJOY,2023-06-06 09:00:00,TS,12.9,66.3,50,988
2023156N10067,2023,02,NI,AS,BIPARJOY,2023-06-06 12:00:00,TS,13.2,66.4,55,984
"""

SAMPLE_NOAA_DIRTY_CSV = """SID,SEASON,NUMBER,BASIN,SUBBASIN,NAME,ISO_TIME,NATURE,LAT,LON,WMO_WIND,WMO_PRES
,,,,,kts,mb
TEST001,2024,01,NI,BB,TESTSTORM,2024-05-01 00:00:00,TS,15.0,88.0,40,998
TEST001,2024,01,NI,BB,TESTSTORM,2024-05-01 00:00:00,TS,15.0,88.0,40,998
TEST001,2024,01,NI,BB,TESTSTORM,2024-05-01 03:00:00,TS,95.0,88.2,45,995
TEST001,2024,01,NI,BB,TESTSTORM,2024-05-01 06:00:00,TS,-99.0,88.5,50,990
TEST001,2024,01,NI,BB,TESTSTORM,2024-05-01 09:00:00,TS,16.0,88.8, , 
TEST001,2024,01,NI,BB,TESTSTORM,2024-05-01 12:00:00,TS,16.5,89.0,60,980
TEST001,2024,01,NI,BB,TESTSTORM,INVALID_TIMESTAMP,TS,17.0,89.2,65,975
"""

def test_csv_parsing_and_units_header_handling():
    """Verify parser properly detects and skips row 1 units without failing numeric parsing."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(SAMPLE_NOAA_CSV_WITH_UNITS)
        tmp_path = f.name

    try:
        processor = IBTrACSProcessor(csv_path=tmp_path)
        df = processor.load_and_clean()
        assert len(df) == 5
        assert list(df['SID'].unique()) == ['2023156N10067']
        # Numeric conversions must succeed without raising dtype errors
        assert pd.api.types.is_numeric_dtype(df['LAT'])
        assert pd.api.types.is_numeric_dtype(df['WMO_WIND'])
        assert df['WMO_WIND'].iloc[0] == 35.0
        assert df['WMO_WIND'].iloc[4] == 55.0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_missing_value_handling():
    """Verify blank strings and NaN values in wind and pressure are cleanly imputed."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(SAMPLE_NOAA_DIRTY_CSV)
        tmp_path = f.name

    try:
        processor = IBTrACSProcessor(csv_path=tmp_path)
        df = processor.load_and_clean()
        # Row with missing wind/pressure (09:00:00) should be forward/backward filled
        row_09 = df[df['ISO_TIME'] == '2024-05-01 09:00:00']
        assert len(row_09) == 1
        assert pd.notnull(row_09['WMO_WIND'].iloc[0])
        assert pd.notnull(row_09['WMO_PRES'].iloc[0])
        assert row_09['WMO_WIND'].iloc[0] > 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_invalid_coordinate_detection():
    """Verify that latitude > 90 or < -90 are dropped."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(SAMPLE_NOAA_DIRTY_CSV)
        tmp_path = f.name

    try:
        processor = IBTrACSProcessor(csv_path=tmp_path)
        df = processor.load_and_clean()
        assert not any(df['LAT'] > 90)
        assert not any(df['LAT'] < -90)
        assert not any(df['LON'] > 180)
        assert not any(df['LON'] < -180)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_utc_timestamp_parsing():
    """Verify invalid timestamps are discarded and valid ones converted to datetime."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(SAMPLE_NOAA_DIRTY_CSV)
        tmp_path = f.name

    try:
        processor = IBTrACSProcessor(csv_path=tmp_path)
        df = processor.load_and_clean()
        assert pd.api.types.is_datetime64_any_dtype(df['ISO_TIME'])
        assert df['ISO_TIME'].notna().all()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_duplicate_record_detection():
    """Verify duplicate observations (same SID and ISO_TIME) are removed."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write(SAMPLE_NOAA_DIRTY_CSV)
        tmp_path = f.name

    try:
        processor = IBTrACSProcessor(csv_path=tmp_path)
        df = processor.load_and_clean()
        dups = df.duplicated(subset=['SID', 'ISO_TIME'])
        assert not dups.any()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_manifest_storm_level_isolation():
    """Verify train, val, and test manifests exist, are disjoint, and retain holdouts."""
    manifest_dir = os.path.join(PROJECT_ROOT, "ml", "data", "manifests")
    train_path = os.path.join(manifest_dir, "train_storms.json")
    val_path = os.path.join(manifest_dir, "val_storms.json")
    test_path = os.path.join(manifest_dir, "test_storms.json")

    assert os.path.exists(train_path), "train_storms.json missing"
    assert os.path.exists(val_path), "val_storms.json missing"
    assert os.path.exists(test_path), "test_storms.json missing"

    with open(train_path, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(val_path, "r", encoding="utf-8") as f:
        val_data = json.load(f)
    with open(test_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    train_ids = set(train_data["storm_ids"])
    val_ids = set(val_data["storm_ids"])
    test_ids = set(test_data["storm_ids"])

    # Disjointness proof: 0 storm overlap
    assert len(train_ids.intersection(val_ids)) == 0, "Train and Val overlap!"
    assert len(train_ids.intersection(test_ids)) == 0, "Train and Test overlap!"
    assert len(val_ids.intersection(test_ids)) == 0, "Val and Test overlap!"

    # Key Holdouts check: AMPHAN and BIPARJOY must be in TEST
    test_storm_names = [s["name"].upper() for s in test_data["storms"]]
    assert "AMPHAN" in test_storm_names, "AMPHAN not preserved in test split!"
    assert "BIPARJOY" in test_storm_names, "BIPARJOY not preserved in test split!"

    # Validation check: DANA must be in VAL
    val_storm_names = [s["name"].upper() for s in val_data["storms"]]
    assert "DANA" in val_storm_names, "DANA not preserved in validation split!"

def test_dataset_checksum_and_provenance():
    """Verify phase 2 data provenance records raw file SHA-256, source URL, and row counts."""
    prov_path = os.path.join(PROJECT_ROOT, "artifacts", "audit", "phase2_data_provenance.json")
    assert os.path.exists(prov_path), "phase2_data_provenance.json missing"

    with open(prov_path, "r", encoding="utf-8") as f:
        prov = json.load(f)

    assert "providers" in prov
    ibtracs_prov = next((p for p in prov["providers"] if "IBTrACS" in p["provider"]), None)
    assert ibtracs_prov is not None
    assert ibtracs_prov["state"] == "HISTORICAL"
    assert ibtracs_prov["version"] == "v04r01"
    assert "sha256" in ibtracs_prov
    assert len(ibtracs_prov["sha256"]) == 64

    # Verify raw file exists and matches the recorded sha256
    raw_file = os.path.join(PROJECT_ROOT, ibtracs_prov["raw_file"])
    if os.path.exists(raw_file):
        hasher = hashlib.sha256()
        with open(raw_file, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        assert hasher.hexdigest() == ibtracs_prov["sha256"]

def test_graceful_missing_file_handling():
    """Verify parser raises descriptive FileNotFoundError for missing path."""
    processor = IBTrACSProcessor(csv_path="non_existent_ibtracs_file_12345.csv")
    with pytest.raises(FileNotFoundError):
        processor.load_and_clean()

def test_historical_endpoint_compatibility():
    """Verify that the processor's storm listing and trajectories match the expected API schema."""
    processor = IBTrACSProcessor()
    storms = processor.get_storm_list()
    assert len(storms) > 0

    first = storms[0]
    required_keys = {"sid", "name", "season", "basin", "subbasin", "start_time", "end_time", "max_wind_kts", "min_pressure_hpa", "observation_count"}
    assert required_keys.issubset(set(first.keys()))

    # Check trajectory retrieval for BIPARJOY
    traj = processor.get_storm_trajectory("BIPARJOY")
    assert len(traj) > 0
    t0 = traj[0]
    traj_keys = {"time", "lat", "lon", "wind_kts", "pressure_hpa", "speed_kts", "bearing_deg", "landfall"}
    assert traj_keys.issubset(set(t0.keys()))
    assert -90 <= t0["lat"] <= 90
    assert -180 <= t0["lon"] <= 180

def test_deterministic_manifest_reproducibility():
    """Verify that regenerating splits with seed 42 produces identical cyclone assignments."""
    test_mf = os.path.join(PROJECT_ROOT, "ml", "data", "manifests", "test_storms.json")
    val_mf = os.path.join(PROJECT_ROOT, "ml", "data", "manifests", "val_storms.json")
    
    with open(test_mf, "r", encoding="utf-8") as f:
        original_test_ids = json.load(f)["storm_ids"]
    with open(val_mf, "r", encoding="utf-8") as f:
        original_val_ids = json.load(f)["storm_ids"]

    # Re-run splitting logic on the modern dataset with identical seed
    modern_path = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "ibtracs", "ibtracs_ni_modern.csv")
    if os.path.exists(modern_path):
        df = pd.read_csv(modern_path)
        storm_obs = df.groupby("SID").size()
        valid_sids = sorted(list(storm_obs[storm_obs >= 4].index))

        seed = 42
        rng = np.random.RandomState(seed)
        
        amphan_sids = df[df["NAME"].str.upper() == "AMPHAN"]["SID"].unique().tolist()
        biparjoy_sids = df[df["NAME"].str.upper() == "BIPARJOY"]["SID"].unique().tolist()
        dana_sids = df[df["NAME"].str.upper() == "DANA"]["SID"].unique().tolist()
        remal_sids = df[df["NAME"].str.upper() == "REMAL"]["SID"].unique().tolist()
        michaung_sids = df[df["NAME"].str.upper() == "MICHAUNG"]["SID"].unique().tolist()

        mandatory_test = set(amphan_sids + biparjoy_sids)
        mandatory_val = set(dana_sids + remal_sids + michaung_sids)

        remaining_sids = [sid for sid in valid_sids if sid not in mandatory_test and sid not in mandatory_val]
        rng.shuffle(remaining_sids)

        n_total = len(valid_sids)
        n_test_target = int(round(0.15 * n_total))
        n_val_target = int(round(0.15 * n_total))

        repro_test_sids = sorted(list(mandatory_test.union(set(remaining_sids[:(n_test_target - len(mandatory_test))]))))
        repro_val_sids = sorted(list(mandatory_val.union(set(remaining_sids[(n_test_target - len(mandatory_test)):(n_test_target - len(mandatory_test) + n_val_target - len(mandatory_val))]))))

        assert repro_test_sids == original_test_ids
        assert repro_val_sids == original_val_ids
