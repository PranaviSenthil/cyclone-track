"""
Model B: Cyclone Structure and Intensity Stage Classifier.
Categorizes cyclone satellite imagery into meteorological stages:
0: Tropical Depression / Deep Depression (< 34 kts)
1: Cyclonic Storm (34 - 47 kts)
2: Severe Cyclonic Storm (48 - 63 kts)
3: Very Severe Cyclonic Storm (64 - 89 kts)
4: Extremely Severe / Super Cyclone (>= 90 kts)
Computes class probabilities, entropy/out-of-distribution flags, and macro F1 metrics.
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from typing import Dict, List, Optional
from sklearn.metrics import classification_report, confusion_matrix, f1_score

CLASSES = [
    "Depression / Deep Depression (<34 kts)",
    "Cyclonic Storm (34-47 kts)",
    "Severe Cyclonic Storm (48-63 kts)",
    "Very Severe Cyclonic Storm (64-89 kts)",
    "Extremely Severe / Super Cyclone (>=90 kts)"
]

class CycloneClassifierNet(nn.Module):
    def __init__(self, num_classes=5):
        super(CycloneClassifierNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.pool1 = nn.MaxPool2d(2, 2) # 256 -> 128
        
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.pool2 = nn.MaxPool2d(2, 2) # 128 -> 64
        
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.pool3 = nn.MaxPool2d(2, 2) # 64 -> 32
        
        self.conv4 = nn.Conv2d(128, 256, 3, padding=1)
        self.bn4 = nn.BatchNorm2d(256)
        self.pool4 = nn.MaxPool2d(2, 2) # 32 -> 16
        
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc1 = nn.Linear(256, 128)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.pool1(F.relu(self.bn1(self.conv1(x))))
        x = self.pool2(F.relu(self.bn2(self.conv2(x))))
        x = self.pool3(F.relu(self.bn3(self.conv3(x))))
        x = self.pool4(F.relu(self.bn4(self.conv4(x))))
        
        feat = self.global_pool(x)
        feat = torch.flatten(feat, 1)
        
        x = F.relu(self.fc1(feat))
        x = self.dropout(x)
        logits = self.fc2(x)
        return logits, feat

class CycloneClassifierService:
    def __init__(self, checkpoint_path: Optional[str] = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CycloneClassifierNet().to(self.device)
        self.classes = CLASSES
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # Checkpoint contains uninitialized / random weights until Phase 4 training
        self.is_trained = False
        self.model_status = "UNTRAINED"
        if checkpoint_path and os.path.exists(checkpoint_path):
            try:
                state_dict = torch.load(checkpoint_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.is_trained = False
                self.model_status = "UNTRAINED"
            except Exception as e:
                print(f"Classifier checkpoint failed to load: {e}")
                self.model_status = "ERROR"
        self.model.eval()

    def predict_image(self, image_input) -> Dict:
        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            image = Image.fromarray(image_input).convert("RGB")
        else:
            raise ValueError("Unsupported image input type")

        arr = np.array(image, dtype=np.float32)
        img_std = float(np.std(arr))

        # Check for blank / solid-color image
        if img_std < 5.0:
            return {
                "predicted_class_id": -1,
                "predicted_stage": "Indeterminate (Blank / Uniform Input)",
                "confidence": 0.0,
                "class_probabilities": [
                    {"class_id": i, "label": self.classes[i], "probability": 0.0}
                    for i in range(len(self.classes))
                ],
                "uncertainty_entropy": 1.0,
                "out_of_distribution_warning": True,
                "scientific_disclaimer": "AI structural classification rejected blank/uniform input. Untrained model will not fabricate predictions.",
                "feature_vector_dim": 256,
                "model_version": "CycloneClassifierNet-v1.0",
                "model_status": self.model_status,
                "quality_flag": "REJECTED_BLANK_OR_UNIFORM_INPUT"
            }

        tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits, features = self.model(tensor)
            probs = F.softmax(logits, dim=1)[0].cpu().numpy()

        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])
        
        # Calculate Shannon entropy as measure of uncertainty / OOD
        entropy = float(-np.sum(probs * np.log(np.maximum(probs, 1e-7))))
        # Max entropy for 5 classes is ln(5) = 1.609
        normalized_entropy = entropy / 1.609
        ood_warning = normalized_entropy > 0.85

        prob_breakdown = [
            {"class_id": i, "label": self.classes[i], "probability": round(float(probs[i]), 4)}
            for i in range(len(self.classes))
        ]

        quality_flag = "DEMO_UNTRAINED" if not self.is_trained else ("HIGH_CONFIDENCE" if confidence > 0.7 else "MODERATE")

        return {
            "predicted_class_id": pred_idx,
            "predicted_stage": self.classes[pred_idx] if self.is_trained else f"Demo Stage ({self.classes[pred_idx]})",
            "confidence": round(confidence, 4),
            "class_probabilities": prob_breakdown,
            "uncertainty_entropy": round(normalized_entropy, 3),
            "out_of_distribution_warning": ood_warning,
            "scientific_disclaimer": (
                "DEMO_ONLY: Model B weights are currently untrained random initializations. "
                "Class probabilities are heuristic outputs and not validated meteorological classifications."
                if not self.is_trained else "AI structural estimation based on satellite cloud patterns. Not an official IMD bulletin."
            ),
            "feature_vector_dim": features.shape[1],
            "model_version": "CycloneClassifierNet-v1.0",
            "model_status": self.model_status,
            "quality_flag": quality_flag
        }

    def evaluate_dataset(self, y_true: List[int], y_pred: List[int]) -> Dict:
        """Evaluates predictions on validation set and computes confusion matrix and macro F1."""
        if not y_true or not y_pred:
            return {
                "status": "NOT_EVALUATED",
                "macro_f1": "NOT_EVALUATED",
                "confusion_matrix": [],
                "classes": self.classes,
                "note": "Model B has not been evaluated on holdout satellite imagery."
            }
        f1 = float(f1_score(y_true, y_pred, average='macro', zero_division=0))
        cm = confusion_matrix(y_true, y_pred, labels=list(range(len(self.classes)))).tolist()
        report = classification_report(y_true, y_pred, target_names=self.classes, output_dict=True, zero_division=0)
        return {
            "macro_f1": round(f1, 4),
            "confusion_matrix": cm,
            "classes": self.classes,
            "detailed_report": report
        }
