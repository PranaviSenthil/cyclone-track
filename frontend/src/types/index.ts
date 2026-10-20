export interface TrajectoryPoint {
  time: string;
  lat: float;
  lon: float;
  wind_kts: number;
  pressure_hpa: number;
  speed_kts?: number;
  bearing_deg?: number;
  landfall?: number;
}

export type float = number;

export interface CycloneSummary {
  sid: string;
  name: string;
  season: number;
  basin: string;
  subbasin: string;
  start_time: string;
  end_time: string;
  max_wind_kts: number;
  min_pressure_hpa: number;
  observation_count: number;
}

export interface CycloneDetail {
  summary: CycloneSummary;
  trajectory: TrajectoryPoint[];
  is_active: boolean;
  status_label: string;
}

export interface ActiveCycloneResponse {
  active_cyclones: CycloneDetail[];
  count: number;
  data_source: string;
  timestamp: string;
  synoptic_status: string;
  note: string;
  historical_demo_available?: {
    storm_name: string;
    sid: string;
    max_wind_kts: number;
    subbasin: string;
    reference_data: CycloneDetail;
  };
}

export interface DataSourceStatus {
  provider: string;
  status: 'LIVE' | 'HISTORICAL' | 'CACHED' | 'DEMO' | 'UNAVAILABLE' | 'CREDENTIALS_REQUIRED';
  observation_timestamp?: string;
  retrieval_timestamp: string;
  freshness: string;
  authenticated: boolean;
  details: string;
  cached_items?: number;
}

export interface SatelliteLayerInfo {
  id: string;
  name: string;
  satellite: string;
  format: string;
  tile_matrix_set: string;
  max_zoom: number;
  description: string;
}

export interface SampleBenchmark {
  filename: string;
  filepath: string;
  storm_name: string;
  observation_time: string;
  stage: string;
  classification_label: string;
  has_eye: boolean;
  center_pixel: [number, number];
  bounds: { min_lat: number; max_lat: number; min_lon: number; max_lon: number };
  center_geo: { lat: number; lon: number };
  intensity_wind_kts: number;
  pressure_hpa: number;
  channel: string;
  provenance: string;
}

export interface SatelliteAvailableResponse {
  layers: SatelliteLayerInfo[];
  default_layer: string;
  default_date: string;
  wmts_base_url: string;
  sample_benchmarks: SampleBenchmark[];
  provider_status: DataSourceStatus[];
}

export interface DetectionResult {
  cyclone_detected: boolean;
  demo_detected?: boolean;
  detection_confidence: number;
  image_dimensions: { width: number; height: number };
  center_pixel: { x: number; y: number };
  estimated_eye_radius_px: number;
  georeferenced: boolean;
  center_coordinates?: { lat: number; lon: number };
  georeferencing_warning?: string;
  model_version: string;
  model_status?: string;
  quality_flag: string;
  scientific_disclaimer?: string;
}

export interface ClassProbability {
  class_id: number;
  label: string;
  probability: number;
}

export interface ClassificationResult {
  predicted_class_id: number;
  predicted_stage: string;
  confidence: number;
  class_probabilities: ClassProbability[];
  uncertainty_entropy: number;
  out_of_distribution_warning: boolean;
  scientific_disclaimer: string;
  model_version: string;
  model_status?: string;
  quality_flag?: string;
}

export interface TrackWaypoint {
  lead_time_hours: number;
  lat: number;
  lon: number;
  method: string;
  is_supported?: boolean;
}

export interface IntensityForecast {
  lead_time_hours: number;
  predicted_wind_kts: number;
  predicted_wind_kmh: number;
  predicted_pressure_hpa: number;
  wind_interval_80pct: [number, number];
  pressure_interval_80pct: [number, number];
  persistence_wind_kts: number;
  persistence_pressure_hpa: number;
}

export interface PredictionResult {
  satellite_analysis?: {
    detection: DetectionResult;
    classification: ClassificationResult;
    status: string;
  };
  has_satellite_data: boolean;
  has_trajectory_data: boolean;
  baseline_track: TrackWaypoint[];
  gru_track: TrackWaypoint[];
  fused_track: TrackWaypoint[];
  uncertainty_cones: {
    cone_80pct_geojson: [number, number][];
    cone_95pct_geojson: [number, number][];
  };
  intensity_forecast: {
    current_observation: {
      wind_kts: number;
      wind_kmh: number;
      pressure_hpa: number;
    };
    forecasts: IntensityForecast[];
    units: { wind: string; pressure: string };
    model_version: string;
  };
  fusion_mode: string;
}

export type ModelStatusType = 
  | 'UNTRAINED' 
  | 'TRAINED_NOT_VALIDATED' 
  | 'VALIDATED_ON_HOLDOUT' 
  | 'TRAINED_EVALUATED'
  | 'CALIBRATED_EMPIRICAL_QUANTILES'
  | 'DEMO_ONLY_SAMPLE_PAIRED'
  | 'DEMO_ONLY' 
  | 'ERROR' 
  | 'UNAVAILABLE'
  | 'VALIDATED';

export interface CoastalSector {
  name: string;
  state: string;
  lat: number;
  lon: number;
  zone: string;
}

export interface SectorRiskAssessment {
  sector_name: string;
  state: string;
  coordinates: { lat: number; lon: number };
  minimum_distance_km: number;
  time_to_closest_approach_hours: number;
  proximity_level: 'CRITICAL_PROXIMITY' | 'HIGH_PROXIMITY' | 'MODERATE_PROXIMITY' | 'LOW_PROXIMITY';
  advisory: string;
  closest_predicted_coords: { lat: number | null; lon: number | null };
}

export interface RiskAssessmentResult {
  assessment_timestamp: string;
  forecast_horizons_checked: number[];
  storm_intensity_classification: { category: string; code: string; severity: string };
  most_exposed_sector: SectorRiskAssessment | null;
  sectors_assessed: SectorRiskAssessment[];
  methodology: string;
  uncertainty_calibrated: boolean;
  disclaimer: string;
}


export interface ModelInfo {
  id: string;
  name: string;
  type: string;
  status: ModelStatusType;
  validation_status?: string;
  real_state?: string;
  architecture: string;
  checkpoint?: string;
  horizons?: string[];
  classes?: string[];
  note?: string;
}

export interface ModelStatusResponse {
  models: ModelInfo[];
  device: string;
  pytorch_version: string;
  checkpoints_present: boolean;
}

export interface AblationConfig {
  name: string;
  description: string;
  track_error_6h_km: number | string;
  track_error_12h_km: number | string;
  track_error_24h_km: number | string;
  intensity_mae_kts: number | string;
  classification_f1: string | number;
  status?: string;
}

export interface EvaluationMetricsResponse {
  track_evaluation: {
    model: string;
    final_train_loss: number;
    test_results_km: {
      [key: string]: { model_mean_km: number; baseline_mean_km: number };
    };
    loss_curve: { epoch: number; loss: number }[];
  };
  fusion_ablation_study: {
    configurations: AblationConfig[];
    conclusion: string;
    test_split_storms: string[];
    verification_status: string;
  };
  training_methodology: string;
  evaluation_date: string;
}
