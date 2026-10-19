import React, { useState } from 'react';
import { 
  Database, 
  Search, 
  Compass, 
  Wind, 
  ArrowRight, 
  MapPin, 
  Calendar,
  Layers,
  CheckCircle2
} from 'lucide-react';
import { CycloneSummary, CycloneDetail } from '../types';

interface HistoricalArchiveProps {
  historicalList: CycloneSummary[];
  selectedStorm: CycloneDetail | null;
  onSelectStorm: (stormId: string) => void;
  onNavigateToMap: () => void;
}

export const HistoricalArchiveSection: React.FC<HistoricalArchiveProps> = ({
  historicalList,
  selectedStorm,
  onSelectStorm,
  onNavigateToMap
}) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedSubbasin, setSelectedSubbasin] = useState<string>('ALL');

  const filtered = historicalList.filter(s => {
    const matchesSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          s.season.toString().includes(searchTerm);
    const matchesSubbasin = selectedSubbasin === 'ALL' || s.subbasin === selectedSubbasin;
    return matchesSearch && matchesSubbasin;
  });

  return (
    <div className="space-y-6">
      {/* Header and Filter */}
      <div className="p-5 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-cyclo-cyan" />
              <h3 className="text-base font-semibold text-white">
                NOAA IBTrACS North Indian Ocean Historical Cyclone Archive
              </h3>
            </div>
            <p className="text-xs text-cyclo-muted">
              Curated official best-track repository (v04r01) containing verified synoptic observations for Arabian Sea & Bay of Bengal cyclones.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-cyclo-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search storm name or year..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 pr-3 py-1.5 rounded-lg bg-cyclo-darkest border border-cyclo-cardBorder text-xs font-mono text-white focus:outline-none focus:border-cyclo-cyan w-56"
              />
            </div>

            {/* Basin Filter */}
            <select
              value={selectedSubbasin}
              onChange={(e) => setSelectedSubbasin(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-cyclo-darkest border border-cyclo-cardBorder text-xs font-mono text-white focus:outline-none focus:border-cyclo-cyan"
            >
              <option value="ALL">All Subbasins</option>
              <option value="BB">Bay of Bengal (BB)</option>
              <option value="AS">Arabian Sea (AS)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Storm Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((s) => {
          const isSelected = selectedStorm?.summary.sid === s.sid;
          const isSuper = s.max_wind_kts >= 120;
          return (
            <div
              key={s.sid}
              className={`p-5 rounded-xl border transition-all flex flex-col justify-between space-y-4 shadow-card ${
                isSelected 
                  ? 'bg-cyclo-card border-cyclo-cyan shadow-glow' 
                  : 'bg-cyclo-card border-cyclo-cardBorder hover:border-slate-600'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyclo-cyan"></span>
                    <h4 className="text-base font-bold text-white font-mono">Cyclone {s.name}</h4>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
                    {s.season}
                  </span>
                </div>

                <div className="text-xs text-cyclo-muted font-mono mb-3">
                  Basin: <span className="text-slate-300">{s.subbasin === 'BB' ? 'Bay of Bengal' : 'Arabian Sea'}</span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-cyclo-darkest/80 border border-cyclo-cardBorder/50">
                    <span className="text-[10px] text-cyclo-muted block">Peak Wind</span>
                    <span className="text-sm font-bold text-sky-400">{s.max_wind_kts} kts</span>
                    <span className="text-[10px] text-slate-400 block">{Math.round(s.max_wind_kts * 1.852)} km/h</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-cyclo-darkest/80 border border-cyclo-cardBorder/50">
                    <span className="text-[10px] text-cyclo-muted block">Min Pressure</span>
                    <span className="text-sm font-bold text-rose-400">{s.min_pressure_hpa} hPa</span>
                    <span className="text-[10px] text-slate-400 block">Severe Core</span>
                  </div>
                </div>

                <div className="text-[11px] font-mono text-slate-400 space-y-1 mt-3 pt-2 border-t border-cyclo-cardBorder/40">
                  <div className="flex justify-between">
                    <span>Obs. Count:</span>
                    <span className="text-white">{s.observation_count} fixes</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Duration:</span>
                    <span className="text-white">{s.start_time.slice(5, 10)} to {s.end_time.slice(5, 10)}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => {
                  onSelectStorm(s.sid);
                  onNavigateToMap();
                }}
                className={`w-full py-2 rounded-lg text-xs font-mono font-medium flex items-center justify-center gap-2 transition-all ${
                  isSelected
                    ? 'bg-cyclo-cyan text-black font-bold'
                    : 'bg-cyclo-darkest hover:bg-cyclo-dark border border-cyclo-cardBorder text-cyclo-cyan'
                }`}
              >
                <span>{isSelected ? 'Currently Loaded in Map' : 'Load into Digital Twin'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
