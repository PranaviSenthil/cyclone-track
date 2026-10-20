"""
Stage 0: Inventory, Safety, Non-destructive Backups, and Phase 2 Data Revalidation.
Verifies all raw, processed, and manifest files, checks SHA-256 hashes,
calculates exact observation and storm split percentages, verifies disjointness
and holdout storm preservation, and produces audit artifacts.
"""

import os
import sys
import json
import shutil
import hashlib
import platform
import psutil
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_FILE = os.path.join(PROJECT_ROOT, "ml", "data", "raw", "ibtracs", "ibtracs.NI.list.v04r01.csv")
MODERN_FILE = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "ibtracs", "ibtracs_ni_modern.csv")
CLEAN_FILE = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "ibtracs", "ibtracs_ni_clean.csv")
MANIFEST_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "manifests")
TRAIN_MANIFEST = os.path.join(MANIFEST_DIR, "train_storms.json")
VAL_MANIFEST = os.path.join(MANIFEST_DIR, "val_storms.json")
TEST_MANIFEST = os.path.join(MANIFEST_DIR, "test_storms.json")
CHECKPOINTS_DIR = os.path.join(PROJECT_ROOT, "artifacts", "checkpoints")
EVALUATIONS_DIR = os.path.join(PROJECT_ROOT, "artifacts", "evaluations")
AUDIT_DIR = os.path.join(PROJECT_ROOT, "artifacts", "audit")

