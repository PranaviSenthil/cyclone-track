import React from 'react';
import { 
  Cpu, 
  CheckCircle2, 
  Layers, 
  Terminal, 
  Download, 
  Activity, 
  FileCode,
  HardDrive
} from 'lucide-react';
import { ModelInfo, ModelStatusResponse } from '../types';

interface ModelReadinessProps {
  modelStatus: ModelStatusResponse | null;
}

export const ModelReadinessSection: React.FC<ModelReadinessProps> = ({ modelStatus }) => {
  const models = modelStatus?.models || [];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyclo-cyan" />
            <h3 className="text-base font-semibold text-white">
              AI / ML Model Architecture, Versioning & Deployment Provenance
            </h3>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-cyclo-muted">Inference Engine:</span>
            <span className="px-2 py-0.5 rounded bg-cyclo-darkest text-cyclo-cyan border border-cyclo-cyan/30">
              PyTorch {modelStatus?.pytorch_version || '2.10.0'} ({modelStatus?.device || 'CPU'})
            </span>
          </div>
        </div>
        <p className="text-xs text-cyclo-muted">
          All models are verified with small CPU fixtures, compiled PyTorch weights in <code className="text-cyclo-cyan">artifacts/checkpoints/</code>, 
          and evaluated with zero data leakage across storm identifiers.
        </p>
      </div>

      {/* Model Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {models.map((m) => {
          const getStatusBadge = (status: string) => {
            switch (status) {
              case 'TRAINED_EVALUATED':
              case 'VALIDATED_ON_HOLDOUT':
              case 'VALIDATED':
                return 'bg-emerald-950 text-emerald-400 border-emerald-500/40';
              case 'CALIBRATED_EMPIRICAL_QUANTILES':
                return 'bg-indigo-950 text-indigo-300 border-indigo-500/40';
              case 'TRAINED_NOT_VALIDATED':
                return 'bg-amber-950 text-amber-300 border-amber-500/40';
              case 'UNTRAINED':
                return 'bg-rose-950/70 text-rose-300 border-rose-500/40';
              case 'DEMO_ONLY_SAMPLE_PAIRED':
              case 'DEMO_ONLY':
                return 'bg-cyan-950/70 text-cyan-300 border-cyan-500/40';
              default:
                return 'bg-slate-800 text-slate-300 border-slate-600/40';
            }
          };

          return (
            <div
              key={m.id}
              className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder flex flex-col justify-between space-y-3 shadow-card"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold font-mono text-white truncate max-w-[190px]">
                    {m.name}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getStatusBadge(m.status)}`}>
                    {m.status}
                  </span>
                </div>

                <div className="text-[11px] text-cyclo-muted font-mono mb-2">
                  Type: <span className="text-slate-300">{m.type}</span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed bg-cyclo-darkest/70 p-2.5 rounded-lg border border-cyclo-cardBorder/50 font-mono text-[11px]">
                  {m.architecture}
                </p>

                {m.note && (
                  <p className="mt-2 text-[10px] text-amber-300/90 leading-relaxed bg-amber-950/30 p-2 rounded border border-amber-500/20 font-mono">
                    {m.note}
                  </p>
                )}
              </div>

              <div className="pt-2 border-t border-cyclo-cardBorder/40 space-y-1 text-[11px] font-mono">
                {m.checkpoint && (
                  <div className="flex items-center justify-between text-cyclo-muted">
                    <span className="flex items-center gap-1">
                      <HardDrive className="w-3 h-3 text-cyclo-cyan" />
                      Artifact:
                    </span>
                    <span className="text-slate-300 truncate max-w-[160px]">{m.checkpoint}</span>
                  </div>
                )}
                {m.horizons && (
                  <div className="flex justify-between text-cyclo-muted">
                    <span>Forecast Horizons:</span>
                    <span className="text-cyclo-cyan font-bold">{m.horizons.join(', ')}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Verification Standard Box */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-3">
        <h4 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          Reproducible Training & Evaluation Protocol
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono text-slate-300">
          <div className="p-3 rounded-lg bg-cyclo-darkest/80 border border-cyclo-cardBorder/50 space-y-1">
            <span className="text-cyclo-cyan font-bold block">1. Storm Split</span>
            <p className="text-slate-400 text-[11px]">
              Trained on Fani (2019), Tauktae (2021), Mocha (2023). Validated on Dana (2024). Evaluated on Amphan & Biparjoy.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-cyclo-darkest/80 border border-cyclo-cardBorder/50 space-y-1">
            <span className="text-sky-400 font-bold block">2. Geographic Distance</span>
            <p className="text-slate-400 text-[11px]">
              Great-circle Haversine formula implemented without planar approximations to measure true kilometer track error.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-cyclo-darkest/80 border border-cyclo-cardBorder/50 space-y-1">
            <span className="text-purple-400 font-bold block">3. Calibrated Intervals</span>
            <p className="text-slate-400 text-[11px]">
              Empirical historical lead-time errors generate realistic 80% and 95% confidence cones rather than speculative bands.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
