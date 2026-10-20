import os
import sys
import pytest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.preprocessing.ibtracs_parser import haversine_distance_km, calculate_bearing, IBTrACSProcessor
from ml.models.detector import CycloneDetectorService
from ml.models.classifier import CycloneClassifierService
from ml.models.track_predictor import CycloneTrackService
from ml.models.intensity_predictor import IntensityPredictorService
from ml.models.uncertainty import ForecastUncertaintyEngine
from ml.models.fusion import MultiSourceFusionService

def test_haversine_distance():
    # Distance between Mumbai (18.9220, 72.8347) and Chennai (13.0827, 80.2707) is approx 1030 km
    dist = haversine_distance_km(18.9220, 72.8347, 13.0827, 80.2707)
    assert 1000 < dist < 1060

def test_calculate_bearing():
    # Straight North is 0 degrees
    b_north = calculate_bearing(10.0, 80.0, 15.0, 80.0)
    assert abs(b_north - 0.0) < 1.0 or abs(b_north - 360.0) < 1.0
    # Straight East is 90 degrees
    b_east = calculate_bearing(10.0, 80.0, 10.0, 85.0)
    assert abs(b_east - 90.0) < 2.0

def test_storm_level_splitting_zero_leakage():
    processor = IBTrACSProcessor()
    test_storms = ['2023157N12066', '2020136N10087']
    val_storms = ['2024296N15090']
    
    (X_tr, Y_tr), (X_va, Y_va), (X_te, Y_te) = processor.storm_level_split(
        test_storms=test_storms, val_storms=val_storms
    )
    
    assert len(X_tr) > 0
    assert len(X_te) > 0
    assert len(X_va) > 0
    # Sequence shapes: [N, seq_len=4, features=6]
    assert X_tr.shape[1:] == (4, 6)
    assert Y_tr.shape[1:] == (3, 3)

def test_detector_service():
    detector = CycloneDetectorService()
    
    # 1. Test blank/zero image rejection
    blank_img = np.zeros((256, 256, 3), dtype=np.uint8)
    bounds = {"min_lat": 10.0, "max_lat": 20.0, "min_lon": 80.0, "max_lon": 90.0}
    blank_res = detector.predict_image(blank_img, bounds=bounds)
    assert blank_res["cyclone_detected"] is False
    assert blank_res["detection_confidence"] == 0.0
    assert blank_res["quality_flag"] == "REJECTED_BLANK_OR_UNIFORM_INPUT"
    assert blank_res["model_status"] == "UNTRAINED"

    # 2. Test textured/patterned image with features
    np.random.seed(42)
    textured_img = np.random.randint(50, 200, (256, 256, 3), dtype=np.uint8)
    res = detector.predict_image(textured_img, bounds=bounds)
    assert "cyclone_detected" in res
    assert "detection_confidence" in res
    assert res["model_status"] == "UNTRAINED"
    # An untrained model should NOT report a confirmed meteorological detection
    assert res["cyclone_detected"] is False
    assert res["georeferenced"] is True
    assert 10.0 <= res["center_coordinates"]["lat"] <= 20.0
    assert 80.0 <= res["center_coordinates"]["lon"] <= 90.0

def test_classifier_service():
    classifier = CycloneClassifierService()
    
    # 1. Test blank/zero image handling
    blank_img = np.zeros((256, 256, 3), dtype=np.uint8)
    blank_res = classifier.predict_image(blank_img)
    assert blank_res["quality_flag"] == "REJECTED_BLANK_OR_UNIFORM_INPUT"
    assert blank_res["confidence"] == 0.0

    # 2. Test patterned image
    np.random.seed(42)
    textured_img = np.random.randint(50, 200, (256, 256, 3), dtype=np.uint8)
    res = classifier.predict_image(textured_img)
    assert "predicted_class_id" in res
    assert "predicted_stage" in res
    assert "class_probabilities" in res
    assert len(res["class_probabilities"]) == 5
    assert res["model_status"] == "UNTRAINED"
    assert "scientific_disclaimer" in res

def test_track_predictor_service():
    tracker = CycloneTrackService()
    history = [
        {"lat": 18.0, "lon": 65.0, "wind_kts": 80, "pressure_hpa": 965},
        {"lat": 18.5, "lon": 65.2, "wind_kts": 85, "pressure_hpa": 960},
        {"lat": 19.0, "lon": 65.4, "wind_kts": 90, "pressure_hpa": 955},
        {"lat": 19.5, "lon": 65.6, "wind_kts": 95, "pressure_hpa": 950}
    ]
    baseline_out = tracker.predict_baseline_track(history)
    assert len(baseline_out) == 3
    assert baseline_out[0]["lead_time_hours"] == 6
    assert baseline_out[2]["lead_time_hours"] == 24
    
    gru_out = tracker.predict_gru_track(history)
    assert len(gru_out) == 3

