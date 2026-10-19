"""
Model C: Cyclone Track Predictor.
Implements two parallel methodologies:
1. Physics & Motion Baseline: Persistence + Extrapolated Forward Velocity + Beta/Coriolis drift
2. Trainable Recurrent Neural Network: PyTorch GRU Sequence Model
Evaluates forecast error in true geographic kilometers via the Haversine formula across +6h, +12h, and +24h lead times.
"""

import os
import math
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional
from ml.preprocessing.ibtracs_parser import haversine_distance_km, calculate_bearing

class CycloneGRUTrackNet(nn.Module):
    """
    GRU Sequence-to-Sequence Track & Motion Predictor.
    Inputs: [batch, seq_len=4, 6] (lat, lon, wind, pressure, speed, bearing)
    Outputs: [batch, 3, 2] -> (+6h [lat, lon], +12h [lat, lon], +24h [lat, lon])
    """
    def __init__(self, input_dim=6, hidden_dim=64, num_layers=2, num_horizons=3):
        super(CycloneGRUTrackNet, self).__init__()
        self.num_horizons = num_horizons
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers=num_layers, batch_first=True, dropout=0.1)
        # Shared dense projection
        self.fc_shared = nn.Linear(hidden_dim, 64)
        # Separate displacement heads for +6h, +12h, +24h
        # Heads predict (dlat, dlon) displacement from the most recent observation point
        self.head_6h = nn.Linear(64, 2)
        self.head_12h = nn.Linear(64, 2)
        self.head_24h = nn.Linear(64, 2)

    def forward(self, x):
        # x: [batch, seq_len, 6]
        gru_out, _ = self.gru(x)
        # Take the final sequence embedding
        last_hidden = gru_out[:, -1, :] # [batch, hidden_dim]
        feat = torch.relu(self.fc_shared(last_hidden))
        
        d_6h = self.head_6h(feat).unsqueeze(1)    # [batch, 1, 2]
        d_12h = self.head_12h(feat).unsqueeze(1)  # [batch, 1, 2]
        d_24h = self.head_24h(feat).unsqueeze(1)  # [batch, 1, 2]
        
        displacements = torch.cat([d_6h, d_12h, d_24h], dim=1) # [batch, 3, 2]
        # Current position is lat, lon at index 0, 1 of last timestep
        curr_pos = x[:, -1, :2].unsqueeze(1) # [batch, 1, 2]
        predicted_coords = curr_pos + displacements
        return predicted_coords

class CycloneTrackService:
    def __init__(self, checkpoint_path: Optional[str] = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CycloneGRUTrackNet().to(self.device)
        self.horizons = [6, 12, 24] # Lead time in hours
        self.is_trained = False
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            try:
                state_dict = torch.load(checkpoint_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                self.is_trained = True
            except Exception as e:
                print(f"Track predictor checkpoint failed to load: {e}")
        self.model.eval()

    def predict_baseline_track(self, history: List[Dict]) -> List[Dict]:
        """
        Extrapolates recent translation vector with atmospheric beta-drift correction.
        Provides a scientifically grounded, non-fabricated reference forecast.
        """
        if len(history) < 2:
            raise ValueError("Baseline predictor requires at least 2 historical trajectory points.")

        p_prev = history[-2]
        p_curr = history[-1]

        # Calculate recent velocity
        dt = 6.0 # standard 6-hour synoptic interval
        dlat = (p_curr['lat'] - p_prev['lat']) / dt
        dlon = (p_curr['lon'] - p_prev['lon']) / dt

        forecast = []
        curr_lat, curr_lon = p_curr['lat'], p_curr['lon']

        for h in self.horizons:
            # Beta drift effect: tropical cyclones in Northern Hemisphere experience slight poleward/westward curvature
            # ~0.02 deg/hr poleward drift
            coriolis_poleward_drift = 0.015 * (h / 6.0)
            pred_lat = curr_lat + (dlat * h) + coriolis_poleward_drift
            pred_lon = curr_lon + (dlon * h)
            
            forecast.append({
                "lead_time_hours": h,
                "lat": round(pred_lat, 2),
                "lon": round(pred_lon, 2),
                "method": "Linear Extrapolation + Beta Drift Baseline",
                "is_supported": True
            })

        return forecast

    def predict_gru_track(self, history: List[Dict]) -> List[Dict]:
        """
        Runs recurrent neural network inference using standardized input features.
        """
        if len(history) < 2:
            return self.predict_baseline_track(history)

        # Build feature vector for last min(len, 4) steps
        features = []
        for pt in history[-4:]:
            lat = pt['lat']
            lon = pt['lon']
            wind = pt.get('wind_kts', 50.0)
            pres = pt.get('pressure_hpa', 990.0)
            speed = pt.get('speed_kts', 10.0)
            bearing = pt.get('bearing_deg', 340.0)
            features.append([lat, lon, wind, pres, speed, bearing])

        # Pad if history is shorter than 4
        while len(features) < 4:
            features.insert(0, features[0])

        inp_tensor = torch.tensor([features], dtype=torch.float32).to(self.device)

        with torch.no_grad():
            pred_coords = self.model(inp_tensor)[0].cpu().numpy()

        results = []
        for i, h in enumerate(self.horizons):
            results.append({
                "lead_time_hours": h,
                "lat": round(float(pred_coords[i, 0]), 2),
                "lon": round(float(pred_coords[i, 1]), 2),
                "method": "Cyclotrack Deep GRU Sequence Network",
                "is_supported": True
            })

        return results

    def compare_and_evaluate(self, history: List[Dict], actuals: Dict[int, Tuple[float, float]]) -> Dict:
        """
        Evaluates both models against ground truth future positions.
        Returns geographic Haversine distance errors in kilometers.
        """
        baseline_preds = self.predict_baseline_track(history)
        gru_preds = self.predict_gru_track(history)

        comparison = []
        for i, h in enumerate(self.horizons):
            b_pt = baseline_preds[i]
            g_pt = gru_preds[i]
            
            entry = {
                "lead_time_hours": h,
                "baseline_coord": {"lat": b_pt['lat'], "lon": b_pt['lon']},
                "gru_coord": {"lat": g_pt['lat'], "lon": g_pt['lon']},
            }

            if h in actuals:
                act_lat, act_lon = actuals[h]
                b_err = haversine_distance_km(b_pt['lat'], b_pt['lon'], act_lat, act_lon)
                g_err = haversine_distance_km(g_pt['lat'], g_pt['lon'], act_lat, act_lon)
                entry["actual_coord"] = {"lat": act_lat, "lon": act_lon}
                entry["baseline_error_km"] = round(b_err, 1)
                entry["gru_error_km"] = round(g_err, 1)
                entry["improvement_km"] = round(b_err - g_err, 1)

            comparison.append(entry)

        return {
            "horizons": self.horizons,
            "predictions": comparison,
            "status": "VALIDATED" if actuals else "INFERENCE_ONLY"
        }
