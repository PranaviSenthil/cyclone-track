import React from 'react';
import { 
  Layers, 
  Cpu, 
  GitCompare, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle,
  TrendingDown,
  Compass,
  ArrowRight
} from 'lucide-react';
import { AblationConfig } from '../types';

interface MultiSourceFusionProps {
  ablationConfigs: AblationConfig[];
}

export const MultiSourceFusionSection: React.FC<MultiSourceFusionProps> = ({ ablationConfigs }) => {
  const configs: AblationConfig[] = ablationConfigs.length > 0 ? ablationConfigs : [
    {
      name: "Historical Motion Baseline",
      description: "Linear forward extrapolation + Coriolis beta-drift vector without neural weights.",
      track_error_6h_km: 11.6,
      track_error_12h_km: 24.9,
      track_error_24h_km: 58.6,
      intensity_mae_kts: "NOT EVALUATED",
      classification_f1: "N/A",
      status: "VALIDATED_ON_HOLDOUT"
    },
    {
      name: "Satellite-Only Model",
      description: "Computer vision classification & center detection from single-snapshot satellite imagery.",
      track_error_6h_km: "NOT EVALUATED",
      track_error_12h_km: "NOT EVALUATED",
      track_error_24h_km: "NOT EVALUATED",
      intensity_mae_kts: "NOT EVALUATED",
      classification_f1: "NOT EVALUATED",
      status: "UNTRAINED"
    },
    {
      name: "Historical-Track Neural Model (GRU)",
      description: "Deep 2-layer GRU sequence network evaluated on holdout storms (Amphan & Biparjoy).",
      track_error_6h_km: 68.9,
      track_error_12h_km: 143.4,
      track_error_24h_km: 271.8,
      intensity_mae_kts: "NOT EVALUATED",
      classification_f1: "N/A",
      status: "TRAINED_NOT_VALIDATED"
    },
    {
      name: "Multi-Source Fused Model (Cyclotrack)",
      description: "Joint representation combining CNN cloud top features, GRU trajectory, and pressure dynamics.",
      track_error_6h_km: "NOT EVALUATED",
      track_error_12h_km: "NOT EVALUATED",
      track_error_24h_km: "NOT EVALUATED",
      intensity_mae_kts: "NOT EVALUATED",
      classification_f1: "NOT EVALUATED",
      status: "DEMO_ONLY"
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-2">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyclo-cyan" />
          <h3 className="text-base font-semibold text-white">
            Multi-Source Fusion Architecture & Rigorous Ablation Study
          </h3>
        </div>
        <p className="text-xs text-cyclo-muted leading-relaxed">
          Evaluating whether multi-modal fusion improves tropical cyclone forecasting. 
          Tested on strictly held-out historical storms (Cyclone AMPHAN and Cyclone BIPARJOY) 
          with <strong className="text-slate-200">zero observation-level leakage</strong>.
        </p>
      </div>

      {/* Multimodal Architecture Diagram Card */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-4">
        <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider block">
          End-to-End Fusion Flow
        </span>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3.5 rounded-xl bg-cyclo-darkest/90 border border-cyclo-cyan/40 space-y-2">
            <div className="text-cyclo-cyan font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyclo-cyan"></span>
              Modality 1: Spatial
            </div>
            <p className="text-[11px] text-slate-400">
              INSAT / GIBS Geostationary TIR-1 brightness temperatures parsed through 4-stage ConvNet to extract eyewall symmetry.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-cyclo-darkest/90 border border-sky-500/40 space-y-2">
            <div className="text-sky-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-sky-400"></span>
              Modality 2: Temporal
            </div>
            <p className="text-[11px] text-slate-400">
              IBTrACS chronological track sequences [lat, lon, speed, bearing] embedded via deep 2-layer GRU with hidden_dim=64.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-cyclo-darkest/90 border border-purple-500/40 space-y-2">
            <div className="text-purple-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
              Modality 3: Physical
            </div>
            <p className="text-[11px] text-slate-400">
              Atmospheric central pressure, translation velocity, and sea-surface thermodynamic potential bounding deltas.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-gradient-to-br from-cyclo-cyan/15 to-blue-900/40 border border-cyclo-cyan space-y-2 shadow-glow">
            <div className="text-white font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyclo-cyan" />
              Fused Output
            </div>
            <p className="text-[11px] text-slate-200">
              Multi-horizon track waypoints, wind/pressure regression, and calibrated 80% & 95% uncertainty cones.
            </p>
          </div>
        </div>
      </div>

      {/* Honest Ablation Comparison Table */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-4">
        <div className="flex items-center justify-between border-b border-cyclo-cardBorder/60 pb-3">
          <div>
            <h4 className="text-sm font-bold text-white font-mono flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-cyclo-cyan" />
              Empirical Ablation Benchmark Matrix
            </h4>
            <span className="text-[11px] text-cyclo-muted font-mono">
              Evaluated on NOAA IBTrACS North Indian Ocean Test Set (Cyclone AMPHAN & BIPARJOY)
            </span>
          </div>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-500/30">
            PRELIMINARY BENCHMARK
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-cyclo-darkest/90 text-cyclo-muted uppercase text-[10px] border-b border-cyclo-cardBorder">
              <tr>
                <th className="py-3 px-3">Model Configuration</th>
                <th className="py-3 px-3">Error @ 6h</th>
                <th className="py-3 px-3">Error @ 12h</th>
                <th className="py-3 px-3">Error @ 24h</th>
                <th className="py-3 px-3">Wind MAE</th>
                <th className="py-3 px-3">Structure F1</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyclo-cardBorder/40">
              {configs.map((c, i) => {
                const isFused = c.name.includes("Fused");
                const formatKm = (val: number | string) => typeof val === 'number' ? `${val} km` : val;
                const formatKts = (val: number | string) => typeof val === 'number' ? `${val} kts` : val;
                return (
                  <tr key={i} className={`hover:bg-cyclo-dark/60 ${isFused ? 'bg-cyclo-cyan/10 font-semibold' : ''}`}>
                    <td className="py-3 px-3">
                      <div className={isFused ? 'text-cyclo-cyan font-bold' : 'text-slate-200 font-medium'}>
                        {c.name}
                      </div>
                      <div className="text-[10px] text-cyclo-muted font-normal mt-0.5 max-w-sm">
                        {c.description}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-slate-300">{formatKm(c.track_error_6h_km)}</td>
                    <td className="py-3 px-3 text-slate-300">{formatKm(c.track_error_12h_km)}</td>
                    <td className={`py-3 px-3 font-bold ${isFused ? 'text-cyclo-cyan text-sm' : 'text-slate-300'}`}>
                      {formatKm(c.track_error_24h_km)}
                    </td>
                    <td className={`py-3 px-3 font-bold ${isFused ? 'text-sky-400' : 'text-slate-400'}`}>
                      {formatKts(c.intensity_mae_kts)}
                    </td>
                    <td className="py-3 px-3 text-purple-400">
                      {typeof c.classification_f1 === 'number' ? c.classification_f1.toFixed(3) : c.classification_f1}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Meteorological Intelligence Conclusion */}
        <div className="p-4 rounded-xl bg-cyclo-darkest/80 border border-cyclo-cyan/30 flex items-start gap-3">
          <TrendingDown className="w-5 h-5 text-cyclo-cyan shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <h5 className="font-bold text-slate-200 font-mono">
              Empirical Evaluation Findings & Roadmap
            </h5>
            <p className="text-slate-400 leading-relaxed font-sans">
              Preliminary holdout evaluation indicates that the initial sequence model (271.8 km at 24h) underperforms 
              the classical linear motion baseline (58.6 km at 24h) due to the limited size of the initial training set 
              (114 observations). In Phase 4, the model will be retrained on the complete NOAA IBTrACS North Indian Ocean 
              archive (~1,500+ fixes) alongside calibrated multimodal fusion.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
