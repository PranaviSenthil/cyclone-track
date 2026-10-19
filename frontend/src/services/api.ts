import {
  ActiveCycloneResponse,
  CycloneDetail,
  CycloneSummary,
  SatelliteAvailableResponse,
  DetectionResult,
  ClassificationResult,
  PredictionResult,
  ModelStatusResponse,
  EvaluationMetricsResponse,
  DataSourceStatus
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {})
      }
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`API Error ${res.status}: ${errText}`);
    }
    return await res.json();
  } catch (err: any) {
    console.error(`Request failed for ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  getHealth: () => request<{ status: string; service: string; version: string }>('/health'),
  
  getDataSources: () => request<DataSourceStatus[]>('/data/sources'),

  getSatelliteAvailable: () => request<SatelliteAvailableResponse>('/satellite/available'),

  getActiveCyclones: () => request<ActiveCycloneResponse>('/cyclones/active'),

  getHistoricalCyclones: () => request<CycloneSummary[]>('/cyclones/historical'),

  getCycloneById: (stormId: string) => request<CycloneDetail>(`/cyclones/${stormId}`),

  detectCyclone: (sampleId?: string, bounds?: Record<string, number>) =>
    request<DetectionResult>('/detect', {
      method: 'POST',
      body: JSON.stringify({ sample_id: sampleId, bounds })
    }),

  classifyStructure: (sampleId?: string) =>
    request<ClassificationResult>('/classify', {
      method: 'POST',
      body: JSON.stringify({ sample_id: sampleId })
    }),

  predictCyclone: (params: {
    stormId?: string;
    sampleImageId?: string;
    trajectoryHistory?: any[];
    bounds?: Record<string, number>;
    currentWindKts?: number;
    currentPressureHpa?: number;
  }) =>
    request<PredictionResult>('/predict', {
      method: 'POST',
      body: JSON.stringify({
        storm_id: params.stormId,
        sample_image_id: params.sampleImageId,
        trajectory_history: params.trajectoryHistory,
        bounds: params.bounds,
        current_wind_kts: params.currentWindKts,
        current_pressure_hpa: params.currentPressureHpa
      })
    }),

  getModelsStatus: () => request<ModelStatusResponse>('/models/status'),

  getModelsMetrics: () => request<EvaluationMetricsResponse>('/models/metrics'),

  dispatchDemoAlert: (params: {
    stormName: string;
    estimatedLandfallTime: string;
    landfallDistrict: string;
    maxSustainedWindKmh: number;
    warningLevel: string;
  }) =>
    request<any>('/alerts/demo', {
      method: 'POST',
      body: JSON.stringify({
        storm_name: params.stormName,
        estimated_landfall_time: params.estimatedLandfallTime,
        landfall_district: params.landfallDistrict,
        max_sustained_wind_kmh: params.maxSustainedWindKmh,
        warning_level: params.warningLevel
      })
    })
};
