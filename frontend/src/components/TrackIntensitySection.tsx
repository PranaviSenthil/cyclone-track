import React, { useState } from 'react';
import { 
  TrendingUp, 
  Wind, 
  Gauge, 
  Layers, 
  Calendar, 
  Clock, 
  CheckCircle2, 
  ArrowUpRight,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  AreaChart, 
  Area,
  Legend
} from 'recharts';
import { PredictionResult, CycloneDetail } from '../types';

interface TrackIntensitySectionProps {
  selectedStorm: CycloneDetail | null;
  predictionData: PredictionResult | null;
  onRunPrediction: () => void;
  isPredicting: boolean;
}

export const TrackIntensitySection: React.FC<TrackIntensitySectionProps> = ({
  selectedStorm,
  predictionData,
  onRunPrediction,
  isPredicting
}) => {
  const [activeHorizon, setActiveHorizon] = useState<number>(24);

  // Prepare Intensity Chart Data
  const intensityData = predictionData?.intensity_forecast?.forecasts.map(f => ({
    horizon: `+${f.lead_time_hours}h`,
    lead_time: f.lead_time_hours,
    wind_kts: f.predicted_wind_kts,
    wind_kmh: f.predicted_wind_kmh,
    wind_lower: f.wind_interval_80pct[0],
    wind_upper: f.wind_interval_80pct[1],
    persistence_wind: f.persistence_wind_kts,
    pressure_hpa: f.predicted_pressure_hpa,
    persistence_pres: f.persistence_pressure_hpa
  })) || [
    { horizon: '+6h', lead_time: 6, wind_kts: 70, wind_kmh: 130, wind_lower: 64, wind_upper: 76, persistence_wind: 65, pressure_hpa: 970, persistence_pres: 975 },
    { horizon: '+12h', lead_time: 12, wind_kts: 78, wind_kmh: 144, wind_lower: 70, wind_upper: 86, persistence_wind: 65, pressure_hpa: 964, persistence_pres: 975 },
    { horizon: '+24h', lead_time: 24, wind_kts: 88, wind_kmh: 163, wind_lower: 76, wind_upper: 100, persistence_wind: 65, pressure_hpa: 955, persistence_pres: 975 }
  ];

  // Track Comparison Data (Loaded from holdout evaluation on Cyclone AMPHAN and BIPARJOY)
  const trackComparison = [
    { horizon: '+6h', baseline_km: 11.6, gru_km: 68.9 },
    { horizon: '+12h', baseline_km: 24.9, gru_km: 143.4 },
    { horizon: '+24h', baseline_km: 58.6, gru_km: 271.8 }
  ];

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-cyclo-cyan" />
            <h3 className="text-base font-semibold text-white">
              Cyclone Track & Intensity Forecasting Engine
            </h3>
          </div>
          <p className="text-xs text-cyclo-muted font-mono">
            Comparing Extrapolation Baseline vs PyTorch Deep GRU vs Multi-Source Fusion (+6h, +12h, +24h)
          </p>
        </div>

        <button
          onClick={onRunPrediction}
          disabled={isPredicting}
          className="px-4 py-2 rounded-lg bg-gradient-to-r from-cyclo-cyan to-blue-600 hover:opacity-95 text-black font-semibold font-mono text-xs shadow-glow flex items-center gap-2 transition-all disabled:opacity-50"
        >
          <Zap className="w-4 h-4" />
          <span>{isPredicting ? 'Forecasting Sequence...' : 'Re-Run Multi-Horizon Predictor'}</span>
        </button>
      </div>

      {/* Main Charts: Track Divergence vs Intensity Forecast */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Track Forecast Error in KM by Lead Time */}
        <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-4">
          <div className="flex items-center justify-between border-b border-cyclo-cardBorder/60 pb-3">
            <div>
              <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyclo-cyan" />
                Track Mean Forecast Error (Haversine KM)
              </h4>
              <span className="text-[11px] text-cyclo-muted font-mono">Evaluated on holdout storms (Amphan & Biparjoy)</span>
            </div>
            <span className="text-xs font-mono text-amber-300 font-bold bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30">
              Baseline Leads Initial GRU
            </span>
          </div>

          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trackComparison} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2D4A" />
                <XAxis dataKey="horizon" stroke="#8A99AD" fontSize={12} fontStyle="bold" />
                <YAxis stroke="#8A99AD" fontSize={11} domain={[0, 300]} unit=" km" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0F182E', borderColor: '#00E5FF', borderRadius: 8, fontSize: 12, fontFamily: 'monospace' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'monospace', paddingTop: 10 }} />
                <Line type="monotone" dataKey="baseline_km" name="Linear Extrapolation Baseline" stroke="#94A3B8" strokeWidth={2} strokeDasharray="4 4" />
                <Line type="monotone" dataKey="gru_km" name="Cyclotrack Track GRU (Initial Train)" stroke="#38BDF8" strokeWidth={2.5} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="text-[11px] font-mono text-cyclo-muted p-2.5 rounded-lg bg-cyclo-darkest/70 border border-cyclo-cardBorder/50 flex justify-between">
            <span>24h Baseline: 58.6 km</span>
            <span className="text-amber-300 font-bold">24h GRU: 271.8 km</span>
            <span className="text-cyclo-muted">Fusion: Phase 4 Retraining</span>
          </div>
        </div>

        {/* Intensity Prediction: Wind Speed & Heuristic Interval */}
        <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-4">
          <div className="flex items-center justify-between border-b border-cyclo-cardBorder/60 pb-3">
            <div>
              <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
                <Wind className="w-4 h-4 text-sky-400" />
                Intensity Prediction (Persistence Baseline)
              </h4>
              <span className="text-[11px] text-cyclo-muted font-mono">Maximum Sustained Winds (knots) — Model D Neural Checkpoint Untrained</span>
            </div>
            <span className="text-xs font-mono text-amber-300 font-bold bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30">
              NOT EVALUATED
            </span>
          </div>

          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={intensityData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2D4A" />
                <XAxis dataKey="horizon" stroke="#8A99AD" fontSize={12} />
                <YAxis stroke="#8A99AD" fontSize={11} domain={['dataMin - 15', 'dataMax + 15']} unit=" kts" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0F182E', borderColor: '#38BDF8', borderRadius: 8, fontSize: 12, fontFamily: 'monospace' }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: 'monospace', paddingTop: 10 }} />
                {/* 80% Confidence Interval envelope */}
                <Area type="monotone" dataKey="wind_upper" name="80% Upper Bound" stroke="none" fill="#38BDF8" fillOpacity={0.15} />
                <Area type="monotone" dataKey="wind_lower" name="80% Lower Bound" stroke="none" fill="#050811" fillOpacity={0.9} />
                {/* Predicted Wind Curve */}
                <Line type="monotone" dataKey="wind_kts" name="Predicted Wind (kts)" stroke="#38BDF8" strokeWidth={3} dot={{ r: 5 }} />
                <Line type="monotone" dataKey="persistence_wind" name="Persistence Baseline" stroke="#64748B" strokeWidth={2} strokeDasharray="4 4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="text-[11px] font-mono text-cyclo-muted p-2.5 rounded-lg bg-cyclo-darkest/70 border border-cyclo-cardBorder/50 flex justify-between">
            <span>Current: {selectedStorm?.trajectory[selectedStorm.trajectory.length - 1]?.wind_kts || 65} kts</span>
            <span>+24h Projected: {intensityData[2]?.wind_kts} kts</span>
            <span className="text-sky-300 font-bold">~{Math.round((intensityData[2]?.wind_kts || 85) * 1.852)} km/h</span>
          </div>
        </div>
      </div>

      {/* Trajectory Waypoints Numerical Table */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-3">
        <h4 className="text-sm font-bold text-white font-mono uppercase tracking-wider">
          Numerical Synoptic Forecast Waypoints
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-cyclo-darkest/90 text-cyclo-muted uppercase text-[10px] border-b border-cyclo-cardBorder">
              <tr>
                <th className="py-2.5 px-3">Lead Time</th>
                <th className="py-2.5 px-3">Forecast Lat</th>
                <th className="py-2.5 px-3">Forecast Lon</th>
                <th className="py-2.5 px-3">Wind Speed (kts / km/h)</th>
                <th className="py-2.5 px-3">80% Interval</th>
                <th className="py-2.5 px-3">Central Pressure</th>
                <th className="py-2.5 px-3">Method</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyclo-cardBorder/40">
              {predictionData?.fused_track.map((pt, idx) => {
                const intens = predictionData.intensity_forecast.forecasts[idx];
                return (
                  <tr key={idx} className="hover:bg-cyclo-dark/40">
                    <td className="py-2 px-3 font-bold text-cyclo-cyan">+{pt.lead_time_hours} Hours</td>
                    <td className="py-2 px-3 text-slate-200">{pt.lat.toFixed(2)}°N</td>
                    <td className="py-2 px-3 text-slate-200">{pt.lon.toFixed(2)}°E</td>
                    <td className="py-2 px-3 text-sky-400 font-bold">
                      {intens?.predicted_wind_kts || 75} kts ({intens?.predicted_wind_kmh || 139} km/h)
                    </td>
                    <td className="py-2 px-3 text-slate-400">
                      [{intens?.wind_interval_80pct[0] || 68} - {intens?.wind_interval_80pct[1] || 82}] kts
                    </td>
                    <td className="py-2 px-3 text-rose-400 font-bold">
                      {intens?.predicted_pressure_hpa || 968} hPa
                    </td>
                    <td className="py-2 px-3 text-slate-400">{pt.method}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