def get_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def execute_stage0():
    print("=== EXECUTING STAGE 0 AUDIT & SAFETY CHECKS ===")
    
    # 1. Non-destructive backups
    backup_ckpts = os.path.join(PROJECT_ROOT, "artifacts", "checkpoints_phase2_backup")
    backup_evals = os.path.join(PROJECT_ROOT, "artifacts", "evaluations_phase2_backup")
    
    if os.path.exists(CHECKPOINTS_DIR) and not os.path.exists(backup_ckpts):
        shutil.copytree(CHECKPOINTS_DIR, backup_ckpts)
        print(f"Backed up checkpoints to: {backup_ckpts}")
    else:
        print(f"Checkpoints backup already exists or source missing: {backup_ckpts}")
        
    if os.path.exists(EVALUATIONS_DIR) and not os.path.exists(backup_evals):
        shutil.copytree(EVALUATIONS_DIR, backup_evals)
        print(f"Backed up evaluations to: {backup_evals}")
    else:
        print(f"Evaluations backup already exists or source missing: {backup_evals}")

    # 2. Checkpoint hashes
    checkpoint_inventory = {}
    if os.path.exists(CHECKPOINTS_DIR):
        for fname in os.listdir(CHECKPOINTS_DIR):
            fpath = os.path.join(CHECKPOINTS_DIR, fname)
            if os.path.isfile(fpath):
                checkpoint_inventory[fname] = {
                    "size_bytes": os.path.getsize(fpath),
                    "sha256": get_file_sha256(fpath)
                }

    eval_inventory = {}
    if os.path.exists(EVALUATIONS_DIR):
        for fname in os.listdir(EVALUATIONS_DIR):
            fpath = os.path.join(EVALUATIONS_DIR, fname)
            if os.path.isfile(fpath):
                eval_inventory[fname] = {
                    "size_bytes": os.path.getsize(fpath),
                    "sha256": get_file_sha256(fpath)
                }

    # 3. Environment Specs
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage(PROJECT_ROOT)
    env_specs = {
        "os": platform.platform(),
        "python_version": sys.version,
        "cpu_count": os.cpu_count(),
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "ram_available_gb": round(ram.available / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "cuda_available": False
    }

    # 4. Verify Raw & Processed Data
    assert os.path.exists(RAW_FILE), f"Raw file missing: {RAW_FILE}"
    assert os.path.exists(MODERN_FILE), f"Modern file missing: {MODERN_FILE}"
    
    raw_size = os.path.getsize(RAW_FILE)
    raw_sha256 = get_file_sha256(RAW_FILE)
    expected_raw_sha256 = "b30984b56c428391eff17a44d1a9662e444fc4ba419417e9613c18db07424155"
    assert raw_sha256 == expected_raw_sha256, f"Raw SHA256 mismatch! Got {raw_sha256}"
    
    # Check raw header & units
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        line0 = f.readline().strip().split(",")
        line1 = f.readline().strip().split(",")
    raw_col_count = len(line0)
    has_units_row = "kts" in line1 or "Year" in line1
    
    # Inspect processed modern file
    modern_df = pd.read_csv(MODERN_FILE)
    modern_rows = len(modern_df)
    modern_storms = modern_df["SID"].nunique()
    
    # 5. Manifest Auditing & Exact Percentage Calculation
    assert os.path.exists(TRAIN_MANIFEST), "Train manifest missing"
    assert os.path.exists(VAL_MANIFEST), "Val manifest missing"
    assert os.path.exists(TEST_MANIFEST), "Test manifest missing"
    
    with open(TRAIN_MANIFEST, "r", encoding="utf-8") as f:
        train_data = json.load(f)
    with open(VAL_MANIFEST, "r", encoding="utf-8") as f:
        val_data = json.load(f)
    with open(TEST_MANIFEST, "r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    train_sids = set(train_data["storm_ids"])
    val_sids = set(val_data["storm_ids"])
    test_sids = set(test_data["storm_ids"])
    
    # Disjointness checks
    disjoint_tr_va = len(train_sids.intersection(val_sids)) == 0
    disjoint_tr_te = len(train_sids.intersection(test_sids)) == 0
    disjoint_va_te = len(val_sids.intersection(test_sids)) == 0
    assert disjoint_tr_va and disjoint_tr_te and disjoint_va_te, "Disjointness violated!"
    
    total_manifest_storms = len(train_sids) + len(val_sids) + len(test_sids)
    assert total_manifest_storms == modern_storms, f"Storm count mismatch: {total_manifest_storms} vs {modern_storms}"
    
    # Observation counts directly from the dataset matching the manifest SIDs
    train_obs_actual = int(modern_df[modern_df["SID"].isin(train_sids)].shape[0])
    val_obs_actual = int(modern_df[modern_df["SID"].isin(val_sids)].shape[0])
    test_obs_actual = int(modern_df[modern_df["SID"].isin(test_sids)].shape[0])
    total_obs_actual = train_obs_actual + val_obs_actual + test_obs_actual
    assert total_obs_actual == modern_rows, f"Observation count mismatch: {total_obs_actual} vs {modern_rows}"
    
    # Exact percentage calculations
    storm_percentages = {
        "train": round((len(train_sids) / total_manifest_storms) * 100, 3),
        "val": round((len(val_sids) / total_manifest_storms) * 100, 3),
        "test": round((len(test_sids) / total_manifest_storms) * 100, 3)
    }
    obs_percentages = {
        "train": round((train_obs_actual / total_obs_actual) * 100, 3),
        "val": round((val_obs_actual / total_obs_actual) * 100, 3),
        "test": round((test_obs_actual / total_obs_actual) * 100, 3)
    }
    
    # Verify mandatory holdout storms
    amphan_sid = "2020136N10088"
    biparjoy_sid = "2023156N10067"
    dana_sid = "2024295N15092"
    remal_sid = "2024145N14087"
    michaung_sid = "2023334N08088"
    
    assert amphan_sid in test_sids, f"AMPHAN ({amphan_sid}) NOT in test manifest!"
    assert biparjoy_sid in test_sids, f"BIPARJOY ({biparjoy_sid}) NOT in test manifest!"
    assert dana_sid in val_sids, f"DANA ({dana_sid}) NOT in val manifest!"
    assert remal_sid in val_sids, f"REMAL ({remal_sid}) NOT in val manifest!"
    assert michaung_sid in val_sids, f"MICHAUNG ({michaung_sid}) NOT in val manifest!"
    
    print(f"Validated holdout storms: AMPHAN ({amphan_sid}) and BIPARJOY ({biparjoy_sid}) in TEST.")
    print(f"Validated holdout storms: DANA ({dana_sid}), REMAL ({remal_sid}), MICHAUNG ({michaung_sid}) in VAL.")
    print(f"Storm counts: Train={len(train_sids)} ({storm_percentages['train']}%), Val={len(val_sids)} ({storm_percentages['val']}%), Test={len(test_sids)} ({storm_percentages['test']}%)")
    print(f"Obs counts: Train={train_obs_actual} ({obs_percentages['train']}%), Val={val_obs_actual} ({obs_percentages['val']}%), Test={test_obs_actual} ({obs_percentages['test']}%)")

    # 6. Save Initial Inventory Artifact
    initial_inventory = {
        "audit_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "project_root": PROJECT_ROOT,
        "environment": env_specs,
        "checkpoints_inventory": checkpoint_inventory,
        "evaluations_inventory": eval_inventory,
        "data_files": {
            "raw_ibtracs": {
                "path": "ml/data/raw/ibtracs/ibtracs.NI.list.v04r01.csv",
                "size_bytes": raw_size,
                "sha256": raw_sha256,
                "has_units_row": has_units_row,
                "columns": raw_col_count
            },
            "processed_modern": {
                "path": "ml/data/processed/ibtracs/ibtracs_ni_modern.csv",
                "size_bytes": os.path.getsize(MODERN_FILE),
                "sha256": get_file_sha256(MODERN_FILE),
                "rows": modern_rows,
                "unique_cyclones": modern_storms
            }
        },
        "backups_created": [backup_ckpts, backup_evals]
    }
    
    inventory_path = os.path.join(AUDIT_DIR, "master_phase3_7_initial_inventory.json")
    with open(inventory_path, "w", encoding="utf-8") as f:
        json.dump(initial_inventory, f, indent=2)
    print(f"Wrote initial inventory to: {inventory_path}")

    # 7. Save Data Integrity Artifact
    data_integrity = {
        "validation_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "raw_checksum_verified": raw_sha256 == expected_raw_sha256,
        "raw_sha256": raw_sha256,
        "modern_era_filter": "SEASON >= 1980 and obs_count >= 4",
        "total_modern_observations": modern_rows,
        "total_modern_cyclones": modern_storms,
        "temporal_range": {
            "start": str(modern_df["ISO_TIME"].min()),
            "end": str(modern_df["ISO_TIME"].max()),
            "start_year": int(modern_df["SEASON"].min()),
            "end_year": int(modern_df["SEASON"].max())
        },
        "manifest_integrity": {
            "train_storms": len(train_sids),
            "val_storms": len(val_sids),
            "test_storms": len(test_sids),
            "total_storms": total_manifest_storms,
            "storm_percentages": storm_percentages,
            "train_observations": train_obs_actual,
            "val_observations": val_obs_actual,
            "test_observations": test_obs_actual,
            "total_observations": total_obs_actual,
            "observation_percentages": obs_percentages,
            "disjointness_verified": True,
            "overlap_train_val": len(train_sids.intersection(val_sids)),
            "overlap_train_test": len(train_sids.intersection(test_sids)),
            "overlap_val_test": len(val_sids.intersection(test_sids))
        },
        "holdout_storms": {
            "AMPHAN": {"sid": amphan_sid, "split": "TEST", "preserved": amphan_sid in test_sids},
            "BIPARJOY": {"sid": biparjoy_sid, "split": "TEST", "preserved": biparjoy_sid in test_sids},
            "DANA": {"sid": dana_sid, "split": "VAL", "preserved": dana_sid in val_sids},
            "REMAL": {"sid": remal_sid, "split": "VAL", "preserved": remal_sid in val_sids},
            "MICHAUNG": {"sid": michaung_sid, "split": "VAL", "preserved": michaung_sid in val_sids}
        },
        "percentage_correction_note": (
            "Previous Phase 2 report recorded storm-count percentages (69.957%, 15.021%, 15.021%) in place of observation percentages. "
            "Actual exact observation split percentages are: Train=69.654% (12,661 obs), Val=15.519% (2,821 obs), Test=14.826% (2,695 obs). "
            "Actual exact storm split percentages are: Train=69.957% (326 storms), Val=15.021% (70 storms), Test=15.021% (70 storms). "
            "Split membership is 100% preserved without any alteration."
        ),
        "data_integrity_verdict": "CRITICAL_CHECKS_PASSED"
    }

    integrity_path = os.path.join(AUDIT_DIR, "master_phase3_7_data_integrity.json")
    with open(integrity_path, "w", encoding="utf-8") as f:
        json.dump(data_integrity, f, indent=2)
    print(f"Wrote data integrity report to: {integrity_path}")
    print("=== STAGE 0 COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    execute_stage0()
