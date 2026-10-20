import os
import json
import torch
from typing import Dict, List, Optional
from PIL import Image

from backend.app.config import settings
from ml.models.detector import CycloneDetectorService
from ml.models.classifier import CycloneClassifierService
from ml.models.track_predictor import CycloneTrackService
from ml.models.intensity_predictor import IntensityPredictorService
from ml.models.uncertainty import ForecastUncertaintyEngine
from ml.models.fusion import MultiSourceFusionService
from ml.preprocessing.ibtracs_parser import IBTrACSProcessor

class MLService:
    def __init__(self):
        ckpts = settings.CHECKPOINTS_DIR
        self.detector = CycloneDetectorService(checkpoint_path=os.path.join(ckpts, "detector.pt"))
        self.classifier = CycloneClassifierService(checkpoint_path=os.path.join(ckpts, "classifier.pt"))
        self.track_predictor = CycloneTrackService(checkpoint_path=os.path.join(ckpts, "track_gru.pt"))
        self.intensity_predictor = IntensityPredictorService(checkpoint_path=os.path.join(ckpts, "intensity.pt"))
        self.uncertainty_engine = ForecastUncertaintyEngine()
        self.fusion_service = MultiSourceFusionService()
        self.processor = IBTrACSProcessor(csv_path=settings.HISTORICAL_DATA_PATH)

    def _resolve_image_input(self, sample_id: Optional[str]):
        if sample_id:
            # Check if it's a file in sample_imagery
            sample_path = os.path.join(settings.SAMPLE_IMAGERY_DIR, sample_id)
            if os.path.exists(sample_path):
                return sample_path
        # Fallback to default benchmark sample
        default_sample = os.path.join(settings.SAMPLE_IMAGERY_DIR, "biparjoy_20230611_mature.jpg")
        if os.path.exists(default_sample):
            return default_sample
        return None

    def detect_cyclone(self, sample_id: Optional[str] = None, bounds: Optional[Dict[str, float]] = None) -> Dict:
        image_path = self._resolve_image_input(sample_id)
        if not image_path:
            return {"error": "No valid satellite image available for detection."}
        
        # If bounds not explicitly provided, try reading from sample manifest
        if not bounds and sample_id:
            manifest_path = os.path.join(settings.SAMPLE_IMAGERY_DIR, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    manifest = json.load(f)
                match = next((item for item in manifest if item["filename"] == sample_id), None)
                if match:
                    bounds = match.get("bounds")

        return self.detector.predict_image(image_path, bounds=bounds)

    def classify_structure(self, sample_id: Optional[str] = None) -> Dict:
        image_path = self._resolve_image_input(sample_id)
        if not image_path:
            return {"error": "No valid satellite image available for classification."}
        return self.classifier.predict_image(image_path)

    def predict_future(self, storm_id: Optional[str] = None, trajectory_history: Optional[List[Dict]] = None,
                       sample_image_id: Optional[str] = None, bounds: Optional[Dict[str, float]] = None,
                       current_wind_kts: float = 65.0, current_pressure_hpa: float = 975.0) -> Dict:
        # If storm_id provided, fetch trajectory from IBTrACS
        if storm_id and not trajectory_history:
            history = self.processor.get_storm_trajectory(storm_id)
            if history:
                trajectory_history = history[-8:] # recent 8 synoptic points
                if trajectory_history:
                    current_wind_kts = trajectory_history[-1]["wind_kts"]
                    current_pressure_hpa = trajectory_history[-1]["pressure_hpa"]

        image_path = self._resolve_image_input(sample_image_id) if sample_image_id else None

        return self.fusion_service.fuse_and_predict(
            image_input=image_path,
            bounds=bounds,
            trajectory_history=trajectory_history,
            current_wind_kts=current_wind_kts,
            current_pressure_hpa=current_pressure_hpa
        )

    def get_models_status(self) -> Dict:
        ckpts = settings.CHECKPOINTS_DIR
        models = [
            {
                "id": "model_a_detector",
                "name": "Cyclone Detection & Center Localization (CNN)",
                "type": "Computer Vision",
                "status": "UNTRAINED",
                "validation_status": "DEMO_ONLY_SAMPLE_BENCHMARKS",
                "real_state": "UNTRAINED_AWAITING_MOSDAC_ARCHIVE",
                "architecture": "Deep CNN with Dual Sigmoid Heads (Detection + Normalized Center)",
                "checkpoint": "artifacts/checkpoints/detector.pt",
                "note": "Awaiting large-scale multispectral Level-1B INSAT-3DR archive access from ISRO MOSDAC (currently credentials restricted). Blank/uniform inputs screened.",
                "supports_georeferencing": True
            },
            {
                "id": "model_b_classifier",
                "name": "Cyclone Structure & Intensity Classifier",
                "type": "Classification",
                "status": "UNTRAINED",
                "validation_status": "DEMO_ONLY_SAMPLE_BENCHMARKS",
                "real_state": "UNTRAINED_AWAITING_MOSDAC_ARCHIVE",
                "architecture": "4-Stage ConvNet with Global Average Pooling + Softmax",
                "num_classes": 5,
                "classes": self.classifier.classes,
                "checkpoint": "artifacts/checkpoints/classifier.pt",
                "note": "Awaiting labeled multi-category satellite imagery archive from ISRO MOSDAC."
            },
            {
                "id": "model_c_track_gru",
                "name": "Cyclone Track Sequence Predictor (Deep GRU)",
                "type": "Recurrent Sequence",
                "status": "TRAINED_EVALUATED",
                "validation_status": "GENUINELY_EVALUATED_ON_HOLDOUT",
                "real_state": "TRAINED_EVALUATED",
                "architecture": "2-Layer GRU (hidden_dim=64) + Multi-Horizon Displacement Heads",
                "horizons": ["+6h", "+12h", "+24h"],
                "checkpoint": "artifacts/checkpoints/track_gru.pt",
                "note": "Trained on 8,775 sequences (326 storms). Evaluated on 1,918 independent test sequences (70 held-out storms): 32.0 km (6h), 67.9 km (12h), 148.3 km (24h). Beats linear extrapolation by 9.17% at 24h."
            },
            {
                "id": "model_d_intensity",
                "name": "Cyclone Intensity Regressor",
                "type": "Regression",
                "status": "TRAINED_EVALUATED",
                "validation_status": "GENUINELY_EVALUATED_ON_HOLDOUT",
                "real_state": "TRAINED_EVALUATED",
                "architecture": "Multi-Layer Perceptron (MLP) for Wind (kts) & Pressure (hPa)",
                "horizons": ["+6h", "+12h", "+24h"],
                "checkpoint": "artifacts/checkpoints/intensity.pt",
                "note": "Trained on 8,775 sequences. Evaluated on 1,918 test sequences: MAE 3.01 kts (+6h), 5.14 kts (+12h), 8.73 kts (+24h). Skill score vs persistence at 24h: +6.29%."
            },
            {
                "id": "model_e_uncertainty",
                "name": "Forecast Uncertainty & Cone Generator",
                "type": "Empirical Quantile Conformal Calibration",
                "status": "CALIBRATED_EMPIRICAL_QUANTILES",
                "validation_status": "VERIFIED_ON_TEST_HOLDOUT",
                "real_state": "CALIBRATED_EMPIRICAL_QUANTILES",
                "confidence_levels": ["70%", "80%", "90%"],
                "note": "Empirical quantile radii calibrated on 2,027 validation sequences. Verified on 1,918 test sequences (Coverage: 81.9% at 6h, 79.6% at 12h, 78.1% at 24h for nominal 80%).",
                "metrics_supported": ["Conformal Quantile Radius", "Lead-time Expansion Polygon"]
            },
            {
                "id": "model_f_multimodal_fusion",
                "name": "Multi-Source Fusion Pipeline",
                "type": "Multimodal Fusion",
                "status": "DEMO_ONLY_SAMPLE_PAIRED",
                "validation_status": "DEMO_ONLY_SAMPLE_PAIRED",
                "real_state": "DEMO_ONLY_SAMPLE_PAIRED",
                "sources_fused": ["Satellite Cloud Geometry", "Numerical Track Sequence", "Thermodynamics"],
                "note": "Evaluated on 5 paired benchmark scenes (e.g. AMPHAN, BIPARJOY). Full archive evaluation pending unauthenticated MOSDAC satellite access."
            }
        ]
        return {
            "models": models,
            "device": "CUDA" if torch.cuda.is_available() else "CPU",
            "pytorch_version": torch.__version__,
            "checkpoints_present": all(os.path.exists(os.path.join(ckpts, f)) for f in ["track_gru.pt", "intensity.pt"])
        }

    def get_evaluation_metrics(self) -> Dict:
        eval_path = os.path.join(settings.BASE_DIR, "artifacts", "audit", "phase3_evaluation_results.json")
        phase3_eval = {}
        if os.path.exists(eval_path):
            with open(eval_path) as f:
                phase3_eval = json.load(f)

        uncert_path = os.path.join(settings.BASE_DIR, "artifacts", "audit", "phase6_uncertainty_results.json")
        uncert_eval = {}
        if os.path.exists(uncert_path):
            with open(uncert_path) as f:
                uncert_eval = json.load(f)

        ablation = self.fusion_service.run_benchmark_ablation()

        return {
            "phase3_evaluation_results": phase3_eval,
            "uncertainty_calibration": uncert_eval,
            "fusion_ablation_study": ablation,
            "training_methodology": "Strict whole-cyclone partition (326 train storms, 70 validation storms, 70 test storms; Zero temporal leakage)",
            "evaluation_date": "2026-10-20"
        }

ml_service = MLService()
