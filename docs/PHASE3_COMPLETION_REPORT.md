# CYCLOTRACK Phase 3 Completion Report: Real Model Training and Scientific Evaluation

**Project:** CYCLOTRACK — AI-Driven Digital Twin for Multi-Source Tropical Cyclone Pattern Analysis & Prediction  
**Problem Statement:** SIH26070 | **Team:** MISSION_POSSIBLE  
**Phase:** 3 — Real Model Training and Scientific Evaluation  
**Status:** Completed  
**Execution Timestamp:** 2026-10-20T03:24:00Z  

---

## 1. Executive Summary

In Phase 3, we transitioned CYCLOTRACK from heuristic and placeholder track/intensity estimators to genuinely trained, scientifically evaluated deep learning models trained on the official NOAA IBTrACS North Indian Ocean (NIO) dataset. 

Key achievements:
1. **Zero-Leakage Whole-Storm Data Partitions:** Sequences were extracted strictly within storm-level partitions defined in Phase 2 (`train`: 326 storms, `val`: 70 storms, `test`: 70 storms). Temporal autocorrelation between consecutive storm fixes cannot leak across splits.
2. **Standardized Sequence Extraction:** Built fixed 6-hour interval interpolation with a 24-hour observation lookback (4 steps) and multi-horizon targets (+6h, +12h, +24h).
3. **Rigorous Baseline Benchmarks:** Every model was benchmarked against official meteorological baselines: Linear Extrapolation (extrapolating recent translation velocity) and Persistence (zero-change).
4. **Trained Checkpoints with Reproducible Checksums:**
   - Model C: `artifacts/checkpoints/track_gru.pt` (SHA-256: `01d846e9f102555d728bff24b49dfa81bbf59f18a3bd54b3c3ffb9983f9ba36f`)
   - Model D: `artifacts/checkpoints/intensity.pt` (SHA-256: `f6b6d75089424f6f97ecaef0d37a08ae7f5182532a5f0fdf3c22c9d0fea2dce3`)
   - Scaler: `artifacts/checkpoints/track_scaler.json`
5. **Honest Metric Evaluation:** Results on 1,918 independent test sequences across 70 held-out storms demonstrate that the GRU significantly outperforms persistence across all horizons (54.6% to 61.5% error reduction) and beats linear extrapolation at +12h (2.59% skill) and +24h (9.17% skill).

---

## 2. Sequence Extraction and Data Integrity

The sequence generator enforces the following constraints:
- Input lookback: 4 timesteps (t-18h, t-12h, t-6h, t-0h)
- Feature vector (8 dimensions): `[lat, lon, v_lat, v_lon, speed_kts, bearing_deg, wind_kts, pressure_hpa]`
- Target horizons: +6h, +12h, +24h
- Normalization: Z-score scaling parameters fitted exclusively on the `train` split and persisted to `track_scaler.json`.

### Split Statistics:
| Split | Total Storms | Extracted Sequences | Rejections (horizon/short) |
|---|---|---|---|
| Train | 326 | 8,775 | 466 |
| Validation | 70 | 2,027 | 54 |
| Test | 70 | 1,918 | 57 |

---

## 3. Empirical Model Evaluation (Untouched Test Split: 1,918 sequences)

### Model C: Cyclone Track Predictor (CycloneGRUTrackNet)
Metric: Great-Circle Haversine Distance Error (km)

| Lead Time | GRU Mean Error (km) | GRU Median (km) | GRU P90 (km) | Linear Extrapolation (km) | Persistence (km) | Skill vs Linear (%) | Skill vs Persistence (%) |
|---|---|---|---|---|---|---|---|
| **+6h** | **32.0 km** | 27.8 km | 56.9 km | 30.8 km | 83.1 km | -3.81% | **+61.51%** |
| **+12h** | **67.9 km** | 60.0 km | 120.6 km | 69.7 km | 165.2 km | **+2.59%** | **+58.87%** |
| **+24h** | **148.3 km** | 133.7 km | 262.2 km | 163.3 km | 327.0 km | **+9.17%** | **+54.65%** |

*Scientific Insight:* At very short lead times (+6h), linear extrapolation of current cyclone velocity is exceptionally competitive (30.8 km vs 32.0 km), which is well-documented in tropical meteorology. Beyond 6 hours (+12h and +24h), dynamic steering flows cause track curvature that linear extrapolation cannot model; here, the GRU demonstrates superior predictive skill (+9.17% improvement at 24h).

### Model D: Cyclone Intensity Predictor (IntensityRegressionNet)
Metric: Maximum Sustained Wind Speed (knots)

| Lead Time | Model MAE (kts) | Model RMSE (kts) | Persistence MAE (kts) | Persistence RMSE (kts) | Skill Score vs Persistence (%) |
|---|---|---|---|---|---|
| **+6h** | 3.01 kts | 4.89 kts | 2.67 kts | 5.13 kts | -12.52% |
| **+12h** | 5.14 kts | 7.83 kts | 5.05 kts | 8.60 kts | -1.78% |
| **+24h** | **8.73 kts** | **12.67 kts** | 9.32 kts | 14.82 kts | **+6.29%** |

*Scientific Insight:* Intensity persistence is tough to beat in the 0–12h window for mature cyclones. At 24h, the neural regression model captures structural decay and intensification trends, providing a 6.29% skill score over persistence.

---

## 4. Notable Holdout Storm Case Studies

### Super Cyclonic Storm AMPHAN (May 2020)
- Evaluated Sequences: 40
- +6h Mean Error: 32.7 km (vs Linear 32.6 km)
- +12h Mean Error: 68.9 km (vs Linear 64.7 km)
- +24h Mean Error: 151.7 km (vs Linear 146.9 km)

### Extremely Severe Cyclonic Storm BIPARJOY (June 2023)
- Evaluated Sequences: 102
- +6h Mean Error: 24.3 km (vs Linear 26.3 km, +7.6% improvement)
- +12h Mean Error: 47.9 km (vs Linear 53.7 km, +10.8% improvement)
- +24h Mean Error: 99.4 km (vs Linear 126.8 km, **+21.6% improvement**)

On BIPARJOY's recurving trajectory across the Arabian Sea, the GRU showed dramatic superior performance over linear extrapolation, cutting 24-hour error from 126.8 km down to 99.4 km.

---

## 5. Artifacts and Audit Files Generated
1. `artifacts/checkpoints/track_gru.pt`: Best model weights (early stopping at epoch 14, validation loss 0.51257).
2. `artifacts/checkpoints/intensity.pt`: Best intensity model weights (early stopping at epoch 3).
3. `artifacts/checkpoints/track_scaler.json`: Scaler means and standard deviations.
4. `artifacts/evaluations/track_predictions_test.json`: Sequence-by-sequence predictions on the 70 test storms.
5. `artifacts/audit/phase3_training_config.json`: Hyperparameters, seeds, and training configuration.
6. `artifacts/audit/phase3_evaluation_results.json`: Comprehensive numerical benchmark results.
7. `artifacts/audit/phase3_model_status.json`: Machine-readable model readiness statuses.
