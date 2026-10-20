"""
Calibrate Empirical Quantile Uncertainty Cones on Validation Storms and
Evaluate Empirical Coverage on Untouched Test Split (70 storms).
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.preprocessing.ibtracs_parser import haversine_distance_km
from ml.models.track_predictor import CycloneGRUTrackNet
from ml.training.train_phase3 import extract_leakage_safe_sequences, apply_scaler

def main():
    print("=== Phase 6: Empirical Quantile Uncertainty Calibration ===")
    
    with open(os.path.join(PROJECT_ROOT, "ml", "data", "manifests", "val_storms.json")) as f:
        val_data = json.load(f)
        val_storms = set(val_data["storm_ids"] if isinstance(val_data, dict) else val_data)
    with open(os.path.join(PROJECT_ROOT, "ml", "data", "manifests", "test_storms.json")) as f:
        test_data = json.load(f)
        test_storms = set(test_data["storm_ids"] if isinstance(test_data, dict) else test_data)

    from ml.preprocessing.ibtracs_parser import IBTrACSProcessor
    modern_csv = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "ibtracs", "ibtracs_ni_modern.csv")
    processor = IBTrACSProcessor(csv_path=modern_csv)
    df = processor.load_and_clean()
    
    with open(os.path.join(PROJECT_ROOT, "artifacts", "checkpoints", "track_scaler.json")) as f:
        scaler_dict = json.load(f)

    # 1. Extract validation sequences (without leakage)
    X_va_raw, Y_va_coords, _, meta_va, _ = extract_leakage_safe_sequences(df, val_storms)
    X_va = apply_scaler(X_va_raw, scaler_dict)
    curr_pos_va = torch.tensor(X_va_raw[:, -1, :2], dtype=torch.float32)

    # 2. Extract test sequences
    X_te_raw, Y_te_coords, _, meta_te, _ = extract_leakage_safe_sequences(df, test_storms)
    X_te = apply_scaler(X_te_raw, scaler_dict)
    curr_pos_te = torch.tensor(X_te_raw[:, -1, :2], dtype=torch.float32)

    # 3. Load Model C checkpoint
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_path = os.path.join(PROJECT_ROOT, "artifacts", "checkpoints", "track_gru.pt")
    weights = torch.load(ckpt_path, map_location=device)
    track_model = CycloneGRUTrackNet(input_dim=6, hidden_dim=64, num_layers=2, num_horizons=3).to(device)
    track_model.load_state_dict(weights)
    track_model.eval()

    # 4. Compute residuals on Validation split (strictly no test data)
    with torch.no_grad():
        val_preds = track_model(torch.tensor(X_va, dtype=torch.float32), curr_pos=curr_pos_va).cpu().numpy()

    horizons = [6, 12, 24]
    val_errors = {h: [] for h in horizons}
    for i in range(len(X_va)):
        for j, h in enumerate(horizons):
            pred_lat, pred_lon = float(val_preds[i, j, 0]), float(val_preds[i, j, 1])
            true_lat, true_lon = float(Y_va_coords[i, j, 0]), float(Y_va_coords[i, j, 1])
            err_km = haversine_distance_km(pred_lat, pred_lon, true_lat, true_lon)
            val_errors[h].append(err_km)

    # Calibrate empirical quantile radii
    calibrated_radii = {}
    for h in horizons:
        errs = np.array(val_errors[h])
        calibrated_radii[f"{h}h"] = {
            "r70_km": round(float(np.percentile(errs, 70)), 2),
            "r80_km": round(float(np.percentile(errs, 80)), 2),
            "r90_km": round(float(np.percentile(errs, 90)), 2),
            "mean_residual_km": round(float(np.mean(errs)), 2),
            "median_residual_km": round(float(np.median(errs)), 2),
            "p95_residual_km": round(float(np.percentile(errs, 95)), 2),
            "validation_sample_size": len(errs)
        }

    print("\n--- Calibrated Empirical Quantile Radii (from 2,027 Validation Sequences) ---")
    for h_str, r in calibrated_radii.items():
        print(f"  Horizon {h_str}: 70%={r['r70_km']}km | 80%={r['r80_km']}km | 90%={r['r90_km']}km | Mean={r['mean_residual_km']}km")

    # 5. Evaluate empirical coverage on untouched Test Split (1,918 sequences)
    with torch.no_grad():
        test_preds = track_model(torch.tensor(X_te, dtype=torch.float32), curr_pos=curr_pos_te).cpu().numpy()

    test_errors = {h: [] for h in horizons}
    for i in range(len(X_te)):
        for j, h in enumerate(horizons):
            pred_lat, pred_lon = float(test_preds[i, j, 0]), float(test_preds[i, j, 1])
            true_lat, true_lon = float(Y_te_coords[i, j, 0]), float(Y_te_coords[i, j, 1])
            err_km = haversine_distance_km(pred_lat, pred_lon, true_lat, true_lon)
            test_errors[h].append(err_km)

    test_coverage = {}
    for h in horizons:
        errs = np.array(test_errors[h])
        q70_r = calibrated_radii[f"{h}h"]["r70_km"]
        q80_r = calibrated_radii[f"{h}h"]["r80_km"]
        q90_r = calibrated_radii[f"{h}h"]["r90_km"]
        cov70 = float(np.mean(errs <= q70_r) * 100)
        cov80 = float(np.mean(errs <= q80_r) * 100)
        cov90 = float(np.mean(errs <= q90_r) * 100)
        test_coverage[f"{h}h"] = {
            "target_70pct_actual_coverage": round(cov70, 2),
            "target_80pct_actual_coverage": round(cov80, 2),
            "target_90pct_actual_coverage": round(cov90, 2),
            "test_sample_size": len(errs)
        }

    print("\n--- Empirical Coverage on Untouched Test Split (1,918 Sequences, 70 Storms) ---")
    for h_str, cov in test_coverage.items():
        print(f"  Horizon {h_str}: Target 70% -> {cov['target_70pct_actual_coverage']}% | Target 80% -> {cov['target_80pct_actual_coverage']}% | Target 90% -> {cov['target_90pct_actual_coverage']}%")

    out_file = os.path.join(PROJECT_ROOT, "artifacts", "audit", "phase6_uncertainty_results.json")
    with open(out_file, "w") as f:
        json.dump({
            "calibration_method": "EMPIRICAL_QUANTILE_RESIDUAL_CALIBRATION",
            "calibration_split": "70_VALIDATION_STORMS_2027_SEQUENCES",
            "test_split": "70_TEST_STORMS_1918_SEQUENCES",
            "calibrated_radii": calibrated_radii,
            "empirical_test_coverage": test_coverage,
            "status": "CALIBRATED_EMPIRICAL_QUANTILES"
        }, f, indent=2)
    print(f"\nSaved uncertainty calibration to {out_file}")

if __name__ == "__main__":
    main()
