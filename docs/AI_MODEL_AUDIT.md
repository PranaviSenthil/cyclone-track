# CYCLOTRACK — Complete AI Model, Agent & System Audit

**Project:** CYCLOTRACK — AI-Driven Digital Twin for Multi-Source Tropical Cyclone Pattern Analysis & Prediction  
**Problem Statement:** SIH26070 | **Theme:** Disaster Management  
**Audit Date:** October 19, 2026  
**Auditor:** Senior AI/ML Engineer, ML Auditor & Full-Stack Systems Reviewer  
**Audit Standard:** Zero-assumption, empirical source-code inspection, artifact checksum verification, and runtime execution reproduction.

---

## 1. Executive Summary

This audit represents an evidence-based technical inspection of the CYCLOTRACK codebase (`c:\Users\prana\Downloads\cyclotrack`). The objective was to verify whether the claimed AI/ML capabilities, trained model weights, evaluation metrics, and multi-source satellite ingestion pipelines exist in code and execution rather than merely in UI presentation or documentation.

### Core Audit Verdict
The CYCLOTRACK project contains a **well-engineered, highly polished full-stack prototype** with an asynchronous FastAPI backend and a responsive React 19 Leaflet dashboard. However, from an AI/ML and scientific meteorology standpoint:
1. **Only ONE model (Model C — Track GRU) has actually been trained with an optimizer.** It was trained on a tiny dataset of 23 sequences and currently **underperforms a simple linear motion baseline** (271.8 km error vs. 58.6 km at 24 hours).
2. **Three models (Model A — Detector, Model B — Classifier, Model D — Intensity) use untrained, randomly initialized PyTorch weights.** Model D does not even load its checkpoint during inference.
3. **Model E (Uncertainty) and Model F (Fusion) are heuristic/placeholder implementations.** Model E uses static lookup tables for cone radii. Model F contains no neural fusion weights and merely copies the Track GRU coordinates while displaying hardcoded ablation figures.
4. **Reported benchmark performance metrics** (such as 24h error: 122.9 km, wind MAE: 7.1 kts, and structure F1: 0.887) are **static hardcoded strings and floats**, directly contradicting the actual evaluation output recorded in `artifacts/evaluations/track_eval.json`.
5. **No raw, calibrated satellite radiance tensors reach the AI model pipeline.** The sample images used by the vision models are mathematically simulated cosine spirals generated via NumPy; real NASA GIBS satellite tiles are only retrieved directly by the browser for map background display.

---

## 2. Comprehensive Audit of the Six AI Models

