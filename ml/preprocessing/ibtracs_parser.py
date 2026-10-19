"""
IBTrACS Historical Cyclone Data Parser and Preprocessing Pipeline.
Guarantees storm-level splits (no data leakage across adjacent observations of same storm).
Calculates haversine distance, forward speed, translation bearing, and standardized features.
"""

import os
import json
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points on the earth in kilometers."""
    R = 6371.0 # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates initial bearing (azimuth in degrees 0-360) from point 1 to point 2."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlon_r = math.radians(lon2 - lon1)
    x = math.sin(dlon_r) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - (math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    return (initial_bearing + 360) % 360

LEGACY_SID_ALIASES: Dict[str, str] = {
    "2020136N10087": "2020136N10088", # AMPHAN
    "2023157N12066": "2023156N10067", # BIPARJOY
    "2023130N08092": "2023129N08091", # MOCHA
    "2019117N02086": "2019116N02090", # FANI
    "2021134N10072": "2021133N10071", # TAUKTAE
    "2024296N15090": "2024295N15092", # DANA
}

class IBTrACSProcessor:
    def __init__(self, csv_path: Optional[str] = None):
        if csv_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            modern_path = os.path.join(base_dir, "data", "processed", "ibtracs", "ibtracs_ni_modern.csv")
            historical_path = os.path.join(base_dir, "data", "historical", "ibtracs_north_indian_ocean.csv")
            if os.path.exists(modern_path):
                csv_path = modern_path
            else:
                csv_path = historical_path
        self.csv_path = csv_path
        self.raw_df = None
        self.cleaned_df = None

    def load_and_clean(self) -> pd.DataFrame:
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Dataset not found at {self.csv_path}")

        # Check if line 1 contains units (official raw NOAA IBTrACS format)
        skiprows = None
        with open(self.csv_path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
            second_line = f.readline()
            if any(u in second_line for u in ["kts", "mb", "Year", "degrees_north"]):
                skiprows = [1]

        df = pd.read_csv(self.csv_path, skiprows=skiprows, low_memory=False)
        # Standardize column names
        df.columns = [c.strip().upper() for c in df.columns]

        # Convert types & clean coordinates
        df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
        df['LON'] = pd.to_numeric(df['LON'], errors='coerce')
        df['ISO_TIME'] = pd.to_datetime(df['ISO_TIME'], errors='coerce')

        # Drop invalid coordinates or timestamps
        df = df.dropna(subset=['LAT', 'LON', 'ISO_TIME', 'SID'])
        coord_valid = (df['LAT'] >= -90) & (df['LAT'] <= 90) & (df['LON'] >= -180) & (df['LON'] <= 180)
        df = df[coord_valid].copy()

        # Handle consensus wind speed & pressure
        # Check priority: BEST_WIND_KTS -> NEWDELHI/IMD -> WMO -> USA
        if 'BEST_WIND_KTS' in df.columns and df['BEST_WIND_KTS'].notna().any():
            best_wind = pd.to_numeric(df['BEST_WIND_KTS'], errors='coerce')
        else:
            wmo_wind = pd.to_numeric(df['WMO_WIND'], errors='coerce') if 'WMO_WIND' in df.columns else pd.Series(np.nan, index=df.index, dtype=float)
            imd_col = 'NEWDELHI_WIND' if 'NEWDELHI_WIND' in df.columns else ('IMD_WIND' if 'IMD_WIND' in df.columns else None)
            imd_wind = pd.to_numeric(df[imd_col], errors='coerce') if imd_col else pd.Series(np.nan, index=df.index, dtype=float)
            usa_wind = pd.to_numeric(df['USA_WIND'], errors='coerce') if 'USA_WIND' in df.columns else pd.Series(np.nan, index=df.index, dtype=float)
            best_wind = imd_wind.combine_first(wmo_wind).combine_first(usa_wind)

        if 'BEST_PRES_HPA' in df.columns and df['BEST_PRES_HPA'].notna().any():
            best_pres = pd.to_numeric(df['BEST_PRES_HPA'], errors='coerce')
        else:
            wmo_pres = pd.to_numeric(df['WMO_PRES'], errors='coerce') if 'WMO_PRES' in df.columns else pd.Series(np.nan, index=df.index, dtype=float)
            imd_p_col = 'NEWDELHI_PRES' if 'NEWDELHI_PRES' in df.columns else ('IMD_PRES' if 'IMD_PRES' in df.columns else None)
            imd_pres = pd.to_numeric(df[imd_p_col], errors='coerce') if imd_p_col else pd.Series(np.nan, index=df.index, dtype=float)
            usa_pres = pd.to_numeric(df['USA_PRES'], errors='coerce') if 'USA_PRES' in df.columns else pd.Series(np.nan, index=df.index, dtype=float)
            best_pres = imd_pres.combine_first(wmo_pres).combine_first(usa_pres)

        df['WMO_WIND'] = best_wind
        df['WMO_PRES'] = best_pres

        # Deduplicate exact storm observation timestamps
        df = df.drop_duplicates(subset=['SID', 'ISO_TIME'], keep='first')

        # Sort chronologically within each storm
        df = df.sort_values(by=['SID', 'ISO_TIME']).reset_index(drop=True)

        # Impute missing wind / pressure where missing per storm
        df['WMO_WIND'] = df.groupby('SID')['WMO_WIND'].ffill().bfill().fillna(35.0)
        df['WMO_PRES'] = df.groupby('SID')['WMO_PRES'].ffill().bfill().fillna(1000.0)

        # Forward speed and azimuth direction
        if 'SPEED_KTS' in df.columns and 'BEARING_DEG' in df.columns and df['SPEED_KTS'].notna().any():
            df['SPEED_KTS'] = pd.to_numeric(df['SPEED_KTS'], errors='coerce').fillna(8.0)
            df['BEARING_DEG'] = pd.to_numeric(df['BEARING_DEG'], errors='coerce').fillna(0.0)
        else:
            computed_speeds = []
            computed_dirs = []
            for sid, group in df.groupby('SID'):
                group_records = group.to_dict('records')
                for i in range(len(group_records)):
                    if i == 0:
                        speed = group_records[i].get('STORM_SPEED', 8.0)
                        direction = group_records[i].get('STORM_DIR', 0.0)
                    else:
                        prev = group_records[i - 1]
                        curr = group_records[i]
                        dt_hours = max((curr['ISO_TIME'] - prev['ISO_TIME']).total_seconds() / 3600.0, 0.1)
                        dist_km = haversine_distance_km(prev['LAT'], prev['LON'], curr['LAT'], curr['LON'])
                        speed = (dist_km / dt_hours) / 1.852
                        direction = calculate_bearing(prev['LAT'], prev['LON'], curr['LAT'], curr['LON'])
                    computed_speeds.append(round(float(speed) if pd.notnull(speed) else 8.0, 2))
                    computed_dirs.append(round(float(direction) if pd.notnull(direction) else 0.0, 1))
            df['SPEED_KTS'] = computed_speeds
            df['BEARING_DEG'] = computed_dirs

        self.cleaned_df = df
        return df

    def get_storm_list(self) -> List[Dict]:
        if self.cleaned_df is None:
            self.load_and_clean()
        storms = []
        for sid, group in self.cleaned_df.groupby('SID'):
            name = str(group['NAME'].iloc[0]) if 'NAME' in group and pd.notnull(group['NAME'].iloc[0]) else 'UNNAMED'
            season = int(group['SEASON'].iloc[0]) if 'SEASON' in group and pd.notnull(group['SEASON'].iloc[0]) else int(group['ISO_TIME'].min().year)
            start_time = group['ISO_TIME'].min().isoformat() + "Z"
            end_time = group['ISO_TIME'].max().isoformat() + "Z"
            max_wind = float(group['WMO_WIND'].max()) if pd.notnull(group['WMO_WIND'].max()) else 35.0
            min_pres = float(group['WMO_PRES'].min()) if pd.notnull(group['WMO_PRES'].min()) else 1000.0
            basin = str(group['BASIN'].iloc[0]) if 'BASIN' in group and pd.notnull(group['BASIN'].iloc[0]) else 'NI'
            subbasin = str(group['SUBBASIN'].iloc[0]) if 'SUBBASIN' in group and pd.notnull(group['SUBBASIN'].iloc[0]) else 'NI'
            obs_count = len(group)
            storms.append({
                "sid": sid,
                "name": name,
                "season": season,
                "basin": basin,
                "subbasin": subbasin,
                "start_time": start_time,
                "end_time": end_time,
                "max_wind_kts": max_wind,
                "min_pressure_hpa": min_pres,
                "observation_count": obs_count
            })
        return sorted(storms, key=lambda x: (x['season'], x['start_time']), reverse=True)

    def get_storm_trajectory(self, storm_identifier: str) -> List[Dict]:
        if self.cleaned_df is None:
            self.load_and_clean()
        
        # Support legacy SID aliases and name lookups
        target_sid = LEGACY_SID_ALIASES.get(storm_identifier, storm_identifier)
        match = self.cleaned_df[
            (self.cleaned_df['SID'] == target_sid) |
            (self.cleaned_df['SID'] == storm_identifier) | 
            (self.cleaned_df['NAME'].str.upper() == storm_identifier.upper())
        ]
        if match.empty:
            return []
        
        trajectory = []
        for idx, row in match.iterrows():
            iso_str = row['ISO_TIME'].isoformat()
            if not iso_str.endswith("Z"):
                iso_str += "Z"
            
            landfall_raw = row.get('LANDFALL', 0)
            try:
                landfall_val = int(landfall_raw) if pd.notnull(landfall_raw) and str(landfall_raw).strip() != '' else 0
            except (ValueError, TypeError):
                landfall_val = 0

            trajectory.append({
                "time": iso_str,
                "lat": float(row['LAT']),
                "lon": float(row['LON']),
                "wind_kts": float(row['WMO_WIND']),
                "pressure_hpa": float(row['WMO_PRES']),
                "speed_kts": float(row.get('SPEED_KTS', 8.0)),
                "bearing_deg": float(row.get('BEARING_DEG', 0.0)),
                "landfall": landfall_val
            })
        return trajectory

    def create_sequence_dataset(self, seq_len: int = 4, lead_times: List[int] = [1, 2, 4]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Builds sequential tracking dataset:
        Inputs: X of shape [N, seq_len, features] (lat, lon, wind, pressure, speed, bearing)
        Outputs: Y of shape [N, len(lead_times), 3] (target_lat, target_lon, target_wind)
        """
        if self.cleaned_df is None:
            self.load_and_clean()

        X_list, Y_list, storm_ids = [], [], []

        for sid, group in self.cleaned_df.groupby('SID'):
            records = group.sort_values('ISO_TIME').reset_index(drop=True)
            n_obs = len(records)
            max_lead = max(lead_times)
            if n_obs < seq_len + max_lead:
                continue

            feature_cols = ['LAT', 'LON', 'WMO_WIND', 'WMO_PRES', 'SPEED_KTS', 'BEARING_DEG']
            feat_matrix = records[feature_cols].values
            target_cols = ['LAT', 'LON', 'WMO_WIND']
            target_matrix = records[target_cols].values

            for t in range(seq_len, n_obs - max_lead + 1):
                x_seq = feat_matrix[t - seq_len : t]
                y_targets = [target_matrix[t + lt - 1] for lt in lead_times]
                
                X_list.append(x_seq)
                Y_list.append(y_targets)
                storm_ids.append(sid)

        return np.array(X_list, dtype=np.float32), np.array(Y_list, dtype=np.float32), storm_ids

    def storm_level_split(
        self,
        test_storms: Optional[List[str]] = None,
        val_storms: Optional[List[str]] = None,
        manifest_dir: Optional[str] = None
    ):
        """
        Strict storm-level splitting. Guarantees 0% data leakage across temporal observations.
        If test_storms / val_storms not provided, attempts to load from official manifests in ml/data/manifests/.
        Falls back to default holdout storms if manifests are unavailable.
        """
        # Resolve aliases if provided
        if test_storms is not None:
            test_storms = [LEGACY_SID_ALIASES.get(s, s) for s in test_storms]
        if val_storms is not None:
            val_storms = [LEGACY_SID_ALIASES.get(s, s) for s in val_storms]

        # If not provided, try loading from manifests
        if test_storms is None or val_storms is None:
            if manifest_dir is None:
                base_dir = os.path.dirname(os.path.dirname(__file__))
                manifest_dir = os.path.join(base_dir, "data", "manifests")
            
            test_mf = os.path.join(manifest_dir, "test_storms.json")
            val_mf = os.path.join(manifest_dir, "val_storms.json")
            
            if os.path.exists(test_mf) and test_storms is None:
                with open(test_mf, 'r', encoding='utf-8') as f:
                    test_storms = json.load(f).get("storm_ids", [])
            if os.path.exists(val_mf) and val_storms is None:
                with open(val_mf, 'r', encoding='utf-8') as f:
                    val_storms = json.load(f).get("storm_ids", [])

        # Default fallbacks if manifests not found
        if test_storms is None:
            test_storms = ['2023156N10067', '2020136N10088']
        if val_storms is None:
            val_storms = ['2024295N15092']

        X, Y, sids = self.create_sequence_dataset()
        train_idx, val_idx, test_idx = [], [], []

        test_set = set(test_storms)
        val_set = set(val_storms)

        for i, sid in enumerate(sids):
            resolved_sid = LEGACY_SID_ALIASES.get(sid, sid)
            if sid in test_set or resolved_sid in test_set:
                test_idx.append(i)
            elif sid in val_set or resolved_sid in val_set:
                val_idx.append(i)
            else:
                train_idx.append(i)

        return (
            (X[train_idx], Y[train_idx]),
            (X[val_idx], Y[val_idx]),
            (X[test_idx], Y[test_idx])
        )
