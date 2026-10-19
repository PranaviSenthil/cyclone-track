# CYCLOTRACK | AI Agent & Model Audit Summary

**Audit Date:** 2026-10-19  
**Auditor:** Senior AI/ML Engineer & Systems Auditor  
**System:** CYCLOTRACK (SIH26070 Prototype)  
**Overall Verdict:** **Full-Stack Application Functional; AI Models Primarily Prototype/Heuristic with Untrained Checkpoints and Hardcoded Benchmark Claims.**

---

## 1. Real Status of the Six AI Models

| Model | Classification Verdict | Real Implementation Status | Checkpoint Integrity |
| :--- | :--- | :--- | :--- |
| **Model A: Cyclone Detection & Center** | **Implementation exists, training unverified** | Architecture coded with dual heads; never trained on labeled satellite data. Outputs ~0.50 confidence and ~(256, 256) center on any image (including blank arrays). | `detector.pt` (5.77 MB) contains uninitialized random PyTorch weights. |
| **Model B: Structure Classification** | **Implementation exists, training unverified** | 4-stage ConvNet coded; never trained on categorized storm imagery. Outputs ~0.21 uniform probability for class 0 regardless of input. | `classifier.pt` (1.71 MB) contains uninitialized random PyTorch weights. |
| **Model C: Track Prediction (GRU)** | **Trained artifacts found, validation incomplete** | Recurrent GRU trained on 23 historical sequences for 35 epochs. Evaluated test error on holdout storms is **271.8 km at 24h**, underperforming the motion baseline (58.6 km) due to small sample size. | `track_gru.pt` (179 KB) is genuinely trained, but severely underfit. |
| **Model D: Intensity Prediction** | **Prototype or heuristic only** | MLP regressor coded, but inference code does not load `intensity.pt` and sets `self.is_trained = False`. Model outputs are random linear projections bounded by heuristics. | `intensity.pt` (16 KB) exists but is unused by inference. |
| **Model E: Uncertainty Estimation** | **Prototype or heuristic only** | Not a quantile regression or ensemble model. Plots Leaflet cone polygons using a fixed static lookup table of operational radii (45, 80, 150 km). | No checkpoint; geometric algorithm with hardcoded constants. |
| **Model F: Multimodal Fusion** | **Placeholder/mock implementation** | No neural fusion mechanism exists. `fused_track` merely copies `gru_track` coordinates. Reported ablation matrix is a static dictionary of hardcoded numbers. | No fusion checkpoint or trained fusion parameters. |

---

## 2. Top Five Issues Ranked by Severity

### Issue 1: Fabricated Benchmark Metrics Presented as Evaluated AI Performance
- **Severity:** **CRITICAL**
- **Location:** `ml/models/fusion.py:138-180`, `frontend/src/components/OverviewSection.tsx:65`, `frontend/src/components/TrackIntensitySection.tsx:64`
- **Finding:** The reported benchmark metrics (24h error: 122.9 km, wind MAE: 7.1 kts, F1: 0.887, 32.6% improvement) are hardcoded literals. The actual GRU model evaluation produced an error of **271.8 km at 24h** (4.6x worse than the 58.6 km baseline). No ablation study was ever executed.

### Issue 2: Vision Models (A & B) and Intensity Model (D) Use Untrained Random Checkpoints
- **Severity:** **CRITICAL**
- **Location:** `ml/training/train_all_models.py:154-165`, `ml/models/intensity_predictor.py:37-43`
- **Finding:** In `train_all_models.py`, `det_model` and `cls_model` are saved directly to disk after instantiation without running a training loop. Model D does not even load its checkpoint during inference. A completely black image produces a "CYCLONE CONFIRMED" output with ~0.50 confidence.

### Issue 3: Zero Real Satellite Radiance Data Ingested into Model Training/Inference
- **Severity:** **HIGH**
- **Location:** `scripts/prepare_sample_imagery.py`, `backend/app/services/ml_service.py:30-37`
- **Finding:** The satellite images used for Model A and B inference are synthetically generated NumPy arrays using trigonometric cosine spirals, not genuine satellite observations. Real NASA GIBS tiles are only fetched by the browser for map display, never fed into PyTorch models.

### Issue 4: Multimodal Fusion Pipeline is a Passthrough Copy of Track GRU
- **Severity:** **HIGH**
- **Location:** `ml/models/fusion.py:85-105`
- **Finding:** `fused_track` simply clones `gru_track` waypoints (`fused_lat = round(base_lat, 2)`). The `symmetry_factor = 0.92` variable is declared and unused. Satellite features and trajectory sequences are never jointly embedded into a unified neural representation.

### Issue 5: Uncertainty Cones are Static Heuristics, Not Calibrated Prediction Intervals
- **Severity:** **MEDIUM**
- **Location:** `ml/models/uncertainty.py:22-27`
- **Finding:** Cones are constructed from static hardcoded radii (45, 80, 150 km) rather than calibrated error distributions, quantile loss, or conformal intervals derived from the model's actual historical variance.
