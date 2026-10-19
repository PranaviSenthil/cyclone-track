# CYCLOTRACK Baseline Status Report
**Project:** CYCLOTRACK — AI-Driven Digital Twin for Multi-Source Tropical Cyclone Pattern Analysis & Prediction  
**Problem Statement:** SIH26070 | **Team:** MISSION_POSSIBLE  
**Audit & Baseline Timestamp:** October 19, 2026  
**Status:** PHASE 0 COMPLETED — EMPIRICAL BASELINE RECORDED  

---

## 1. Executive Summary & Objective

This document establishes the empirical, reproducible baseline of the CYCLOTRACK system prior to Phase 1 modifications. Every finding recorded herein has been verified through direct inspection of the repository source code, execution of tests, extraction of model checkpoint weights, and evaluation on held-out historical storms.

In accordance with the non-negotiable rules of the project, **no metric, status, or performance claim is fabricated**. Where models are uninitialized, untrained, or unvalidated, they are explicitly designated as such.

---

## 2. Execution Environment & Hardware Inventory

| Component | Verified Specification | Notes |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Build 26200 | PowerShell 5.1 / 7 compatible |
| **CPU Architecture** | 16 Logical Cores (Intel/AMD x86_64) | Full multi-processing support |
| **System Memory (RAM)** | 15.33 GB Total | Sufficient for tabular & batch CNN inference |
| **Hardware Acceleration** | **CUDA Available: False (CPU Only)** | PyTorch `2.10.0+cpu` installed. All training & inference must be CPU-compatible. |
| **Python Runtime** | Python 3.10.0 | Environment packages managed via `requirements.txt` |
| **Node.js Runtime** | Node.js v22.14.0 (npm v10.9.2) | Frontend build toolchain |
| **Frontend Toolchain** | Vite v8.3.4, React 19, TypeScript | Strict typing, Tailwind CSS, Leaflet 1.9.4 |
| **Backend Framework** | FastAPI 0.115.6, Uvicorn, Pydantic v2 | Asynchronous REST API server |

---

## 3. Model Inventory & Artifact Verification

| Model Component | Checkpoint File | Size | SHA256 Hash | Parameter Count | Actual State | Empirical Reality |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Model A: Cyclone Detection** | `artifacts/checkpoints/detector.pt` | 5.77 MB | `eca4493e2cab8efe0da450b8e60936e269e0c0dcbd86faa2437ba5cbbe111a45` | 1,443,459 | **UNTRAINED (Random Weights)** | Initialized from `CycloneDetectorNet` without training. Yields ~0.50 confidence and ~[257, 262] center coordinates on blank/zero arrays. |
| **Model B: Structure Classification** | `artifacts/checkpoints/classifier.pt` | 1.71 MB | `57b4c19cece7de8b2197eef2e0338628f891beda69c716dc1dc73fcedb2a4d4b` | 425,861 | **UNTRAINED (Random Weights)** | Untrained 5-class ConvNet. Outputs near-uniform probabilities (~0.21) regardless of input features. |
| **Model C: Track Prediction** | `artifacts/checkpoints/track_gru.pt` | 179 KB | `58e68783b275cf966dc31f2bbb7b8f69f1ce443ed2f4b5bf6b729fcb2adcbc8a` | 44,484 | **TRAINED (Severely Underfit)** | Trained for 35 epochs on 23 short trajectory sequences. Evaluated holdout error on Amphan & Biparjoy is **271.8 km at 24h**, underperforming the simple linear motion baseline (**58.6 km at 24h**). |
| **Model D: Intensity Prediction** | `artifacts/checkpoints/intensity.pt` | 16 KB | `3e088ad36ec2874d1498a59e1de7bbfc466b6f346e8a4c7121fe194532d29480` | 3,778 | **UNTRAINED / UNLOADED** | `intensity_predictor.py` instantiates the class but never loads the checkpoint weights (`self.is_trained = False`), falling back to a persistence formula. |
| **Model E: Forecast Uncertainty** | *None (Code heuristic)* | N/A | N/A | 0 | **HEURISTIC CONE** | Uses fixed operational radii (45 km at 6h, 80 km at 12h, 150 km at 24h) based on IMD empirical tables; not a calibrated probabilistic/conformal model. |
| **Model F: Multimodal Fusion** | *None (Code wrapper)* | N/A | N/A | 0 | **PLACEHOLDER** | Copies track predictions directly from Model C. Hardcodes ablation metrics (14.8% improvement, 0.887 F1) in `fusion.py`. |

---

## 4. Data Provenance & Ingestion Reality

### 4.1 NOAA IBTrACS Historical Dataset
- **Local Location:** `ml/data/historical/ibtracs_north_indian_ocean.csv`
- **Current Size:** 7,943 bytes (114 records)
- **Storms Included:** 6 historical North Indian Ocean cyclones (`AMPHAN`, `BIPARJOY`, `MOCHA`, `FANI`, `TAUKTAE`, `DANA`).
- **Data Reality:** Genuine historical observations, but the sample size is currently too small (only 23 train sequences) for machine learning sequence models to generalize beyond simple persistence.
- **Pipeline Need:** An automated download and curation script to pull the official full NIO basin dataset (~1,500+ storm fixes).

### 4.2 NASA GIBS Satellite Imagery Integration
- **Service Integration:** Web Map Tile Service (WMTS) EPSG:3857 Tile Protocol in Leaflet (`InteractiveMapSection.tsx`).
- **Data Reality:** Genuinely renders live/historical cloud layers (`MODIS_Terra_CorrectedReflectance_TrueColor`, `VIIRS_SNPP_CorrectedReflectance_TrueColor`, `AIRS_Precipitation_Day`) in the browser map.
- **Limitation:** Visual raster tiles rendered in DOM only; no server-side scientific raster or tensor ingestion pipeline currently feeds satellite imagery into PyTorch models.

