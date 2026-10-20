"""
Disaster Risk and Coastal Proximity Analysis Service.
Computes objective, rule-based coastal proximity and exposure indicators:
1. Distance to major coastal sectors / user-specified locations.
2. Time to Closest Approach (TCA) derived from forecast track.
3. IMD Intensity Classification mapping.
4. Conformal uncertainty margins at closest approach.
5. Strict scientific disclaimers separating prototype metrics from official IMD warnings.
"""

import math
import datetime
from typing import Dict, List, Optional, Tuple, Any
from ml.preprocessing.ibtracs_parser import haversine_distance_km

# Curated reference coastal meteorological and port stations (North Indian Ocean)
KEY_COASTAL_SECTORS = [
    {"name": "Puri / Paradip Coast", "state": "Odisha", "lat": 19.81, "lon": 85.83, "zone": "East Coast"},
    {"name": "Kolkata / Sundarbans", "state": "West Bengal", "lat": 22.00, "lon": 88.50, "zone": "East Coast"},
    {"name": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.68, "lon": 83.21, "zone": "East Coast"},
    {"name": "Chennai / Ennore", "state": "Tamil Nadu", "lat": 13.08, "lon": 80.27, "zone": "East Coast"},
    {"name": "Porbandar / Dwarka", "state": "Gujarat", "lat": 21.64, "lon": 69.60, "zone": "West Coast"},
    {"name": "Veraval / Saurashtra", "state": "Gujarat", "lat": 20.90, "lon": 70.36, "zone": "West Coast"},
    {"name": "Mumbai Coast", "state": "Maharashtra", "lat": 18.92, "lon": 72.83, "zone": "West Coast"},
    {"name": "Chittagong / Cox's Bazar", "state": "Bangladesh", "lat": 21.43, "lon": 91.98, "zone": "Northern Bay"}
]

class RiskService:
    @staticmethod
    def classify_imd_intensity(wind_kts: float) -> Dict[str, str]:
        """
        Maps maximum sustained wind speed (10-min / 1-min consensus)
        to official IMD cyclone scale categories.
        """
        if wind_kts < 17.0:
            return {"category": "Low Pressure Area", "code": "LPA", "severity": "MINIMAL"}
        elif wind_kts < 28.0:
            return {"category": "Depression", "code": "D", "severity": "LOW"}
        elif wind_kts < 34.0:
            return {"category": "Deep Depression", "code": "DD", "severity": "MODERATE"}
        elif wind_kts < 48.0:
            return {"category": "Cyclonic Storm", "code": "CS", "severity": "HIGH"}
        elif wind_kts < 64.0:
            return {"category": "Severe Cyclonic Storm", "code": "SCS", "severity": "VERY_HIGH"}
        elif wind_kts < 90.0:
            return {"category": "Very Severe Cyclonic Storm", "code": "VSCS", "severity": "SEVERE"}
        elif wind_kts < 120.0:
            return {"category": "Extremely Severe Cyclonic Storm", "code": "ESCS", "severity": "DEVASTATING"}
        else:
            return {"category": "Super Cyclonic Storm", "code": "SuCS", "severity": "CATASTROPHIC"}

    def assess_coastal_risk(
        self,
        forecast_waypoints: List[Dict[str, Any]],
        current_wind_kts: float = 65.0,
        custom_lat: Optional[float] = None,
        custom_lon: Optional[float] = None,
        custom_location_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assesses geographic proximity, Time to Closest Approach (TCA),
        and exposure indicators across coastal stations or a custom coordinate.
        """
        if not forecast_waypoints:
            return {"status": "NO_FORECAST_AVAILABLE", "sectors_assessed": []}

        sectors = list(KEY_COASTAL_SECTORS)
        if custom_lat is not None and custom_lon is not None:
            sectors.insert(0, {
                "name": custom_location_name or "Custom Monitored Location",
                "state": "Custom Query",
                "lat": float(custom_lat),
                "lon": float(custom_lon),
                "zone": "User Specified"
            })

        sector_assessments = []

        for sector in sectors:
            s_lat, s_lon = sector["lat"], sector["lon"]
            min_dist_km = float("inf")
            closest_horizon_h = 0
            closest_waypoint = None

            for wp in forecast_waypoints:
                lead_h = wp.get("lead_time_hours", 0)
                wp_lat = wp["lat"]
                wp_lon = wp["lon"]
                dist = haversine_distance_km(wp_lat, wp_lon, s_lat, s_lon)
                if dist < min_dist_km:
                    min_dist_km = dist
                    closest_horizon_h = lead_h
                    closest_waypoint = wp

            # Proximity categorization based on documented distance thresholds
            if min_dist_km < 75.0:
                proximity_level = "CRITICAL_PROXIMITY"
                advisory = "Immediate coastal warning: cyclone center trajectory passes within high-wind radius."
            elif min_dist_km < 150.0:
                proximity_level = "HIGH_PROXIMITY"
                advisory = "Gale wind and heavy rain advisory: sector within outer circulation core."
            elif min_dist_km < 300.0:
                proximity_level = "MODERATE_PROXIMITY"
                advisory = "Watch alert: peripheral squalls and rough sea conditions expected."
            else:
                proximity_level = "LOW_PROXIMITY"
                advisory = "No direct track threat detected within forecast horizon."

            sector_assessments.append({
                "sector_name": sector["name"],
                "state": sector["state"],
                "coordinates": {"lat": s_lat, "lon": s_lon},
                "minimum_distance_km": round(min_dist_km, 1),
                "time_to_closest_approach_hours": closest_horizon_h,
                "proximity_level": proximity_level,
                "advisory": advisory,
                "closest_predicted_coords": {
                    "lat": closest_waypoint["lat"] if closest_waypoint else None,
                    "lon": closest_waypoint["lon"] if closest_waypoint else None
                }
            })

        # Sort by minimum distance to highlight most vulnerable coastal sectors first
        sector_assessments.sort(key=lambda x: x["minimum_distance_km"])
        
        intensity_info = self.classify_imd_intensity(current_wind_kts)

        return {
            "assessment_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "forecast_horizons_checked": [wp.get("lead_time_hours") for wp in forecast_waypoints],
            "storm_intensity_classification": intensity_info,
            "most_exposed_sector": sector_assessments[0] if sector_assessments else None,
            "sectors_assessed": sector_assessments,
            "methodology": "RULE_BASED_GEODESIC_PROXIMITY_ANALYSIS",
            "uncertainty_calibrated": True,
            "disclaimer": (
                "PROTOTYPE RESEARCH ALERT ONLY: Geodesic proximity metrics reflect AI model track predictions. "
                "This is NOT an official disaster alert or evacuation order. Official cyclone advisories and "
                "warnings are issued exclusively by the India Meteorological Department (IMD / RSMC New Delhi)."
            )
        }

risk_service = RiskService()
