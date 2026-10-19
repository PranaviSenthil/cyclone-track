import React, { useState } from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  Send, 
  MapPin, 
  Wind, 
  Clock, 
  FileText, 
  CheckCircle2, 
  Info,
  Radio
} from 'lucide-react';
import { api } from '../services/api';
import { CycloneDetail, PredictionResult } from '../types';

interface RiskImpactProps {
  selectedStorm: CycloneDetail | null;
  predictionData: PredictionResult | null;
}

export const RiskImpactSection: React.FC<RiskImpactProps> = ({
  selectedStorm,
  predictionData
}) => {
  const [warningLevel, setWarningLevel] = useState<string>('RED_ALERT');
  const [targetDistrict, setTargetDistrict] = useState<string>('Kutch District, Gujarat');
  const [dispatchedAlert, setDispatchedAlert] = useState<any>(null);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);

  const handleDispatchDemoAlert = async () => {
    setIsDispatching(true);
    try {
      const res = await api.dispatchDemoAlert({
        stormName: selectedStorm ? `Cyclone ${selectedStorm.summary.name}` : 'Cyclone BIPARJOY',
        estimatedLandfallTime: '2023-06-15T12:00:00Z',
        landfallDistrict: targetDistrict,
        maxSustainedWindKmh: 145.0,
        warningLevel: warningLevel
      });
      setDispatchedAlert(res);
    } catch (err: any) {
      console.error('Failed to dispatch demo alert:', err);
    } finally {
      setIsDispatching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-2">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-500" />
          <h3 className="text-base font-semibold text-white">
            Disaster Risk, Landfall Impact Assessment & Early Warning Workflow
          </h3>
        </div>
        <p className="text-xs text-cyclo-muted leading-relaxed">
          Simulated multi-tier alert generation based on model track divergence and projected gale wind radii. 
          <strong className="text-amber-400"> Research Demonstration:</strong> Official bulletins are exclusively issued by IMD RSMC New Delhi.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Risk Impact Modeling & Radius Cards (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-4">
            <h4 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center gap-2">
              <MapPin className="w-4 h-4 text-cyclo-cyan" />
              Projected Coastal Impact Zones
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3.5 rounded-xl bg-cyclo-darkest/90 border border-rose-500/40 space-y-1.5">
                <div className="text-[10px] text-rose-400 font-bold uppercase">Estimated Landfall Window</div>
                <div className="text-base font-bold text-white">Within 18 - 24 Hours</div>
                <div className="text-[11px] text-slate-400">Target Sector: Kutch & Saurashtra Coast</div>
              </div>

              <div className="p-3.5 rounded-xl bg-cyclo-darkest/90 border border-amber-500/40 space-y-1.5">
                <div className="text-[10px] text-amber-400 font-bold uppercase">Gale Wind Radius (50+ kts)</div>
                <div className="text-base font-bold text-white">~110 km from Core</div>
                <div className="text-[11px] text-slate-400">Damage Potential: Structural & Power grid</div>
              </div>
            </div>

            {/* Inundation & Surge Estimates */}
            <div className="p-4 rounded-xl bg-cyclo-darkest/80 border border-cyclo-cardBorder/60 space-y-2 text-xs font-mono">
              <span className="text-cyclo-cyan font-bold block">Estimated Storm Surge:</span>
              <div className="flex justify-between text-slate-300">
                <span>Astronomical Tide + Surge:</span>
                <span className="text-white font-bold">2.5 - 3.5 meters above normal</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Inundation Zone:</span>
                <span className="text-white">Low-lying tidal flats up to 4 km inland</span>
              </div>
            </div>

            {/* Standard Operating Procedures (SOP) Checklist */}
            <div className="space-y-2 pt-2">
              <span className="text-xs font-mono font-bold text-slate-300 block uppercase">
                Recommended Disaster Management Actions:
              </span>
              <div className="space-y-1.5 text-xs text-slate-300 font-mono">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Immediate suspension of all deep-sea and coastal fishing operations.</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Evacuation of vulnerable populace in coastal mudhouse settlements.</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Pre-positioning of NDRF/SDRF rescue teams and backup diesel generators.</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Interactive Early Warning Bulletin Dispatcher (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-4">
            <div className="flex items-center justify-between border-b border-cyclo-cardBorder/60 pb-2">
              <span className="text-xs font-mono font-bold uppercase text-white flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyclo-cyan" />
                Demonstration Alert Dispatcher
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-500/30">
                DEMO WORKFLOW
              </span>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div>
                <label className="text-cyclo-muted block mb-1">Target District / Sector:</label>
                <input
                  type="text"
                  value={targetDistrict}
                  onChange={(e) => setTargetDistrict(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-cyclo-darkest border border-cyclo-cardBorder text-white focus:outline-none focus:border-cyclo-cyan"
                />
              </div>

              <div>
                <label className="text-cyclo-muted block mb-1">Warning Severity Tier:</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'RED_ALERT', label: 'Red Alert', color: 'border-rose-500 text-rose-400 bg-rose-950/40' },
                    { id: 'ORANGE_ALERT', label: 'Orange Alert', color: 'border-amber-500 text-amber-300 bg-amber-950/40' },
                    { id: 'YELLOW_WATCH', label: 'Yellow Watch', color: 'border-yellow-500 text-yellow-300 bg-yellow-950/40' },
                  ].map(w => (
                    <button
                      key={w.id}
                      type="button"
                      onClick={() => setWarningLevel(w.id)}
                      className={`p-2 rounded-lg border text-center transition-all ${
                        warningLevel === w.id ? `${w.color} font-bold shadow` : 'border-cyclo-cardBorder text-cyclo-muted'
                      }`}
                    >
                      {w.label}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleDispatchDemoAlert}
                disabled={isDispatching}
                className="w-full py-2.5 rounded-lg bg-gradient-to-r from-rose-600 to-amber-600 hover:opacity-95 text-white font-bold font-mono text-xs shadow-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isDispatching ? 'Transmitting...' : 'Dispatch Demonstration Early Warning'}</span>
              </button>
            </div>

            {/* Dispatched Bulletin Preview */}
            {dispatchedAlert && (
              <div className="p-3.5 rounded-xl bg-cyclo-darkest border border-rose-500/50 space-y-2 text-xs font-mono shadow-card animate-fadeIn">
                <div className="flex items-center justify-between text-rose-400 font-bold border-b border-rose-500/30 pb-1.5">
                  <span>{dispatchedAlert.bulletin_id}</span>
                  <span>{dispatchedAlert.warning_level}</span>
                </div>
                <div className="text-[11px] text-slate-300 space-y-1">
                  <div><strong>Storm:</strong> {dispatchedAlert.storm}</div>
                  <div><strong>Target:</strong> {dispatchedAlert.landfall_target}</div>
                  <div><strong>Peak Wind:</strong> {dispatchedAlert.projected_peak_wind_kmh} km/h</div>
                </div>
                <div className="p-2 rounded bg-rose-950/30 border border-rose-500/20 text-[10px] text-rose-300 leading-tight">
                  {dispatchedAlert.official_disclaimer}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