### 4.3 ISRO MOSDAC / INSAT-3D/3DR
- **Status:** `BLOCKED_BY_CREDENTIALS` / `CREDENTIALS_REQUIRED`.
- **Data Reality:** Official ISRO MOSDAC OpenData API requires user API keys. In accordance with Rule 9 & Rule 12, the adapter gracefully falls back to explicit status reporting rather than fabricating imagery.

### 4.4 Synthetic Imagery Generator
- **Location:** `ml/data/sample_imagery/` (5 files) and `ml/data/synthetic_generator.py`.
- **Data Reality:** Synthetic 2D NumPy arrays generated using parametric cosine spirals. These are used for UI layout testing and pipeline verification, but must never be presented as real satellite validation data.

---

## 5. Software Architecture & API Surface

### 5.1 Backend REST API (`http://127.0.0.1:8000`)
The FastAPI backend is fully operational with 12 distinct endpoints across 5 routers:
1. `GET /api/health`: Process health and API status.
2. `GET /api/data/sources`: Provider connectivity, operational state, and provenance.
3. `GET /api/satellite/available`: Catalog of NASA GIBS layers and resolution metadata.
4. `GET /api/satellite/latest`: Latest cataloged satellite observation metadata.
5. `GET /api/cyclones/active`: Basin real-time active storm status (currently 0 active storms).
6. `GET /api/cyclones/historical`: Catalog of historical North Indian Ocean storms with track summaries.
7. `GET /api/cyclones/{storm_id}`: High-resolution synoptic trajectory and wind history.
8. `POST /api/detect`: Storm center localization service (currently running random weights).
9. `POST /api/classify`: Convective structure classification service (currently running random weights).
10. `POST /api/predict`: Multi-horizon trajectory and intensity forecast service.
11. `GET /api/models/status`: Readiness, checkpoint presence, and training status.
12. `GET /api/models/metrics`: Model evaluation metrics, holdout validation scores, and ablation matrix.

### 5.2 Frontend Single-Page Application (`http://127.0.0.1:5173`)
The React 19 dashboard has 9 verified functional sections:
- `OverviewSection.tsx`: System KPI summary, active alerts, multi-basin map preview.
- `InteractiveMapSection.tsx`: Leaflet map with GIBS WMS layers, IBTrACS historical tracks, forecast cones.
- `SatelliteExplorerSection.tsx`: NASA GIBS multi-spectral layer viewer with date scrubber.
- `AIVisionSection.tsx`: Center localization and convective structure inspection interface.
- `TrackIntensitySection.tsx`: Multi-horizon track error curves, intensity time-series charts.
- `MultiSourceFusionSection.tsx`: Multi-modal ablation matrix and feature attribution bars.
- `HistoricalArchiveSection.tsx`: Synoptic drill-down for Amphan, Biparjoy, Fani, Mocha, etc.
- `RiskImpactSection.tsx`: Coastal exposure modeling, population risk index, early warning bulletins.
- `ModelReadinessSection.tsx`: Component architecture, checkpoint status, and training metadata.

---

## 6. Baseline Verification Results

### 6.1 Pytest Backend Suite
- **Command:** `python -m pytest backend/tests/ -v`
- **Result:** **19 Passed, 0 Failed** (Execution time: 21.4s).
- **Audit Assessment:** Tests verify API contract shapes and non-crashing execution. They currently do not assert strict meteorological bounds (e.g., passing a zero array into the detector returns 200 OK without asserting that confidence should be near zero).

### 6.2 Frontend Production Build
- **Command:** `npm run build` in `frontend/`
- **Result:** **Built successfully in 3.65s**.
- **Bundle Footprint:** `index.html` (1.29 kB), CSS (40.59 kB), JS (841.40 kB). No syntax or TypeScript compilation errors.

---

## 7. Known Discrepancies & Phase 1 Target Corrections

| Location | Hardcoded / Misleading Claim | Empirical Truth | Phase 1 Correction Action |
| :--- | :--- | :--- | :--- |
| `backend/app/services/ml_service.py` | Track 24h Error = 122.9 km | Evaluated GRU error is 271.8 km; Linear baseline is 58.6 km. | Expose actual evaluated metrics from `track_eval.json` with explicit sample sizes. |
| `backend/app/services/ml_service.py` | Wind MAE = 7.1 knots, Pressure MAE = 5.2 hPa | Model D weights are not loaded; predictions use persistence. | Label as `NOT_EVALUATED` / `PERSISTENCE_BASELINE`. |
| `backend/app/services/ml_service.py` | Structure F1 = 0.887 | Model B has untrained random weights. | Label as `UNTRAINED` / `NOT_EVALUATED`. |
| `ml/models/fusion.py` | Fusion improves track error by 14.8% | Fusion code currently copies GRU track output. | Display `UNVERIFIED` / `DEMO_ONLY` until real fusion is trained. |
| `ml/models/detector.py` | Blank image generates cyclone detection | Random weights generate ~0.50 confidence. | Add input validation and minimum variance check; return `NO_CYCLONE_DETECTED` on uniform/blank images. |
| `frontend/src/components/*` | Displaying hardcoded benchmark numbers | UI templates render static mock constants. | Wire UI directly to backend status and display honest status badges (`UNTRAINED`, `VALIDATED_ON_HOLDOUT`, `DEMO_ONLY`). |

---

## 8. Conclusion & Sign-Off

The baseline has been thoroughly audited and documented. The infrastructure is robust and runnable, the dashboard design is functional and rich, and the codebase is completely transparent. We are ready to proceed with Phase 1 to enforce rigorous honesty across all APIs and UI components.
