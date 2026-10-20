"""
Phase 3: Scientific Model Training, Leakage-Safe Sequence Building, and Genuine Evaluation.
- Uses IBTrACSProcessor.load_and_clean() to ensure 0 NaNs and consensus wind/pressure normalization.
- Fits scalers exclusively on Training storms.
- Predicts physical displacements from unscaled issue-time coordinates.
- Early stopping on Validation storms.
- Evaluates against Persistence and Constant-Motion Baselines on identical untouched Test sequences.
- Computes Mean, Median, and 90th percentile Geodesic Errors (Haversine KM).
- Evaluates per-storm performance including mandatory holdouts: Cyclone AMPHAN and BIPARJOY.
- Saves model weights, training configurations, loss curves, and predictions.
"""

import os
import sys
import json
import math
import hashlib
import random
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.preprocessing.ibtracs_parser import IBTrACSProcessor, haversine_distance_km, calculate_bearing
from ml.models.track_predictor import CycloneGRUTrackNet
from ml.models.intensity_predictor import IntensityRegressionNet

MODERN_DATA_PATH = os.path.join(PROJECT_ROOT, "ml", "data", "processed", "ibtracs", "ibtracs_ni_modern.csv")
MANIFEST_DIR = os.path.join(PROJECT_ROOT, "ml", "data", "manifests")
TRAIN_MANIFEST_PATH = os.path.join(MANIFEST_DIR, "train_storms.json")
VAL_MANIFEST_PATH = os.path.join(MANIFEST_DIR, "val_storms.json")
TEST_MANIFEST_PATH = os.path.join(MANIFEST_DIR, "test_storms.json")