def test_intensity_predictor_service():
    intensity_svc = IntensityPredictorService()
    res = intensity_svc.predict_intensity(current_wind_kts=75.0, current_pressure_hpa=972.0)
    
    assert "forecasts" in res
    assert len(res["forecasts"]) == 3
    f6 = res["forecasts"][0]
    assert f6["lead_time_hours"] == 6
    assert f6["predicted_wind_kmh"] == round(f6["predicted_wind_kts"] * 1.852, 1)
    assert f6["wind_interval_80pct"][0] <= f6["predicted_wind_kts"] <= f6["wind_interval_80pct"][1]

def test_uncertainty_cone_generation():
    engine = ForecastUncertaintyEngine()
    waypoints = [
        {"lead_time_hours": 6, "lat": 19.0, "lon": 87.0},
        {"lead_time_hours": 12, "lat": 20.0, "lon": 87.5},
        {"lead_time_hours": 24, "lat": 21.5, "lon": 88.0}
    ]
    cone_80 = engine.generate_cone_polygon(waypoints, "80pct")
    assert len(cone_80) >= 6
    # Coordinates must be valid lat/lon
    for pt in cone_80:
        assert len(pt) == 2
        assert -90 <= pt[0] <= 90
        assert -180 <= pt[1] <= 180

def test_fusion_service():
    fusion = MultiSourceFusionService()
    res = fusion.fuse_and_predict(current_wind_kts=70.0, current_pressure_hpa=975.0)
    assert "fused_track" in res
    assert "uncertainty_cones" in res
    assert "intensity_forecast" in res

def test_calibrated_uncertainty_quantiles():
    engine = ForecastUncertaintyEngine()
    assert engine.IS_CALIBRATED is True
    assert engine.CONE_TYPE == "EMPIRICAL_QUANTILE_RESIDUAL_CALIBRATION"
    # Radii must grow monotonically with lead time
    r6 = engine.CALIBRATED_QUANTILES[6]["r80_km"]
    r12 = engine.CALIBRATED_QUANTILES[12]["r80_km"]
    r24 = engine.CALIBRATED_QUANTILES[24]["r80_km"]
    assert r6 < r12 < r24
    assert 40.0 < r6 < 55.0
    assert 85.0 < r12 < 110.0
    assert 180.0 < r24 < 230.0

def test_satellite_preprocessor():
    from backend.app.services.satellite.satellite_preprocessor import SatellitePreprocessor
    from PIL import Image

    preproc = SatellitePreprocessor(target_size=(256, 256))
    
    # 1. Temporal alignment check
    aligned, delta_h = preproc.verify_temporal_alignment("2023-06-11T12:00:00Z", "2023-06-11T13:30:00Z", max_delta_hours=3.0)
    assert aligned is True
    assert delta_h == 1.5

    misaligned, delta_h2 = preproc.verify_temporal_alignment("2023-06-11T12:00:00Z", "2023-06-11T18:00:00Z", max_delta_hours=3.0)
    assert misaligned is False
    assert delta_h2 == 6.0

    # 2. Planck brightness temperature conversion
    rad = np.array([50.0, 75.0, 100.0], dtype=np.float32)
    tb = preproc.radiance_to_brightness_temp(rad, nu=925.925)
    # Brightness temperature of cold convective cloud tops typically 200 - 320 Kelvin
    assert np.all(tb > 180.0) and np.all(tb < 360.0)

    # 3. Quality screening
    uniform_arr = np.ones((256, 256, 3), dtype=np.float32) * 128.0
    val_res = preproc.validate_image_quality(uniform_arr)
    assert val_res["valid"] is False

def test_risk_service_logic():
    from backend.app.services.risk_service import risk_service

    # Test IMD scale classification
    assert risk_service.classify_imd_intensity(25.0)["code"] == "D"
    assert risk_service.classify_imd_intensity(40.0)["code"] == "CS"
    assert risk_service.classify_imd_intensity(75.0)["code"] == "VSCS"
    assert risk_service.classify_imd_intensity(100.0)["code"] == "ESCS"
    assert risk_service.classify_imd_intensity(135.0)["code"] == "SuCS"

    # Test coastal proximity calculation
    waypoints = [
        {"lead_time_hours": 6, "lat": 19.5, "lon": 85.5},
        {"lead_time_hours": 12, "lat": 19.8, "lon": 85.8}, # Near Puri/Paradip
        {"lead_time_hours": 24, "lat": 20.5, "lon": 86.5}
    ]
    res = risk_service.assess_coastal_risk(waypoints, current_wind_kts=85.0)
    assert "most_exposed_sector" in res
    assert "Puri" in res["most_exposed_sector"]["sector_name"] or "Paradip" in res["most_exposed_sector"]["sector_name"]
    assert res["most_exposed_sector"]["minimum_distance_km"] < 50.0
    assert res["most_exposed_sector"]["proximity_level"] == "CRITICAL_PROXIMITY"

