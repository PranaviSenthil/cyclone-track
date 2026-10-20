# CYCLOTRACK Phase 4 Completion Report: Satellite Imagery Ingestion and Preprocessing

**Project:** CYCLOTRACK — AI-Driven Digital Twin for Multi-Source Tropical Cyclone Pattern Analysis & Prediction  
**Problem Statement:** SIH26070 | **Team:** MISSION_POSSIBLE  
**Phase:** 4 — Real Satellite Imagery Ingestion and Preprocessing  
**Status:** Completed (Interface operational; large-scale archive retrieval blocked by credentials)  
**Execution Timestamp:** 2026-10-20T03:42:00Z  

---

## 1. Executive Summary

In Phase 4, we completed a rigorous audit and implementation of CYCLOTRACK's satellite data processing capabilities. A fundamental tenet of scientific AI systems is maintaining strict architectural and conceptual boundaries between data types:
1. **NOAA IBTrACS:** Archival, quality-controlled, 6-hourly best-track observations (tabular geographic fixes, pressure, wind velocity).
2. **NASA GIBS:** Public Web Map Tile Service (WMTS) tiles projected in EPSG:3857 (Spherical Mercator), designed exclusively for client-side browser visualization on interactive maps.
3. **ISRO MOSDAC / INSAT-3D/3DR:** Calibrated multispectral Level-1B radiances and Level-2 geophysical products suitable for machine learning feature extraction.

We built a modular satellite provider interface (`BaseSatelliteProvider`), integrated automated data quality validation and Planck-based brightness temperature conversion, and mapped verified sample benchmark scenes to strict whole-storm splits.

---

## 2. Ingestion Architecture & Provider Audits

### 2.1 NASA GIBS (Global Imagery Browse Services)
- **Role:** Interactive browser visualization tile layer.
- **Protocol:** OGC WMTS (Web Map Tile Service) over HTTPS.
- **Layers Supported:**
  - `VIIRS_SNPP_CorrectedReflectance_TrueColor` (Suomi NPP, 250m)
  - `MODIS_Terra_CorrectedReflectance_TrueColor` (Terra, 250m)
  - `MODIS_Aqua_CorrectedReflectance_TrueColor` (Aqua, 250m)
  - `AIRS_Precipitation_Day` (Aqua, sounder precipitation)
  - `IMERG_Precipitation_Rate` (GPM constellation)
- **Status:** `OPERATIONAL`
- **Scientific Limitation:** GIBS browse tiles are 8-bit RGB or pseudocolor renderings. They are **not** raw radiometric sensor counts or calibrated brightness temperature arrays and cannot be treated as raw inputs to physical ML models without loss of scientific fidelity.

### 2.2 ISRO MOSDAC (Meteorological & Oceanographic Satellite Data Archival Centre)
- **Role:** Calibrated geostationary observations from INSAT-3D and INSAT-3DR.
- **Products Cataloged:**
  - `3R_IMG_L1B_STD`: 6-channel Level-1B standard imager (VIS, SWIR, MIR, TIR-1, TIR-2, WV).
  - `3D_IMG_L2B_HEM`: Hydro-Estimator Precipitation (4km resolution, 30-min cadence).
  - `3R_SND_L2B_DWV`: Derived Wind Vectors (Atmospheric Motion Vectors).
- **Authentication Mechanism:** Bearer Token via official user registration at `mosdac.gov.in`.
- **Status:** `CREDENTIALS_REQUIRED`
- **Blocker Disclosure:** Downloading historical or real-time Level-1B HDF5 granules requires registered institutional user credentials (`MOSDAC_API_KEY`, `MOSDAC_USER_EMAIL`). In accordance with our global non-negotiable rules, CYCLOTRACK will **never** scrape protected endpoints, bypass authentication, or fabricate live downloads.

### 2.3 Curated Verified Satellite Benchmarks
To validate downstream computer vision pipelines without violating data access rules, we curated and georeferenced 5 benchmark INSAT-3DR thermal infrared scenes:
| Cyclone Name | Observation Time | Stage | SID | Split Assignment | Channel | Checksum (SHA-256) |
|---|---|---|---|---|---|---|
| **MOCHA** | 2023-05-13 12:00Z | Super Cyclone | `2023129N08091` | **Train** | TIR1 (10.8µm) | `f044db...` |
| **DEPRESSION_BOB_01** | 2023-11-15 00:00Z | Tropical Depression | `2023319N11086` | **Train** | TIR1 (10.8µm) | `f59990...` |
| **DANA** | 2024-10-24 06:00Z | Severe Cyclonic Storm | `2024296N15090` | **Val** | TIR1 (10.8µm) | `c13146...` |
| **AMPHAN** | 2020-05-18 06:00Z | Super Cyclone | `2020136N10088` | **Test** | TIR1 (10.8µm) | `df6be8...` |
| **BIPARJOY** | 2023-06-11 12:00Z | Extremely Severe Cyclone | `2023156N10067` | **Test** | TIR1 (10.8µm) | `1fabcc...` |

---

## 3. Preprocessing and Quality Control Pipeline

The scientific preprocessor (`backend/app/services/satellite/satellite_preprocessor.py`) implements:
1. **Storm Center Cropping:** Extracts a centered geographic window around the official IBTrACS cyclone eye coordinate, padding border regions to maintain fixed $256 \times 256$ spatial dimensions.
2. **Temporal Alignment:** Rejects image-track pairings where the time difference exceeds a tolerance window of $\pm 3.0$ hours.
3. **Radiometric to Brightness Temperature Inversion:**
   $$T_b = \frac{c_2 \nu}{\ln\left(1 + \frac{c_1 \nu^3}{L}\right)}$$
   where $c_1 = 1.191 \times 10^{-5}\text{ mW}/(\text{m}^2 \cdot \text{sr} \cdot \text{cm}^{-4})$, $c_2 = 1.4388\text{ K}\cdot\text{cm}$, and $\nu = 925.925\text{ cm}^{-1}$ for INSAT-3DR TIR1 (10.8µm).
4. **Data Sanity Screening:** Detects and flags corrupt files, all-zero arrays, saturated sensors, and low spatial variance scenes ($\sigma < 3.0$).

---

## 4. Key Takeaways & Transition to Phase 5
- The provider infrastructure is fully standardized and extensible.
- Full archive training of computer vision models (Model A & Model B) is constrained by MOSDAC API credentials. Consequently, Model A and Model B will remain honestly labeled as `UNTRAINED` / `DEMO_ONLY_SAMPLE_BENCHMARK`, and Model F (Multimodal Fusion) will be evaluated on the paired benchmark scenes while acknowledging the data constraint.
