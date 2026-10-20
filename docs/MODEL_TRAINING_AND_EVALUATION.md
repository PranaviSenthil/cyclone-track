# CYCLOTRACK Model Training and Evaluation Methodology Guide

**Project:** CYCLOTRACK — AI-Driven Digital Twin for Multi-Source Tropical Cyclone Pattern Analysis & Prediction  
**Problem Statement:** SIH26070 | **Team:** MISSION_POSSIBLE  

---

## 1. Problem Formulation

Cyclones in the North Indian Ocean (Arabian Sea and Bay of Bengal) exhibit rapid changes in translation speed and bearing due to complex monsoonal steering currents and topography.

We formulate cyclone track and intensity forecasting as a supervised sequence-to-sequence regression problem:
Given a history of cyclone states over the past 24 hours at 6-hour intervals:
$$\mathbf{X}_{t} = [\mathbf{x}_{t-18}, \mathbf{x}_{t-12}, \mathbf{x}_{t-6}, \mathbf{x}_{t}]$$
where each observation $\mathbf{x}_i \in \mathbb{R}^8$:
$$\mathbf{x}_i = [\text{lat}, \text{lon}, v_{\text{lat}}, v_{\text{lon}}, \text{speed\_kts}, \text{bearing\_deg}, \text{wind\_kts}, \text{pressure\_hpa}]$$

The model predicts future states at three operational horizons:
$$\mathbf{Y}_{t} = [\mathbf{y}_{t+6\text{h}}, \mathbf{y}_{t+12\text{h}}, \mathbf{y}_{t+24\text{h}}]$$

---

## 2. Leakage Prevention and Cross-Validation

Standard random splitting or time-slice splitting across fixes causes catastrophic data leakage because consecutive 6-hour fixes of the same cyclone are strongly autocorrelated.
CYCLOTRACK strictly uses **whole-storm level partitioning**:
- Every cyclone (identified by unique NOAA IBTrACS `SID`) is assigned entirely to either `train`, `val`, or `test`.
- Test set consists of 70 completely held-out cyclones, including high-impact storms such as `AMPHAN (2020)` and `BIPARJOY (2023)`.
- All feature standardizers (means and standard deviations) are computed solely from the `train` split and frozen.

---

## 3. Network Architectures

### 3.1 Model C: Cyclone Track Predictor (CycloneGRUTrackNet)
- **Recurrent Backbone:** 2-layer Gated Recurrent Unit (GRU) with hidden dimension 128 and dropout 0.2.
- **Input Projection:** Maps 8-dimensional feature vectors to GRU input space.
- **Multi-Horizon Forecast Heads:** Fully-connected heads for each forecast horizon (+6h, +12h, +24h), predicting geographic displacement relative to current fix:
  $$(\Delta \text{lat}_{t+h}, \Delta \text{lon}_{t+h})$$
- **Loss Function:** Multi-task MSE on coordinate displacements:
  $$\mathcal{L}_{\text{track}} = \sum_{h \in \{6, 12, 24\}} w_h \|\hat{\Delta}_{t+h} - \Delta_{t+h}\|^2$$

### 3.2 Model D: Cyclone Intensity Predictor (IntensityRegressionNet)
- **Architecture:** MLP with LayerNorm, GELU activations, and residual skip connections.
- **Input:** Recent track dynamics, pressure tendency, translation velocity, and current wind speed.
- **Target:** Absolute maximum sustained wind speed (knots) at +6h, +12h, and +24h.
- **Loss Function:** Smooth L1 loss (Huber loss) robust to extreme intensification outliers.

---

## 4. Meteorological Baseline Benchmarks

In tropical cyclone forecasting, complex deep learning models must be compared against established standard baselines:
1. **Persistence (CLIPER zero-order):** Assumes zero future change from the current observation:
   $$\hat{\mathbf{y}}_{t+h} = \mathbf{x}_t$$
2. **Linear Extrapolation:** Assumes constant forward velocity computed from the previous fix:
   $$\hat{\mathbf{y}}_{t+h} = \mathbf{x}_t + h \cdot \mathbf{v}_t$$

### Skill Score Formulation:
$$\text{Skill}(\%) = \left( 1 - \frac{\text{Error}_{\text{model}}}{\text{Error}_{\text{baseline}}} \right) \times 100$$
A positive skill score indicates true model value above standard operational baselines.

---

## 5. Reproducing Model Training and Evaluation

To reproduce the exact training and evaluation runs from scratch:
```powershell
# 1. Activate environment and run automated training pipeline
python ml/training/train_all_models.py

# 2. Check evaluation outputs
cat artifacts/audit/phase3_evaluation_results.json
cat artifacts/audit/phase3_model_status.json
```
