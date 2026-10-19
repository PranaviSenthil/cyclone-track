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
                "validation_status": "NOT_EVALUATED",
                "real_state": "UNTRAINED_RANDOM_WEIGHTS",
                "architecture": "Deep CNN with Dual Sigmoid Heads (Detection + Normalized Center)",
                "checkpoint": "artifacts/checkpoints/detector.pt",
                "note": "Weights are random initializations. Blank/uniform inputs rejected. Real satellite training scheduled for Phase 4.",
                "supports_georeferencing": True
            },
            {
                "id": "model_b_classifier",
                "name": "Cyclone Structure & Intensity Classifier",
                "type": "Classification",
                "status": "UNTRAINED",
                "validation_status": "NOT_EVALUATED",
                "real_state": "UNTRAINED_RANDOM_WEIGHTS",
                "architecture": "4-Stage ConvNet with Global Average Pooling + Softmax",
                "num_classes": 5,
                "classes": self.classifier.classes,
                "checkpoint": "artifacts/checkpoints/classifier.pt",
                "note": "Weights are random initializations. Real labeled satellite imagery training scheduled for Phase 4."
            },
            {
                "id": "model_c_track_gru",
                "name": "Cyclone Track Sequence Predictor (Deep GRU)",
                "type": "Recurrent Sequence",
                "status": "TRAINED_NOT_VALIDATED",
                "validation_status": "EVALUATED_ON_HOLDOUT",
                "real_state": "TRAINED_UNDERFIT",
                "architecture": "2-Layer GRU (hidden_dim=64) + Multi-Horizon Displacement Heads",
                "horizons": ["+6h", "+12h", "+24h"],
                "checkpoint": "artifacts/checkpoints/track_gru.pt",
                "note": "Trained on 23 sequences. Evaluated on holdout Amphan & Biparjoy: 271.8 km at 24h (underperforms linear motion baseline 58.6 km). Retraining on full IBTrACS archive scheduled for Phase 4."
            },
            {
                "id": "model_d_intensity",
                "name": "Cyclone Intensity Regressor",
                "type": "Regression",
                "status": "UNTRAINED",
                "validation_status": "NOT_EVALUATED",
                "real_state": "PERSISTENCE_BASELINE_ACTIVE",
                "architecture": "Multi-Layer Perceptron (MLP) for Wind (kts) & Pressure (hPa)",
                "horizons": ["+6h", "+12h", "+24h"],
                "checkpoint": "artifacts/checkpoints/intensity.pt",
                "note": "Model D checkpoint is untrained. Active predictions use a verified persistence baseline."
            },
            {
                "id": "model_e_uncertainty",
                "name": "Forecast Uncertainty & Cone Generator",
                "type": "Operational Heuristic",
                "status": "DEMO_ONLY",
                "validation_status": "NOT_EVALUATED",
                "real_state": "OPERATIONAL_HEURISTIC_IMD_BENCHMARK",
                "confidence_levels": ["80%", "95%"],
                "note": "Uses historical IMD/JTWC regional lookup table (45km/80km/150km). Calibrated conformal quantile modeling scheduled for Phase 4.",
                "metrics_supported": ["Cone Polygon Area", "Lead-time Expansion"]
            },
            {
                "id": "model_f_multimodal_fusion",
                "name": "Multi-Source Fusion Pipeline",
                "type": "Multimodal Fusion",
                "status": "DEMO_ONLY",
                "validation_status": "NOT_EVALUATED",
                "real_state": "PROTOTYPE_PIPELINE",
                "sources_fused": ["Satellite Cloud Geometry", "Numerical Track Sequence", "Thermodynamics"],
                "note": "Integration pipeline verified with smoke tests. Full joint training and ablation scheduled for Phase 4 after upstream retraining."
            }
        ]
        return {
            "models": models,
            "device": "CUDA" if torch.cuda.is_available() else "CPU",
            "pytorch_version": torch.__version__,
            "checkpoints_present": all(os.path.exists(os.path.join(ckpts, f)) for f in ["track_gru.pt", "detector.pt", "classifier.pt", "intensity.pt"])
        }

    def get_evaluation_metrics(self) -> Dict:
        eval_path = os.path.join(settings.BASE_DIR, "artifacts", "evaluations", "track_eval.json")
        track_eval = {}
        if os.path.exists(eval_path):
            with open(eval_path) as f:
                track_eval = json.load(f)

        ablation = self.fusion_service.run_benchmark_ablation()

        return {
            "track_evaluation": track_eval,
            "fusion_ablation_study": ablation,
            "training_methodology": "Hold-out storm split (Zero leakage: Tested on unseen Amphan & Biparjoy)",
            "evaluation_date": "2026-10-19"
        }

ml_service = MLService()
