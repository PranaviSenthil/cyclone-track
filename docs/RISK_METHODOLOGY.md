# CYCLOTRACK Risk Assessment and Uncertainty Calibration Methodology

**Project:** CYCLOTRACK — AI-Driven Digital Twin for Multi-Source Tropical Cyclone Pattern Analysis & Prediction  
**Problem Statement:** SIH26070 | **Team:** MISSION_POSSIBLE  

---

## 1. Conformal Empirical Quantile Uncertainty Calibration

Standard cone-of-uncertainty implementations in research prototypes frequently use static, handpicked circular radii. CYCLOTRACK calibrates track uncertainty empirically from holdout validation residuals:

### Mathematical Formulation
Given the trained recurrent model $f_\theta(\mathbf{X})$ and validation storm ground truth coordinates $\mathbf{Y}_v$:
For each forecast horizon $h \in \{6, 12, 24\}$, compute geodesic error residuals:
$$e_{i, h} = \text{Haversine}(\hat{\mathbf{y}}_{i, h}, \mathbf{y}_{i, h}), \quad i \in \{1, \dots, N_{\text{val}}\}$$
The empirical quantile radius for confidence level $1 - \alpha$ is:
$$r_{1-\alpha, h} = \text{Quantile}(e_h, 1-\alpha)$$

For a confidence level of $\alpha = 0.20$ (80% confidence interval):
$$P\left(\text{Haversine}(\hat{\mathbf{y}}_{\text{test}, h}, \mathbf{y}_{\text{test}, h}) \le r_{0.80, h}\right) \approx 0.80$$

Empirical testing on 1,918 independent test fixes confirmed observed coverages of:
- 6h: 81.86% (vs 80% nominal)
- 12h: 79.61% (vs 80% nominal)
- 24h: 78.10% (vs 80% nominal)

---

## 2. Coastal Proximity and Exposure Modeling

Located at: `backend/app/services/risk_service.py`

### Distance Thresholds:
- **$\le 75\text{ km}$ — Critical Proximity:** Immediate hurricane/gale-force wind threat. High risk of severe structural and infrastructure disruption.
- **$75 - 150\text{ km}$ — High Proximity:** Outer core spiral bands. Squally winds, intense rainfall bursts, rough seas.
- **$150 - 300\text{ km}$ — Moderate Proximity:** Peripheral squalls and high swells. Coastal monitoring recommended.
- **$> 300\text{ km}$ — Low Proximity:** No direct storm impact anticipated within current forecast horizon.

### IMD Scale Classification:
Wind speeds are mapped directly to India Meteorological Department categories:
- Depressions (17–27 kts) & Deep Depressions (28–33 kts)
- Cyclonic Storms (34–47 kts)
- Severe Cyclonic Storms (48–63 kts)
- Very Severe Cyclonic Storms (64–89 kts)
- Extremely Severe Cyclonic Storms (90–119 kts)
- Super Cyclonic Storms ($\ge 120\text{ kts}$)

---

## 3. Disclaimers and Institutional Boundaries

1. **No Unvalidated Hazard Claims:** CYCLOTRACK does not claim hydrodynamic storm-surge inundation or inland flood modeling without high-resolution bathymetry and hydrological models.
2. **Authority Recognition:** The system prominently alerts users that official warnings and evacuation directives remain the exclusive domain of the India Meteorological Department (IMD / RSMC New Delhi) and the National Disaster Management Authority (NDMA).