### Model A — Cyclone Detection & Center Localization
- **Source File:** [`ml/models/detector.py`](file:///c:/Users/prana/Downloads/cyclotrack/ml/models/detector.py) (`CycloneDetectorNet`, `CycloneDetectorService`)
- **Checkpoint:** `artifacts/checkpoints/detector.pt` (5,776,225 bytes | SHA-256: `eca4493e2cab8efe0da450b8e60936e269e0c0dcbd86faa2437ba5cbbe111a45`)
- **Architecture:** 4-stage convolutional network (32, 64, 128, 256 channels) with adaptive average pooling and two linear heads:
  - Detection head: Linear(4096 -> 128 -> 1) with sigmoid activation.
  - Localization head: Linear(4096 -> 128 -> 3) outputting normalized center `[x, y]` and eye radius.
- **Audit Findings:**
  1. *Training Status:* **UNTRAINED.** In `ml/training/train_all_models.py` lines 140–159, `det_model` is instantiated and immediately saved via `torch.save(det_model.state_dict(), det_ckpt)`. No training loop, loss function, or optimizer steps were ever executed on satellite imagery.
  2. *Inference Behavior:* During empirical testing with `CycloneDetectorService`:
     - An all-black image (`np.zeros((512, 512, 3))`) outputs detection confidence **0.5054** and center **(257, 262)**.
     - An all-white image (`np.ones((512, 512, 3)) * 255`) outputs detection confidence **0.5042** and center **(260, 264)**.
     - Because `prob >= 0.5` is the detection threshold, an uninformative blank canvas is reported as a "CONFIRMED CYCLONE".
  3. *Georeferencing:* Georeferencing logic is mathematically sound (converts normalized `[x, y]` to `[lat, lon]` via linear interpolation using bounding box metadata). However, because `[x, y]` is stuck at ~(0.5, 0.5) from uninitialized weights, the georeferenced coordinates simply point to the exact midpoint of the bounding box.
- **Classification Verdict:** **Implementation exists, training unverified.**

---

### Model B — Convective Structure Classification
- **Source File:** [`ml/models/classifier.py`](file:///c:/Users/prana/Downloads/cyclotrack/ml/models/classifier.py) (`CycloneClassifierNet`, `CycloneClassifierService`)
- **Checkpoint:** `artifacts/checkpoints/classifier.pt` (1,705,845 bytes | SHA-256: `57b4c19cece7de8b2197eef2e0338628f891beda69c716dc1dc73fcedb2a4d4b`)
- **Architecture:** 4-stage ConvNet (32, 64, 128, 256) with MaxPooling, Global Average Pooling, and FC classification head for 5 classes.
- **Audit Findings:**
  1. *Training Status:* **UNTRAINED.** In `train_all_models.py:160`, `cls_model.state_dict()` is saved immediately without any training.
  2. *Inference Behavior:*
     - Tested on Cyclone Biparjoy (Extremely Severe Cyclone): outputs class 0 (Depression) with probability **0.2111**.
     - Tested on a Tropical Depression image: outputs class 0 with probability **0.2109**.
     - Tested on a blank image: outputs class 0 with probability **0.2117**.
     - The output is approximately uniform across all 5 classes (1/5 = 0.20), exactly matching expectations for random linear weights followed by Softmax.
  3. *Reported F1 Score:* The claimed Macro F1 scores (0.842 for satellite-only, 0.887 for fused) originate from static hardcoded dictionary values in `ml/models/fusion.py:149,170`. No evaluation script was ever executed on categorized ground-truth satellite labels.
- **Classification Verdict:** **Implementation exists, training unverified.**

---

### Model C — Cyclone Track Prediction
- **Source File:** [`ml/models/track_predictor.py`](file:///c:/Users/prana/Downloads/cyclotrack/ml/models/track_predictor.py) (`CycloneGRUTrackNet`, `CycloneTrackService`)
- **Checkpoint:** `artifacts/checkpoints/track_gru.pt` (179,039 bytes | SHA-256: `58e68783b275cf966dc31f2bbb7b8f69f1ce443ed2f4b5bf6b729fcb2adcbc8a`)
- **Architecture:** 2-layer Recurrent GRU (`input_dim=6`, `hidden_dim=64`, `dropout=0.1`) with separate displacement heads for +6h, +12h, and +24h lead times.
- **Audit Findings:**
  1. *Training Status:* **GENUINELY TRAINED.** The model was trained for 35 epochs using Adam optimizer (`lr=0.005`) and `MSELoss` on 23 historical sequences derived from Fani, Tauktae, and Mocha.
  2. *Data Leakage Check:* **VERIFIED ZERO LEAKAGE.** The train/validation/test split in `ml/preprocessing/ibtracs_parser.py:151-175` partitions strictly by whole storm identifier (`SID`). Observations of Amphan and Biparjoy are completely held out from training.
  3. *Real Measured Performance vs. Baseline:*
     - In `artifacts/evaluations/track_eval.json`:
       - +6h: Model error = **68.9 km** | Baseline error = **11.6 km**
       - +12h: Model error = **143.4 km** | Baseline error = **24.9 km**
       - +24h: Model error = **271.8 km** | Baseline error = **58.6 km**
     - Due to the small training dataset (only 23 sequences across 3 storms), the neural network is severely underfit and performs **4.6x worse than the simple linear motion baseline** at 24 hours.
  4. *Presentation Discrepancy:* In the dashboard and `fusion.py`, the model error was claimed to be 141.5 km (beating an inflated 182.4 km baseline). This presentation contradicts the real evaluation file.
- **Classification Verdict:** **Trained artifacts found, validation incomplete (model underperforms baseline).**

---

### Model D — Intensity Prediction
- **Source File:** [`ml/models/intensity_predictor.py`](file:///c:/Users/prana/Downloads/cyclotrack/ml/models/intensity_predictor.py) (`IntensityRegressionNet`, `IntensityPredictorService`)
- **Checkpoint:** `artifacts/checkpoints/intensity.pt` (16,037 bytes | SHA-256: `3e088ad36ec2874d1498a59e1de7bbfc466b6f346e8a4c7121fe194532d29480`)
- **Architecture:** 3-layer MLP (`input_dim=6`, `hidden_dim=48`) predicting wind speed and pressure deltas.
- **Audit Findings:**
  1. *Checkpoint Loading Bug:* In `IntensityPredictorService.__init__` (`intensity_predictor.py:37-43`), the constructor accepts `checkpoint_path` but **never calls `load_state_dict()`**. It instantiates a fresh uninitialized network and sets `self.is_trained = False`.
  2. *Training Status:* **UNTRAINED.** `train_all_models.py:162-163` saves random weights without training.
  3. *Reported Performance:* The claimed MAE of **7.1 kts** (vs. 12.6 kts persistence) is a static string literal in `fusion.py:169`. No evaluation against ground truth was performed.
- **Classification Verdict:** **Prototype or heuristic only.**

---

### Model E — Calibrated Forecast Uncertainty
- **Source File:** [`ml/models/uncertainty.py`](file:///c:/Users/prana/Downloads/cyclotrack/ml/models/uncertainty.py) (`ForecastUncertaintyEngine`)
- **Checkpoint:** None (No ML weights).
- **Audit Findings:**
  1. *Methodology:* Uncertainty is not estimated using quantile regression, Gaussian processes, or conformal prediction. Instead, the engine looks up static operational rule-of-thumb radii in `HISTORICAL_ERROR_BENCHMARKS`:
     - 6h: 80% = 45 km | 95% = 75 km
     - 12h: 80% = 80 km | 95% = 135 km
     - 24h: 80% = 150 km | 95% = 250 km
     - 48h: 80% = 280 km | 95% = 460 km
  2. *Evaluation:* `evaluate_calibration()` checks whether simulated forecast errors fall within these static thresholds rather than computing real empirical coverage on holdout storms.
  3. *Conclusion:* The cone of uncertainty is a **geometric visual heuristic**, not a data-driven calibrated prediction interval.
- **Classification Verdict:** **Prototype or heuristic only.**

---

### Model F — Multi-Source Fusion
- **Source File:** [`ml/models/fusion.py`](file:///c:/Users/prana/Downloads/cyclotrack/ml/models/fusion.py) (`MultiSourceFusionService`)
- **Checkpoint:** None (No fusion weights).
- **Audit Findings:**
  1. *Pipeline Inspection:* In `fusion.py:85-105`:
     ```python
     fused_track = []
     for i, pt in enumerate(gru_track):
         ...
         if has_satellite and sat_result["detection"]["cyclone_detected"]:
             symmetry_factor = 0.92
             fused_lat = round(base_lat, 2)
             fused_lon = round(base_lon, 2)
     ```
     `symmetry_factor` is a dead variable. `fused_lat` and `fused_lon` are simply copies of `gru_track`. There is no neural or mathematical fusion taking place between satellite features and trajectory embeddings.
  2. *Ablation Results:* `run_benchmark_ablation()` returns a hardcoded dictionary. No actual comparative ablation experiment was executed.
- **Classification Verdict:** **Placeholder/mock implementation.**

---

## 3. Data Ingestion & Satellite Provenance

### NOAA NCEI IBTrACS
- **Data File:** [`ml/data/historical/ibtracs_north_indian_ocean.csv`](file:///c:/Users/prana/Downloads/cyclotrack/ml/data/historical/ibtracs_north_indian_ocean.csv) (114 rows, 6 storms).
- **Status:** Real, authentic synoptic meteorological observations (latitude, longitude, maximum sustained wind in knots, central pressure in hPa). It is a curated fixture subset rather than the live multi-decadal NOAA archive.
- **Script:** [`scripts/download_ibtracs.py`](file:///c:/Users/prana/Downloads/cyclotrack/scripts/download_ibtracs.py) correctly points to the official NOAA NCEI URL.

### NASA GIBS (Earthdata WMTS)
- **Implementation:** [`backend/app/services/satellite/gibs_adapter.py`](file:///c:/Users/prana/Downloads/cyclotrack/backend/app/services/satellite/gibs_adapter.py).
- **Status:** **Frontend Map Visualization Only.** The adapter correctly formats WMTS tile URLs for layers like `VIIRS_SNPP_CorrectedReflectance_TrueColor` and `AIRS_Precipitation_Day`. The browser downloads these map tiles directly into Leaflet. **No NASA GIBS imagery is downloaded or passed to any AI model.**

### ISRO MOSDAC (INSAT-3D/3DR)
- **Implementation:** [`backend/app/services/satellite/mosdac_adapter.py`](file:///c:/Users/prana/Downloads/cyclotrack/backend/app/services/satellite/mosdac_adapter.py).
- **Status:** **Blocked by Credentials (Honest Reporting).** The adapter reports `CREDENTIALS_REQUIRED`. It does not invent fake endpoints or mock live satellite feeds.

### Benchmark Imagery
- **Data Directory:** `ml/data/sample_imagery/`.
- **Status:** **SYNTHETIC NUMPY ARRAYS.** Generated by [`scripts/prepare_sample_imagery.py`](file:///c:/Users/prana/Downloads/cyclotrack/scripts/prepare_sample_imagery.py) using radial trigonometric cosine equations to simulate cold convective cloud tops. **These are synthetic simulations, not genuine satellite imagery from INSAT or NOAA.**

---

## 4. Test Suite and Build Audit

- **Backend PyTest Suite:** [`backend/tests/`](file:///c:/Users/prana/Downloads/cyclotrack/backend/tests/)
  - Executed: `python -m pytest backend/tests/ -v`
  - Result: **19 passed, 0 failed** in 21.42s.
  - Quality Assessment: The tests verify that endpoints return HTTP 200 and expected JSON keys. However, they are **schema/smoke tests**, not scientific validation tests. For instance, `test_detector_service` passes when fed an all-black dummy array because it only verifies that the key `"cyclone_detected"` is present.
- **Frontend Production Build:** [`frontend/`](file:///c:/Users/prana/Downloads/cyclotrack/frontend/)
  - Executed: `npm run build`
  - Result: **Successfully built in 3.65s** (`dist/assets/index-DXLg7yXE.js` 841 kB).

---

## 5. Summary of Audit Findings by Severity

| ID | Finding | Severity | Status | Location |
| :--- | :--- | :---: | :---: | :--- |
| **F-01** | Benchmark metrics (122.9 km, 7.1 kts, 0.887 F1) are hardcoded literals | **CRITICAL** | FAILED | `fusion.py:138`, `OverviewSection.tsx:65` |
| **F-02** | Models A, B, and D use untrained random weights; Model D does not load weights | **CRITICAL** | FAILED | `train_all_models.py:154`, `intensity_predictor.py:37` |
| **F-03** | Model C (Track GRU) error (271.8 km) underperforms simple baseline (58.6 km) | **HIGH** | VERIFIED | `track_eval.json:15-17` |
| **F-04** | Multimodal fusion is a passthrough copy of Track GRU with no neural fusion | **HIGH** | FAILED | `fusion.py:85-105` |
| **F-05** | Satellite sample imagery is mathematically simulated, not genuine satellite data | **HIGH** | FAILED | `prepare_sample_imagery.py:33` |
| **F-06** | Uncertainty cones are fixed operational radii, not calibrated prediction intervals | **MEDIUM** | PARTIAL | `uncertainty.py:22-27` |
| **F-07** | Unit tests assert schema presence rather than model prediction accuracy | **MEDIUM** | VERIFIED | `backend/tests/test_ml_models.py` |

---

## 6. Concrete Remediation Plan

To convert this prototype into an honest, operational research system:

1. **Remove Hardcoded Metrics:** Update `fusion.py:run_benchmark_ablation` and frontend components to report the actual evaluation output from `track_eval.json` (e.g. baseline 58.6 km vs. GRU 271.8 km) and mark untrained models as `UNTRAINED` or `NOT VALIDATED`.
2. **Expand the Track Training Dataset:** Increase historical storm coverage from 6 storms to the full North Indian Ocean IBTrACS archive (500+ storms from 1980–2024) by running `scripts/download_ibtracs.py`. Retrain Model C so the GRU genuinely learns steering currents and beats the baseline.
3. **Train Model D on Historical Pressure/Wind Drops:** Implement a real training loop in `train_all_models.py` fitting `IntensityRegressionNet` on sequential `[wind, pressure]` deltas, and fix `intensity_predictor.py` to call `self.model.load_state_dict(torch.load(checkpoint_path))`.
4. **Acquire Real Geostationary Infrared Imagery:** Replace synthetic NumPy images in `ml/data/sample_imagery/` with genuine INSAT-3D/3DR or Himawari/INSAT open datasets (e.g., from Kaggle/MOSDAC open portals) and fine-tune Model A and Model B with real labels.
5. **Implement Conformal Uncertainty:** Replace static lookup tables in `uncertainty.py` with conformal prediction intervals derived from validation residuals.