CHECKPOINTS_DIR = os.path.join(PROJECT_ROOT, "artifacts", "checkpoints")
EVAL_DIR = os.path.join(PROJECT_ROOT, "artifacts", "evaluations")
AUDIT_DIR = os.path.join(PROJECT_ROOT, "artifacts", "audit")

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def extract_leakage_safe_sequences(
    df: pd.DataFrame,
    allowed_sids: set,
    seq_len: int = 4,
    lead_steps: list = [2, 4, 8], # corresponding to +6h, +12h, +24h given 3-hour fixes
    nominal_horizons: list = [6, 12, 24]
):
    """
    Vectorized extraction of chronological sequence windows strictly isolated within each storm ID.
    Rejection rules:
    - Storm ID not in allowed set.
    - Storm has fewer than seq_len + max(lead_steps) fixes.
    - Consecutive input fixes have a temporal gap > 6.0 hours (discontinuous tracking).
    - Future target fix is missing or time delta deviates by > 2.5 hours from nominal horizon.
    """
    X_list = []
    Y_coords_list = []
    Y_intensity_list = []
    meta_list = []
    
    rejection_reasons = {
        "storm_not_in_split": 0,
        "storm_too_short": 0,
        "input_gap_exceeded": 0,
        "target_horizon_misaligned": 0
    }

    feature_cols = ['LAT', 'LON', 'WMO_WIND', 'WMO_PRES', 'SPEED_KTS', 'BEARING_DEG']
    max_lead = max(lead_steps)

    for sid, group in df.groupby("SID"):
        if sid not in allowed_sids:
            rejection_reasons["storm_not_in_split"] += len(group)
            continue

        records = group.sort_values("ISO_TIME").reset_index(drop=True)
        n_obs = len(records)

        if n_obs < seq_len + max_lead:
            rejection_reasons["storm_too_short"] += 1
            continue

        records['ISO_TIME'] = pd.to_datetime(records['ISO_TIME'])
        feat_matrix = records[feature_cols].values.astype(np.float32)
        times = records['ISO_TIME'].values # numpy datetime64
        coords = records[['LAT', 'LON']].values.astype(np.float32)
        intens = records[['WMO_WIND', 'WMO_PRES']].values.astype(np.float32)
        storm_name = str(records['NAME'].iloc[0])
        storm_season = int(records['SEASON'].iloc[0])

        for t in range(seq_len, n_obs - max_lead + 1):
            # Check input window continuity: each step must be <= 6h from previous step
            input_window_times = times[t - seq_len : t]
            has_large_gap = False
            for k in range(1, seq_len):
                dt_h = (input_window_times[k] - input_window_times[k - 1]) / np.timedelta64(1, 'h')
                if dt_h > 6.0:
                    has_large_gap = True
                    break
            
            if has_large_gap:
                rejection_reasons["input_gap_exceeded"] += 1
                continue

            issue_time = input_window_times[-1]
            targets_valid = True
            y_coords = []
            y_intens = []

            for step_idx, h_nom in zip(lead_steps, nominal_horizons):
                target_idx = t + step_idx - 1
                target_time = times[target_idx]
                actual_delta_h = (target_time - issue_time) / np.timedelta64(1, 'h')
                
                # Tolerance: target must be within 2.5 hours of nominal horizon
                if abs(actual_delta_h - h_nom) > 2.5:
                    targets_valid = False
                    break
                
                y_coords.append(coords[target_idx])
                y_intens.append(intens[target_idx])

            if not targets_valid:
                rejection_reasons["target_horizon_misaligned"] += 1
                continue

            x_seq = feat_matrix[t - seq_len : t]
            X_list.append(x_seq)
            Y_coords_list.append(y_coords)
            Y_intensity_list.append(y_intens)
            meta_list.append({
                "sid": sid,
                "name": storm_name,
                "season": storm_season,
                "issue_time": pd.to_datetime(issue_time).isoformat() + "Z",
                "current_lat": float(coords[t - 1, 0]),
                "current_lon": float(coords[t - 1, 1]),
                "current_wind": float(intens[t - 1, 0]),
                "current_pres": float(intens[t - 1, 1]),
                "prev_lat": float(coords[t - 2, 0]),
                "prev_lon": float(coords[t - 2, 1])
            })

    X_arr = np.array(X_list, dtype=np.float32)
    Y_coords_arr = np.array(Y_coords_list, dtype=np.float32)
    Y_intensity_arr = np.array(Y_intensity_list, dtype=np.float32)

    return X_arr, Y_coords_arr, Y_intensity_arr, meta_list, rejection_reasons

def fit_training_scaler(X_train: np.ndarray, feature_names: list):
    """
    Fits mean and standard deviation scaling exclusively on Training data.
    X_train: [N, seq_len, num_features]
    """
    flat_features = X_train.reshape(-1, X_train.shape[-1])
    means = np.mean(flat_features, axis=0)
    stds = np.std(flat_features, axis=0)
    stds = np.where(stds < 1e-4, 1.0, stds)

    scaler_dict = {
        "features": feature_names,
        "means": [float(m) for m in means],
        "stds": [float(s) for s in stds],
        "fit_samples": int(X_train.shape[0]),
        "fit_timesteps_total": int(flat_features.shape[0])
    }
    return scaler_dict

def apply_scaler(X: np.ndarray, scaler_dict: dict) -> np.ndarray:
    means = np.array(scaler_dict["means"], dtype=np.float32)
    stds = np.array(scaler_dict["stds"], dtype=np.float32)
    return (X - means) / stds

