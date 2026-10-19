import React, { useState, useEffect } from 'react';
import { 
  Eye, 
  Target, 
  Crosshair, 
  AlertTriangle, 
  CheckCircle2, 
  BarChart3, 
  HelpCircle,
  Play,
  RotateCcw,
  ShieldAlert,
  Info
} from 'lucide-react';
import { api } from '../services/api';
import { DetectionResult, ClassificationResult, SampleBenchmark } from '../types';

interface AIVisionSectionProps {
  benchmarks: SampleBenchmark[];
}

export const AIVisionSection: React.FC<AIVisionSectionProps> = ({ benchmarks }) => {
  const [selectedSample, setSelectedSample] = useState<SampleBenchmark | null>(benchmarks[0] || null);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [classificationResult, setClassificationResult] = useState<ClassificationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (benchmarks.length > 0 && !selectedSample) {
      setSelectedSample(benchmarks[0]);
    }
  }, [benchmarks]);

  useEffect(() => {
    if (selectedSample) {
      runAIInference(selectedSample);
    }
  }, [selectedSample]);

  const runAIInference = async (sample: SampleBenchmark) => {
    setLoading(true);
    setError(null);
    try {
      const [det, cls] = await Promise.all([
        api.detectCyclone(sample.filename, sample.bounds),
        api.classifyStructure(sample.filename)
      ]);
      setDetectionResult(det);
      setClassificationResult(cls);
    } catch (err: any) {
      console.error('AI Vision error:', err);
      setError('Backend AI inference failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getImageUrl = (filename: string) => {
    return `http://127.0.0.1:8000/static/imagery/${filename}`;
  };

  return (
    <div className="space-y-6">
      {/* Benchmark Observation Picker */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Eye className="w-5 h-5 text-cyclo-cyan" />
            <h3 className="text-base font-semibold text-white">AI Vision: Detection, Center Estimation & Structure</h3>
          </div>
          <span className="text-xs font-mono text-cyclo-muted">Models A & B (PyTorch 2.10)</span>
        </div>

        <p className="text-xs text-cyclo-muted">
          Select a verified multi-spectral Geostationary Infrared (10.8 µm TIR-1) observation to run real-time dual-head 
          cyclone center localization and 5-stage structural classification.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-2">
          {benchmarks.map((b) => {
            const isSelected = selectedSample?.filename === b.filename;
            return (
              <button
                key={b.filename}
                onClick={() => setSelectedSample(b)}
                className={`p-2.5 rounded-xl text-left border transition-all text-xs font-mono flex flex-col justify-between ${
                  isSelected
                    ? 'bg-cyclo-cyan/15 border-cyclo-cyan text-cyclo-cyan shadow-glow'
                    : 'bg-cyclo-darkest/70 border-cyclo-cardBorder text-slate-300 hover:border-slate-500'
                }`}
              >
                <div>
                  <div className="font-bold truncate">{b.storm_name}</div>
                  <div className="text-[10px] text-cyclo-muted truncate mt-0.5">{b.stage}</div>
                </div>
                <div className="text-[10px] text-slate-400 mt-2 pt-1 border-t border-cyclo-cardBorder/50 flex justify-between">
                  <span>{b.intensity_wind_kts} kts</span>
                  <span>{b.pressure_hpa} hPa</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Analysis Display */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Satellite Image with Interactive AI Center Crosshair (6 cols) */}
        <div className="lg:col-span-6 rounded-xl overflow-hidden border border-cyclo-cardBorder bg-cyclo-card shadow-card flex flex-col">
          <div className="p-3 bg-cyclo-dark/80 border-b border-cyclo-cardBorder flex items-center justify-between text-xs font-mono">
            <span className="text-white font-bold flex items-center gap-1.5">
              <Crosshair className="w-3.5 h-3.5 text-cyclo-cyan" />
              {selectedSample?.storm_name} ({selectedSample?.channel})
            </span>
            <span className="text-slate-400 text-[11px]">{selectedSample?.observation_time.slice(0, 16)} UTC</span>
          </div>

          <div className="relative p-4 flex items-center justify-center bg-cyclo-darkest/90 min-h-[420px]">
            {selectedSample && (
              <div className="relative inline-block max-w-[380px] max-h-[380px] rounded-lg overflow-hidden border border-cyclo-cardBorder/80 shadow-2xl">
                <img
                  src={getImageUrl(selectedSample.filename)}
                  alt="Cyclone Satellite Imagery"
                  className="w-full h-full object-contain block"
                />

                {/* AI Overlaid Storm Center Crosshairs */}
                {detectionResult && detectionResult.cyclone_detected && (
                  <>
                    {/* Pulsing center marker */}
                    <div 
                      className="absolute w-6 h-6 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                      style={{
                        top: `${(detectionResult.center_pixel.y / detectionResult.image_dimensions.height) * 100}%`,
                        left: `${(detectionResult.center_pixel.x / detectionResult.image_dimensions.width) * 100}%`
                      }}
                    >
                      <div className="w-full h-full rounded-full border-2 border-cyclo-cyan animate-ping opacity-75"></div>
                      <div className="absolute inset-0 m-auto w-2 h-2 rounded-full bg-cyclo-cyan shadow-glow"></div>
                      {/* Reticle lines */}
                      <div className="absolute -left-3 top-1/2 w-3 h-[1px] bg-cyclo-cyan"></div>
                      <div className="absolute -right-3 top-1/2 w-3 h-[1px] bg-cyclo-cyan"></div>
                      <div className="absolute left-1/2 -top-3 w-[1px] h-3 bg-cyclo-cyan"></div>
                      <div className="absolute left-1/2 -bottom-3 w-[1px] h-3 bg-cyclo-cyan"></div>
                    </div>

                    {/* Eyewall radius circle */}
                    {detectionResult.estimated_eye_radius_px > 0 && (
                      <div
                        className="absolute rounded-full border border-dashed border-amber-400 pointer-events-none"
                        style={{
                          top: `${(detectionResult.center_pixel.y / detectionResult.image_dimensions.height) * 100}%`,
                          left: `${(detectionResult.center_pixel.x / detectionResult.image_dimensions.width) * 100}%`,
                          width: `${(detectionResult.estimated_eye_radius_px * 2 / detectionResult.image_dimensions.width) * 100}%`,
                          height: `${(detectionResult.estimated_eye_radius_px * 2 / detectionResult.image_dimensions.height) * 100}%`,
                          transform: 'translate(-50%, -50%)'
                        }}
                      ></div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Georeferenced Coordinates Pill */}
            {detectionResult?.georeferenced && (
              <div className="absolute bottom-6 left-6 px-3 py-1.5 rounded-lg bg-cyclo-dark/95 border border-cyclo-cyan/40 text-xs font-mono text-cyclo-cyan shadow-glow flex items-center gap-2">
                <Target className="w-4 h-4 text-cyclo-cyan" />
                <span>
                  Center: {detectionResult.center_coordinates?.lat.toFixed(2)}°N, {detectionResult.center_coordinates?.lon.toFixed(2)}°E
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Model A & Model B Deep Telemetry (6 cols) */}
        <div className="lg:col-span-6 space-y-4">
          {/* Model A Detection Card */}
          <div className="p-4 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-3">
            <div className="flex items-center justify-between border-b border-cyclo-cardBorder/60 pb-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                Model A: Cyclone Detection & Center Head
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                detectionResult?.quality_flag === 'REJECTED_BLANK_OR_UNIFORM_INPUT'
                  ? 'bg-rose-950 text-rose-300 border border-rose-500/40'
                  : detectionResult?.model_status === 'UNTRAINED'
                  ? 'bg-amber-950 text-amber-300 border border-amber-500/40'
                  : detectionResult?.cyclone_detected 
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40' 
                  : 'bg-slate-800 text-slate-300 border border-slate-600/40'
              }`}>
                {detectionResult?.quality_flag === 'REJECTED_BLANK_OR_UNIFORM_INPUT'
                  ? 'BLANK INPUT REJECTED'
                  : detectionResult?.model_status === 'UNTRAINED'
                  ? 'DEMO (UNTRAINED MODEL)'
                  : detectionResult?.cyclone_detected 
                  ? 'CYCLONE CONFIRMED' 
                  : 'NO CYCLONE DETECTED'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-cyclo-darkest/80 border border-cyclo-cardBorder/50">
                <span className="text-[10px] text-cyclo-muted block">Detection Confidence</span>
                <span className="text-lg font-bold text-cyclo-cyan">
                  {detectionResult ? `${(detectionResult.detection_confidence * 100).toFixed(1)}%` : '--'}
                </span>
                <span className="text-[10px] text-slate-400 block mt-0.5">Dual-Head Sigmoid</span>
              </div>
              <div className="p-2.5 rounded-lg bg-cyclo-darkest/80 border border-cyclo-cardBorder/50">
                <span className="text-[10px] text-cyclo-muted block">Image-Space Pixel Center</span>
                <span className="text-sm font-bold text-slate-200 mt-1 block">
                  {detectionResult ? `[X: ${detectionResult.center_pixel.x}, Y: ${detectionResult.center_pixel.y}]` : '--'}
                </span>
                <span className="text-[10px] text-cyclo-muted block mt-0.5">Dim: 512 x 512 px</span>
              </div>
            </div>

            {/* Georeferencing Status Notice */}
            <div className="p-2.5 rounded-lg bg-cyclo-darkest/60 border border-cyclo-cardBorder/40 text-[11px] font-mono text-slate-300 flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
              <div>
                <strong>Georeferencing Pipeline:</strong> {detectionResult?.georeferenced ? (
                  <span>Geographic bounds parsed from observation manifest; latitude and longitude computed via linear transform.</span>
                ) : (
                  <span className="text-amber-400">{detectionResult?.georeferencing_warning}</span>
                )}
              </div>
            </div>
          </div>

          {/* Model B Structure Classification Card */}
          <div className="p-4 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-3">
            <div className="flex items-center justify-between border-b border-cyclo-cardBorder/60 pb-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                Model B: Structure & Stage Classifier
              </span>
              <span className="text-xs font-mono text-purple-400 font-bold">
                {classificationResult?.predicted_stage || 'Analyzing...'}
              </span>
            </div>

            {/* Class Probabilities Bar Chart */}
            <div className="space-y-2 pt-1 font-mono text-xs">
              {classificationResult?.class_probabilities.map((cp) => {
                const pct = Math.round(cp.probability * 100);
                const isWinner = cp.class_id === classificationResult.predicted_class_id;
                return (
                  <div key={cp.class_id} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className={isWinner ? 'text-white font-bold' : 'text-cyclo-muted'}>
                        {cp.label}
                      </span>
                      <span className={isWinner ? 'text-cyclo-cyan font-bold' : 'text-slate-400'}>
                        {pct}%
                      </span>
                    </div>
                    <div className="h-1.5 w-full bg-cyclo-darkest rounded-full overflow-hidden border border-cyclo-cardBorder/40">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${
                          isWinner ? 'bg-gradient-to-r from-cyclo-cyan to-blue-500 shadow-glow' : 'bg-slate-700'
                        }`}
                        style={{ width: `${pct}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Entropy & Scientific Disclaimer */}
            <div className="pt-2 border-t border-cyclo-cardBorder/50 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono text-cyclo-muted">
                <span>Normalized Shannon Entropy:</span>
                <span className="text-slate-300 font-bold">
                  {classificationResult ? classificationResult.uncertainty_entropy : '--'} (Max: 1.0)
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-sky-950/20 border border-sky-500/20 text-[10px] text-slate-400 leading-relaxed">
                <span className="text-sky-300 font-semibold">Scientific Disclaimer: </span>
                {classificationResult?.scientific_disclaimer}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
