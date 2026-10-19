"""
Model A: Cyclone Detection and Center Localization Network.
PyTorch deep learning model with dual heads:
1. Detection Head: Cyclone Present vs Background (Sigmoid confidence)
2. Localization Head: Center regression (Normalized coordinates [x, y] in [0, 1])
Converts to georeferenced coordinates only when valid bounding box metadata is supplied.
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from typing import Dict, Tuple, Optional

class CycloneDetectorNet(nn.Module):
    def __init__(self):
        super(CycloneDetectorNet, self).__init__()
        # Convolutional feature extractor
        self.conv1 = nn.Conv2d(3, 32, kernel_size=5, stride=2, padding=2) # 256 -> 128
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1) # 128 -> 64
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1) # 64 -> 32
        self.bn3 = nn.BatchNorm2d(128)
        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1) # 32 -> 16
        self.bn4 = nn.BatchNorm2d(256)
        
        self.pool = nn.AdaptiveAvgPool2d((4, 4))
        
        # Detection Head
        self.det_fc1 = nn.Linear(256 * 4 * 4, 128)
        self.det_fc2 = nn.Linear(128, 1)
        
        # Center Localization Head (outputs norm_x, norm_y, eye_radius)
        self.loc_fc1 = nn.Linear(256 * 4 * 4, 128)
        self.loc_fc2 = nn.Linear(128, 3)

    def forward(self, x):
        feat = F.relu(self.bn1(self.conv1(x)))
        feat = F.relu(self.bn2(self.conv2(feat)))
        feat = F.relu(self.bn3(self.conv3(feat)))
        feat = F.relu(self.bn4(self.conv4(feat)))
        pooled = self.pool(feat)
        flat = torch.flatten(pooled, 1)

        # Detection probability
        det_logit = self.det_fc2(F.relu(self.det_fc1(flat)))
        det_prob = torch.sigmoid(det_logit)

        # Localization: sigmoid bounds normalized center [0, 1]
        loc_out = self.loc_fc2(F.relu(self.loc_fc1(flat)))
        norm_center = torch.sigmoid(loc_out[:, :2])
        norm_radius = torch.sigmoid(loc_out[:, 2:]) * 0.2

        return det_prob, norm_center, norm_radius

class CycloneDetectorService:
    def __init__(self, checkpoint_path: Optional[str] = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CycloneDetectorNet().to(self.device)
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
                # Note: Currently detector.pt holds random weights; marked UNTRAINED
                self.is_trained = False
                self.model_status = "UNTRAINED"
            except Exception as e:
                print(f"Failed to load checkpoint: {e}")
                self.model_status = "ERROR"
        self.model.eval()

    def predict_image(self, image_input, bounds: Optional[Dict[str, float]] = None) -> Dict:
        """
        Runs inference on PIL Image or image file path.
        Rejects uniform/blank images and prevents untrained models from fabricating confirmed cyclone detections.
        """
        if isinstance(image_input, str):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            image = Image.fromarray(image_input).convert("RGB")
        else:
            raise ValueError("Unsupported image input type")

        orig_w, orig_h = image.size
        arr = np.array(image, dtype=np.float32)
        img_std = float(np.std(arr))

        # Check for blank / solid-color / uniform image input
        if img_std < 5.0:
            return {
                "cyclone_detected": False,
                "detection_confidence": 0.0,
                "image_dimensions": {"width": orig_w, "height": orig_h},
                "center_pixel": None,
                "estimated_eye_radius_px": 0,
                "georeferenced": False,
                "center_coordinates": None,
                "georeferencing_warning": "Input image is uniform or blank (pixel std < 5.0). No cyclone can be detected.",
                "model_version": "CycloneDetectorNet-v1.0",
                "model_status": self.model_status,
                "device": str(self.device),
                "quality_flag": "REJECTED_BLANK_OR_UNIFORM_INPUT",
                "scientific_disclaimer": "AI detection rejected blank/uniform input. Untrained model will not fabricate detections."
            }

        tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            det_prob, norm_center, norm_radius = self.model(tensor)
            prob = float(det_prob[0, 0].item())
            norm_x = float(norm_center[0, 0].item())
            norm_y = float(norm_center[0, 1].item())
            radius_norm = float(norm_radius[0, 0].item())

        # If model is untrained, do not claim a confirmed meteorological detection
        raw_detected = prob >= 0.5
        detected = raw_detected if self.is_trained else False
        pixel_x = int(round(norm_x * orig_w))
        pixel_y = int(round(norm_y * orig_h))
        radius_px = int(round(radius_norm * min(orig_w, orig_h)))

        # Validate georeferencing
        georeferenced = False
        geo_lat = None
        geo_lon = None
        geo_warning = None

        if bounds and all(k in bounds for k in ['min_lat', 'max_lat', 'min_lon', 'max_lon']):
            min_lat, max_lat = bounds['min_lat'], bounds['max_lat']
            min_lon, max_lon = bounds['min_lon'], bounds['max_lon']
            
            if min_lat < max_lat and min_lon < max_lon:
                geo_lat = round(max_lat - norm_y * (max_lat - min_lat), 2)
                geo_lon = round(min_lon + norm_x * (max_lon - min_lon), 2)
                georeferenced = True
            else:
                geo_warning = "Provided geographic bounding box has invalid extents."
        else:
            geo_warning = "Geographic bounds not supplied with satellite tile; coordinates remain in pixel space."

        quality_flag = "DEMO_UNTRAINED" if not self.is_trained else ("HIGH_CONFIDENCE" if prob > 0.8 else "MODERATE")

        return {
            "cyclone_detected": detected,
            "demo_detected": raw_detected,
            "detection_confidence": round(prob, 4),
            "image_dimensions": {"width": orig_w, "height": orig_h},
            "center_pixel": {"x": pixel_x, "y": pixel_y},
            "estimated_eye_radius_px": radius_px,
            "georeferenced": georeferenced,
            "center_coordinates": {"lat": geo_lat, "lon": geo_lon} if georeferenced else None,
            "georeferencing_warning": geo_warning,
            "model_version": "CycloneDetectorNet-v1.0",
            "model_status": self.model_status,
            "device": str(self.device),
            "quality_flag": quality_flag,
            "scientific_disclaimer": (
                "DEMO_ONLY: Model A weights are currently untrained random initializations. "
                "Center localization and detection probabilities are not validated meteorological predictions."
                if not self.is_trained else "AI structural estimation based on satellite cloud patterns."
            )
        }