def train_and_evaluate_phase3():
    print("==========================================================")
    print("PHASE 3: SCIENTIFIC MODEL TRAINING AND GENUINE EVALUATION")
    print("==========================================================")

    set_seed(42)
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
    os.makedirs(EVAL_DIR, exist_ok=True)
    os.makedirs(AUDIT_DIR, exist_ok=True)

    # 1. Load cleaned data via processor to guarantee 0 NaNs
    processor = IBTrACSProcessor(csv_path=MODERN_DATA_PATH)
    df = processor.load_and_clean()

    with open(TRAIN_MANIFEST_PATH, "r", encoding="utf-8") as f:
        train_sids = set(json.load(f)["storm_ids"])
    with open(VAL_MANIFEST_PATH, "r", encoding="utf-8") as f:
        val_sids = set(json.load(f)["storm_ids"])
    with open(TEST_MANIFEST_PATH, "r", encoding="utf-8") as f:
        test_sids = set(json.load(f)["storm_ids"])

    feature_cols = ['LAT', 'LON', 'WMO_WIND', 'WMO_PRES', 'SPEED_KTS', 'BEARING_DEG']
    lead_steps = [2, 4, 8] # +6h, +12h, +24h (3-hour grid)
    horizons = [6, 12, 24]

    print(f"Extracting leakage-safe sequences for Train (326 storms)...")
    X_tr_raw, Y_tr_coords, Y_tr_intens, meta_tr, rej_tr = extract_leakage_safe_sequences(
        df, train_sids, seq_len=4, lead_steps=lead_steps, nominal_horizons=horizons
    )
    print(f"Train sequences extracted: {len(X_tr_raw):,} (Rejections: {rej_tr})")

    print(f"Extracting leakage-safe sequences for Validation (70 storms)...")
    X_va_raw, Y_va_coords, Y_va_intens, meta_va, rej_va = extract_leakage_safe_sequences(
        df, val_sids, seq_len=4, lead_steps=lead_steps, nominal_horizons=horizons
    )
    print(f"Val sequences extracted: {len(X_va_raw):,} (Rejections: {rej_va})")

    print(f"Extracting leakage-safe sequences for Test (70 storms)...")
    X_te_raw, Y_te_coords, Y_te_intens, meta_te, rej_te = extract_leakage_safe_sequences(
        df, test_sids, seq_len=4, lead_steps=lead_steps, nominal_horizons=horizons
    )
    print(f"Test sequences extracted: {len(X_te_raw):,} (Rejections: {rej_te})")

    # 2. Fit Scaler ONLY on Training Data
    scaler_dict = fit_training_scaler(X_tr_raw, feature_cols)
    scaler_path = os.path.join(CHECKPOINTS_DIR, "track_scaler.json")
    with open(scaler_path, "w", encoding="utf-8") as f:
        json.dump(scaler_dict, f, indent=2)
    print(f"Fitted training scaler saved to {scaler_path}")

    # Scale inputs
    X_tr = apply_scaler(X_tr_raw, scaler_dict)
    X_va = apply_scaler(X_va_raw, scaler_dict)
    X_te = apply_scaler(X_te_raw, scaler_dict)

    # 3. Train Track GRU Model with Early Stopping
    print("\n--- Training Model C: CycloneGRUTrackNet ---")
    device = torch.device("cpu")
    track_model = CycloneGRUTrackNet(input_dim=6, hidden_dim=64, num_layers=2, num_horizons=3).to(device)
    optimizer = optim.Adam(track_model.parameters(), lr=0.003, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)
    criterion = nn.MSELoss()

    curr_pos_tr = torch.tensor(X_tr_raw[:, -1, :2], dtype=torch.float32)
    curr_pos_va = torch.tensor(X_va_raw[:, -1, :2], dtype=torch.float32)
    curr_pos_te = torch.tensor(X_te_raw[:, -1, :2], dtype=torch.float32)

    train_dataset = TensorDataset(torch.tensor(X_tr), curr_pos_tr, torch.tensor(Y_tr_coords))
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

    max_epochs = 35
    best_val_loss = float("inf")
    patience = 6
    patience_counter = 0
    best_weights = None
    best_epoch = 0
    loss_history = []

    start_time = datetime.datetime.utcnow()

    for ep in range(max_epochs):
        track_model.train()
        train_loss = 0.0
        for bx, b_pos, by in train_loader:
            optimizer.zero_grad()
            preds = track_model(bx, curr_pos=b_pos)
            loss = criterion(preds, by)
            if torch.isnan(loss) or torch.isinf(loss):
                raise ValueError(f"NaN/Inf loss encountered at epoch {ep+1}!")
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(bx)
        
        train_loss /= len(train_dataset)

        # Validation loss
        track_model.eval()
        with torch.no_grad():
            val_preds = track_model(torch.tensor(X_va), curr_pos=curr_pos_va)
            val_loss = criterion(val_preds, torch.tensor(Y_va_coords)).item()

        scheduler.step(val_loss)
        loss_history.append({
            "epoch": ep + 1,
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_loss, 5),
            "lr": float(optimizer.param_groups[0]["lr"])
        })
        print(f"  [Track GRU] Epoch {ep+1:2d}/{max_epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}", flush=True)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = ep + 1
            best_weights = {k: v.clone() for k, v in track_model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"  [Track GRU] Early stopping at epoch {ep+1}. Best epoch was {best_epoch} (val_loss: {best_val_loss:.5f})", flush=True)
                break

    # Restore best checkpoint
    track_model.load_state_dict(best_weights)
    track_ckpt_path = os.path.join(CHECKPOINTS_DIR, "track_gru.pt")
    torch.save(best_weights, track_ckpt_path)
    track_ckpt_sha256 = compute_sha256(track_ckpt_path)
    print(f"Saved best Track GRU checkpoint to {track_ckpt_path} (SHA-256: {track_ckpt_sha256})", flush=True)

    # 4. Train Intensity Predictor Model (Model D)
    print("\n--- Training Model D: IntensityRegressionNet ---", flush=True)
    intensity_model = IntensityRegressionNet(input_dim=6, hidden_dim=48).to(device)
    int_optimizer = optim.Adam(intensity_model.parameters(), lr=0.003, weight_decay=1e-4)
    int_scheduler = optim.lr_scheduler.ReduceLROnPlateau(int_optimizer, mode="min", factor=0.5, patience=3)
    int_criterion = nn.MSELoss()

    curr_wind_tr = X_tr_raw[:, -1, 2:3]
    curr_pres_tr = X_tr_raw[:, -1, 3:4]
    delta_wind_tr = Y_tr_intens[:, :, 0] - curr_wind_tr
    delta_pres_tr = Y_tr_intens[:, :, 1] - curr_pres_tr
    Y_tr_delta = np.stack([delta_wind_tr, delta_pres_tr], axis=-1).astype(np.float32)

    curr_wind_va = X_va_raw[:, -1, 2:3]
    curr_pres_va = X_va_raw[:, -1, 3:4]
    delta_wind_va = Y_va_intens[:, :, 0] - curr_wind_va
    delta_pres_va = Y_va_intens[:, :, 1] - curr_pres_va
    Y_va_delta = np.stack([delta_wind_va, delta_pres_va], axis=-1).astype(np.float32)

    int_train_dataset = TensorDataset(torch.tensor(X_tr), torch.tensor(Y_tr_delta))
    int_train_loader = DataLoader(int_train_dataset, batch_size=64, shuffle=True)

    int_best_val_loss = float("inf")
    int_best_epoch = 0
    int_best_weights = None
    int_patience_counter = 0
    int_loss_history = []

    for ep in range(max_epochs):
        intensity_model.train()
        train_loss = 0.0
        for bx, by in int_train_loader:
            int_optimizer.zero_grad()
            preds = intensity_model(bx)
            loss = int_criterion(preds, by)
            loss.backward()
            int_optimizer.step()
            train_loss += loss.item() * len(bx)
        train_loss /= len(int_train_dataset)

        intensity_model.eval()
        with torch.no_grad():
            val_preds = intensity_model(torch.tensor(X_va))
            val_loss = int_criterion(val_preds, torch.tensor(Y_va_delta)).item()

        int_scheduler.step(val_loss)
        int_loss_history.append({
            "epoch": ep + 1,
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_loss, 5)
        })
        print(f"  [Intensity] Epoch {ep+1:2d}/{max_epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}", flush=True)

        if val_loss < int_best_val_loss:
            int_best_val_loss = val_loss
            int_best_epoch = ep + 1
            int_best_weights = {k: v.clone() for k, v in intensity_model.state_dict().items()}
            int_patience_counter = 0
        else:
            int_patience_counter += 1
            if int_patience_counter >= patience:
                print(f"  [Intensity] Early stopping at epoch {ep+1}. Best epoch: {int_best_epoch}", flush=True)
                break

    intensity_model.load_state_dict(int_best_weights)
    int_ckpt_path = os.path.join(CHECKPOINTS_DIR, "intensity.pt")
    torch.save(int_best_weights, int_ckpt_path)
    int_ckpt_sha256 = compute_sha256(int_ckpt_path)
    print(f"Saved best Intensity checkpoint to {int_ckpt_path} (SHA-256: {int_ckpt_sha256})")

    # 5. Genuine Scientific Evaluation on Untouched Test Set (70 storms)
    print("\n--- Running Unbiased Evaluation on Untouched Test Split (70 storms) ---")
    track_model.eval()
    with torch.no_grad():
        test_track_preds = track_model(torch.tensor(X_te), curr_pos=curr_pos_te).cpu().numpy()

    intensity_model.eval()
    with torch.no_grad():
        test_int_deltas = intensity_model(torch.tensor(X_te)).cpu().numpy()
        curr_wind_te = X_te_raw[:, -1, 2:3]
        curr_pres_te = X_te_raw[:, -1, 3:4]
        test_wind_preds = curr_wind_te + test_int_deltas[:, :, 0]
        test_pres_preds = curr_pres_te + test_int_deltas[:, :, 1]

    test_predictions_record = []
    horizon_track_metrics = {h: {"model": [], "linear_baseline": [], "persistence": []} for h in horizons}
    horizon_wind_metrics = {h: {"model_abs_err": [], "pers_abs_err": []} for h in horizons}

    storm_specific_results = {}

    for i in range(len(X_te)):
        meta = meta_te[i]
        sid = meta["sid"]
        name = meta["name"]
        curr_lat, curr_lon = meta["current_lat"], meta["current_lon"]
        prev_lat, prev_lon = meta["prev_lat"], meta["prev_lon"]
        curr_w = meta["current_wind"]
        curr_p = meta["current_pres"]

        # Constant velocity from past 2 observations (dt = 3.0h)
        dt_v = 3.0
        v_lat = (curr_lat - prev_lat) / dt_v
        v_lon = (curr_lon - prev_lon) / dt_v

        if sid not in storm_specific_results:
            storm_specific_results[sid] = {
                "name": name,
                "season": meta["season"],
                "seq_count": 0,
                "errors_km": {h: [] for h in horizons},
                "baseline_errors_km": {h: [] for h in horizons}
            }
        storm_specific_results[sid]["seq_count"] += 1

        seq_record = {
            "sid": sid,
            "name": name,
            "issue_time": meta["issue_time"],
            "current_observation": {"lat": curr_lat, "lon": curr_lon, "wind_kts": curr_w, "pressure_hpa": curr_p},
            "horizons": {}
        }

        for j, h in enumerate(horizons):
            true_lat, true_lon = float(Y_te_coords[i, j, 0]), float(Y_te_coords[i, j, 1])
            true_wind = float(Y_te_intens[i, j, 0])
            true_pres = float(Y_te_intens[i, j, 1])

            # Model prediction
            pred_lat = float(test_track_preds[i, j, 0])
            pred_lon = float(test_track_preds[i, j, 1])
            pred_w = float(test_wind_preds[i, j])
            pred_p = float(test_pres_preds[i, j])

            # Baselines
            b_lat = curr_lat + v_lat * h
            b_lon = curr_lon + v_lon * h
            pers_lat = curr_lat
            pers_lon = curr_lon

            # Errors (Haversine KM)
            err_model_km = haversine_distance_km(pred_lat, pred_lon, true_lat, true_lon)
            err_linear_km = haversine_distance_km(b_lat, b_lon, true_lat, true_lon)
            err_pers_km = haversine_distance_km(pers_lat, pers_lon, true_lat, true_lon)

            err_w_model = abs(pred_w - true_wind)
            err_w_pers = abs(curr_w - true_wind)

            horizon_track_metrics[h]["model"].append(err_model_km)
            horizon_track_metrics[h]["linear_baseline"].append(err_linear_km)
            horizon_track_metrics[h]["persistence"].append(err_pers_km)

            horizon_wind_metrics[h]["model_abs_err"].append(err_w_model)
            horizon_wind_metrics[h]["pers_abs_err"].append(err_w_pers)

            storm_specific_results[sid]["errors_km"][h].append(err_model_km)
            storm_specific_results[sid]["baseline_errors_km"][h].append(err_linear_km)

            seq_record["horizons"][f"{h}h"] = {
                "ground_truth": {"lat": round(true_lat, 2), "lon": round(true_lon, 2), "wind_kts": round(true_wind, 1), "pressure_hpa": round(true_pres, 1)},
                "gru_track_pred": {"lat": round(pred_lat, 2), "lon": round(pred_lon, 2), "error_km": round(err_model_km, 1)},
                "linear_baseline_pred": {"lat": round(b_lat, 2), "lon": round(b_lon, 2), "error_km": round(err_linear_km, 1)},
                "persistence_pred": {"lat": round(pers_lat, 2), "lon": round(pers_lon, 2), "error_km": round(err_pers_km, 1)},
                "intensity_pred": {"wind_kts": round(pred_w, 1), "wind_err_kts": round(err_w_model, 1), "pers_wind_err_kts": round(err_w_pers, 1)}
            }

        test_predictions_record.append(seq_record)

    # 6. Compute Aggregate Summary Statistics
    aggregate_results = {
        "evaluation_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "total_test_sequences": len(X_te),
        "total_test_cyclones": len(storm_specific_results),
        "horizons_evaluated": [f"{h}h" for h in horizons],
        "track_metrics": {},
        "intensity_metrics": {},
        "holdout_storms": {}
    }

    for h in horizons:
        m_arr = np.array(horizon_track_metrics[h]["model"])
        b_arr = np.array(horizon_track_metrics[h]["linear_baseline"])
        p_arr = np.array(horizon_track_metrics[h]["persistence"])

        w_m_arr = np.array(horizon_wind_metrics[h]["model_abs_err"])
        w_p_arr = np.array(horizon_wind_metrics[h]["pers_abs_err"])

        mean_m = float(np.mean(m_arr))
        median_m = float(np.median(m_arr))
        p90_m = float(np.percentile(m_arr, 90))

        mean_b = float(np.mean(b_arr))
        median_b = float(np.median(b_arr))
        p90_b = float(np.percentile(b_arr, 90))

        mean_p = float(np.mean(p_arr))

        aggregate_results["track_metrics"][f"{h}h"] = {
            "model_mean_km": round(mean_m, 2),
            "model_median_km": round(median_m, 2),
            "model_p90_km": round(p90_m, 2),
            "linear_baseline_mean_km": round(mean_b, 2),
            "linear_baseline_median_km": round(median_b, 2),
            "linear_baseline_p90_km": round(p90_b, 2),
            "persistence_mean_km": round(mean_p, 2),
            "relative_improvement_vs_baseline_pct": round(((mean_b - mean_m) / mean_b) * 100, 2),
            "relative_improvement_vs_pers_pct": round(((mean_p - mean_m) / mean_p) * 100, 2),
            "sample_count": len(m_arr)
        }

        aggregate_results["intensity_metrics"][f"{h}h"] = {
            "model_mae_kts": round(float(np.mean(w_m_arr)), 2),
            "model_rmse_kts": round(float(np.sqrt(np.mean(w_m_arr**2))), 2),
            "persistence_mae_kts": round(float(np.mean(w_p_arr)), 2),
            "persistence_rmse_kts": round(float(np.sqrt(np.mean(w_p_arr**2))), 2),
            "skill_score_pct": round(((np.mean(w_p_arr) - np.mean(w_m_arr)) / max(np.mean(w_p_arr), 1e-4)) * 100, 2)
        }

    # Performance on holdouts: AMPHAN and BIPARJOY
    amphan_sid = "2020136N10088"
    biparjoy_sid = "2023156N10067"

    for sid, label in [(amphan_sid, "AMPHAN"), (biparjoy_sid, "BIPARJOY")]:
        if sid in storm_specific_results:
            st = storm_specific_results[sid]
            aggregate_results["holdout_storms"][label] = {
                "sid": sid,
                "name": st["name"],
                "season": st["season"],
                "evaluated_sequences": st["seq_count"],
                "results": {
                    f"{h}h": {
                        "gru_mean_km": round(float(np.mean(st["errors_km"][h])), 1) if st["errors_km"][h] else None,
                        "baseline_mean_km": round(float(np.mean(st["baseline_errors_km"][h])), 1) if st["baseline_errors_km"][h] else None
                    } for h in horizons
                }
            }

    # 7. Save Evaluation Artifacts
    pred_save_path = os.path.join(EVAL_DIR, "track_predictions_test.json")
    with open(pred_save_path, "w", encoding="utf-8") as f:
        json.dump(test_predictions_record[:250], f, indent=2)
    print(f"Sample test predictions saved to {pred_save_path}")

    track_eval_save_path = os.path.join(EVAL_DIR, "track_eval.json")
    with open(track_eval_save_path, "w", encoding="utf-8") as f:
        json.dump({
            "model": "CycloneGRUTrackNet",
            "epochs": best_epoch,
            "final_train_loss": round(loss_history[-1]["train_loss"], 4),
            "best_val_loss": round(best_val_loss, 4),
            "test_results_km": {
                f"{h}h": {
                    "model_mean_km": aggregate_results["track_metrics"][f"{h}h"]["model_mean_km"],
                    "baseline_mean_km": aggregate_results["track_metrics"][f"{h}h"]["linear_baseline_mean_km"]
                } for h in horizons
            },
            "loss_curve": loss_history
        }, f, indent=2)

    int_eval_save_path = os.path.join(EVAL_DIR, "intensity_eval.json")
    with open(int_eval_save_path, "w", encoding="utf-8") as f:
        json.dump({
            "model": "IntensityRegressionNet",
            "best_epoch": int_best_epoch,
            "final_val_loss": round(int_best_val_loss, 4),
            "test_results": aggregate_results["intensity_metrics"]
        }, f, indent=2)

    eval_results_path = os.path.join(AUDIT_DIR, "phase3_evaluation_results.json")
    with open(eval_results_path, "w", encoding="utf-8") as f:
        json.dump(aggregate_results, f, indent=2)
    print(f"Phase 3 evaluation results saved to {eval_results_path}")

    # 8. Training Configuration Record
    train_config = {
        "training_timestamp_utc": start_time.isoformat() + "Z",
        "random_seed": 42,
        "device": str(device),
        "track_model": {
            "architecture": "CycloneGRUTrackNet",
            "input_dim": 6,
            "hidden_dim": 64,
            "num_layers": 2,
            "dropout": 0.1,
            "learning_rate": 0.003,
            "batch_size": 32,
            "best_epoch": best_epoch,
            "best_val_loss": round(best_val_loss, 5),
            "checkpoint_sha256": track_ckpt_sha256
        },
        "intensity_model": {
            "architecture": "IntensityRegressionNet",
            "input_dim": 6,
            "hidden_dim": 48,
            "learning_rate": 0.003,
            "best_epoch": int_best_epoch,
            "best_val_loss": round(int_best_val_loss, 5),
            "checkpoint_sha256": int_ckpt_sha256
        },
        "dataset_hashes": {
            "modern_data_sha256": compute_sha256(MODERN_DATA_PATH),
            "train_manifest_sha256": compute_sha256(TRAIN_MANIFEST_PATH),
            "val_manifest_sha256": compute_sha256(VAL_MANIFEST_PATH),
            "test_manifest_sha256": compute_sha256(TEST_MANIFEST_PATH)
        }
    }
    config_save_path = os.path.join(AUDIT_DIR, "phase3_training_config.json")
    with open(config_save_path, "w", encoding="utf-8") as f:
        json.dump(train_config, f, indent=2)
    print(f"Phase 3 training config saved to {config_save_path}")

    # 9. Model Status Inventory
    model_status_record = {
        "status_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "models": [
            {
                "id": "model_c_track_gru",
                "name": "Model C: Cyclone Track Predictor (GRU)",
                "status": "TRAINED_EVALUATED",
                "evaluation_verdict": "GENUINELY_EVALUATED_ON_HOLDOUT",
                "checkpoint": "artifacts/checkpoints/track_gru.pt",
                "horizons": ["6h", "12h", "24h"],
                "results_summary": aggregate_results["track_metrics"]
            },
            {
                "id": "model_d_intensity",
                "name": "Model D: Cyclone Intensity Predictor (Regression Net)",
                "status": "TRAINED_EVALUATED",
                "evaluation_verdict": "GENUINELY_EVALUATED_ON_HOLDOUT",
                "checkpoint": "artifacts/checkpoints/intensity.pt",
                "horizons": ["6h", "12h", "24h"],
                "results_summary": aggregate_results["intensity_metrics"]
            },
            {
                "id": "model_a_detector",
                "name": "Model A: Cyclone Detection Network",
                "status": "UNTRAINED",
                "note": "Awaiting Phase 4 calibrated satellite imagery ingestion"
            },
            {
                "id": "model_b_classifier",
                "name": "Model B: Cyclone Structure Classifier",
                "status": "UNTRAINED",
                "note": "Awaiting Phase 4 calibrated satellite imagery ingestion"
            }
        ]
    }
    status_save_path = os.path.join(AUDIT_DIR, "phase3_model_status.json")
    with open(status_save_path, "w", encoding="utf-8") as f:
        json.dump(model_status_record, f, indent=2)
    print(f"Phase 3 model status saved to {status_save_path}")
    print("\n=== PHASE 3 TRAINING & EVALUATION COMPLETED ===")

    print("\n----------------- TRACK ERROR (KM) -----------------")
    print(f"{'Horizon':<10} | {'GRU Mean':<12} | {'Linear Baseline':<16} | {'Persistence':<12} | {'Improvement vs Base'}")
    for h in horizons:
        m = aggregate_results['track_metrics'][f'{h}h']
        print(f"+{h}h{'':<7} | {m['model_mean_km']:<12.1f} | {m['linear_baseline_mean_km']:<16.1f} | {m['persistence_mean_km']:<12.1f} | {m['relative_improvement_vs_baseline_pct']}%")

    print("\n----------------- INTENSITY ERROR (KTS) -----------------")
    print(f"{'Horizon':<10} | {'Model MAE':<12} | {'Persist MAE':<12} | {'Skill Score'}")
    for h in horizons:
        m = aggregate_results['intensity_metrics'][f'{h}h']
        print(f"+{h}h{'':<7} | {m['model_mae_kts']:<12.1f} | {m['persistence_mae_kts']:<12.1f} | {m['skill_score_pct']}%")

if __name__ == "__main__":
    train_and_evaluate_phase3()
