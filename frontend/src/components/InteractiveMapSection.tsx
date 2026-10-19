import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { 
  Layers, 
  Eye, 
  Compass, 
  MapPin, 
  Wind, 
  Activity, 
  Maximize2,
  Calendar,
  ShieldAlert,
  Info
} from 'lucide-react';
import { CycloneDetail, CycloneSummary, PredictionResult } from '../types';

interface InteractiveMapSectionProps {
  selectedStorm: CycloneDetail | null;
  historicalList: CycloneSummary[];
  onSelectStorm: (stormId: string) => void;
  predictionData: PredictionResult | null;
  onRunPrediction: () => void;
  isPredicting: boolean;
}

export const InteractiveMapSection: React.FC<InteractiveMapSectionProps> = ({
  selectedStorm,
  historicalList,
  onSelectStorm,
  predictionData,
  onRunPrediction,
  isPredicting
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layersGroupRef = useRef<L.LayerGroup | null>(null);
  const gibsTileLayerRef = useRef<L.TileLayer | null>(null);

  const [showSatellite, setShowSatellite] = useState<boolean>(true);
  const [showUncertainty, setShowUncertainty] = useState<boolean>(true);
  const [showPredicted, setShowPredicted] = useState<boolean>(true);
  const [selectedGibsLayer, setSelectedGibsLayer] = useState<string>('VIIRS_SNPP_CorrectedReflectance_TrueColor');

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      // Center on North Indian Ocean (Arabian Sea + Bay of Bengal)
      const map = L.map(mapContainerRef.current, {
        center: [18.0, 78.0],
        zoom: 5,
        minZoom: 3,
        maxZoom: 9,
        zoomControl: true,
        attributionControl: false
      });

      // Dark theme CartoDB base layer
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 19
      }).addTo(map);

      const layersGroup = L.layerGroup().addTo(map);
      layersGroupRef.current = layersGroup;
      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update NASA GIBS satellite overlay
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (gibsTileLayerRef.current) {
      map.removeLayer(gibsTileLayerRef.current);
      gibsTileLayerRef.current = null;
    }

    if (showSatellite && selectedStorm) {
      // Pick representative date from storm
      const stormDate = selectedStorm.trajectory[0]?.time.slice(0, 10) || '2023-06-11';
      const gibsUrl = `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${selectedGibsLayer}/default/${stormDate}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;

      const tileLayer = L.tileLayer(gibsUrl, {
        opacity: 0.55,
        maxZoom: 9
      });
      tileLayer.addTo(map);
      gibsTileLayerRef.current = tileLayer;
    }
  }, [showSatellite, selectedGibsLayer, selectedStorm]);

  // Update storm trajectory and predictions
  useEffect(() => {
    const map = mapInstanceRef.current;
    const group = layersGroupRef.current;
    if (!map || !group || !selectedStorm) return;

    group.clearLayers();

    const traj = selectedStorm.trajectory;
    if (traj.length === 0) return;

    const latlngs: [number, number][] = traj.map(p => [p.lat, p.lon]);

    // 1. Draw Observed Trajectory Polyline
    const observedPolyline = L.polyline(latlngs, {
      color: '#00E5FF',
      weight: 3.5,
      opacity: 0.85
    });
    group.addLayer(observedPolyline);

    // 2. Add Observation Markers
    traj.forEach((pt, idx) => {
      const isLatest = idx === traj.length - 1;
      const isLandfall = pt.landfall === 1;

      // Color based on wind intensity
      let markerColor = '#38BDF8';
      let radius = 4;
      if (pt.wind_kts >= 120) markerColor = '#ec4899'; // Super Cyclone
      else if (pt.wind_kts >= 90) markerColor = '#ef4444'; // ESCS
      else if (pt.wind_kts >= 64) markerColor = '#f97316'; // VSCS
      else if (pt.wind_kts >= 48) markerColor = '#eab308'; // SCS
      else if (pt.wind_kts >= 34) markerColor = '#06b6d4'; // CS

      if (isLatest) {
        radius = 8;
        markerColor = '#00E5FF';
      }

      const circle = L.circleMarker([pt.lat, pt.lon], {
        radius: isLatest ? 8 : radius,
        fillColor: markerColor,
        color: isLatest ? '#FFFFFF' : '#050811',
        weight: isLatest ? 2.5 : 1.5,
        opacity: 1,
        fillOpacity: 0.95
      });

      const popupHtml = `
        <div style="font-family: inherit; font-size: 12px; line-height: 1.4;">
          <div style="font-weight: bold; color: #00E5FF; border-bottom: 1px solid #1E2D4A; padding-bottom: 4px; margin-bottom: 4px;">
            ${selectedStorm.summary.name} ${isLatest ? '(Current Position)' : ''}
          </div>
          <div><strong>Time:</strong> ${pt.time.replace('T', ' ')}</div>
          <div><strong>Position:</strong> ${pt.lat.toFixed(2)}°N, ${pt.lon.toFixed(2)}°E</div>
          <div><strong>Max Sustained Wind:</strong> ${pt.wind_kts} kts (${Math.round(pt.wind_kts * 1.852)} km/h)</div>
          <div><strong>Central Pressure:</strong> ${pt.pressure_hpa} hPa</div>
          <div><strong>Forward Speed:</strong> ${pt.speed_kts || 8} kts</div>
          ${isLandfall ? '<div style="color: #ef4444; font-weight: bold; margin-top: 4px;">⚠ Landfall Event Point</div>' : ''}
        </div>
      `;
      circle.bindPopup(popupHtml);
      group.addLayer(circle);
    });

    // 3. Draw Uncertainty Cones if Prediction Data available
    if (showUncertainty && predictionData && predictionData.uncertainty_cones) {
      const cone95 = predictionData.uncertainty_cones.cone_95pct_geojson;
      const cone80 = predictionData.uncertainty_cones.cone_80pct_geojson;

      if (cone95 && cone95.length > 0) {
        const poly95 = L.polygon(cone95 as any, {
          color: '#38BDF8',
          weight: 1,
          fillColor: '#00E5FF',
          fillOpacity: 0.12,
          dashArray: '4, 4'
        });
        poly95.bindTooltip('95% Calibrated Forecast Uncertainty Envelope');
        group.addLayer(poly95);
      }

      if (cone80 && cone80.length > 0) {
        const poly80 = L.polygon(cone80 as any, {
          color: '#00E5FF',
          weight: 1.5,
          fillColor: '#00E5FF',
          fillOpacity: 0.22
        });
        poly80.bindTooltip('80% Calibrated Forecast Uncertainty Envelope');
        group.addLayer(poly80);
      }
    }

    // 4. Draw Predicted Trajectory
    if (showPredicted && predictionData && predictionData.fused_track) {
      const lastObs = traj[traj.length - 1];
      const predCoords: [number, number][] = [
        [lastObs.lat, lastObs.lon],
        ...predictionData.fused_track.map(p => [p.lat, p.lon] as [number, number])
      ];

      const predPolyline = L.polyline(predCoords, {
        color: '#FFAA00',
        weight: 3,
        dashArray: '6, 6',
        opacity: 0.95
      });
      group.addLayer(predPolyline);

      // Prediction waypoints
      predictionData.fused_track.forEach(pt => {
        const predCircle = L.circleMarker([pt.lat, pt.lon], {
          radius: 6,
          fillColor: '#FFAA00',
          color: '#FFFFFF',
          weight: 1.5,
          opacity: 1,
          fillOpacity: 0.9
        });

        const predPopup = `
          <div style="font-family: inherit; font-size: 12px; line-height: 1.4;">
            <div style="font-weight: bold; color: #FFAA00; border-bottom: 1px solid #1E2D4A; padding-bottom: 4px; margin-bottom: 4px;">
              Forecast Point (+${pt.lead_time_hours} Hours)
            </div>
            <div><strong>Position:</strong> ${pt.lat.toFixed(2)}°N, ${pt.lon.toFixed(2)}°E</div>
            <div><strong>Model:</strong> ${pt.method}</div>
            <div style="color: #8A99AD; font-size: 11px; margin-top: 4px;">Enclosed by empirical uncertainty cone</div>
          </div>
        `;
        predCircle.bindPopup(predPopup);
        group.addLayer(predCircle);
      });
    }

    // Pan map to fit storm bounds
    map.fitBounds(observedPolyline.getBounds(), { padding: [50, 50] });
  }, [selectedStorm, predictionData, showUncertainty, showPredicted]);

  const handleCenterOnStorm = () => {
    if (!mapInstanceRef.current || !selectedStorm || selectedStorm.trajectory.length === 0) return;
    const last = selectedStorm.trajectory[selectedStorm.trajectory.length - 1];
    mapInstanceRef.current.setView([last.lat, last.lon], 6, { animate: true });
  };

  return (
    <div className="space-y-4">
      {/* Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-cyclo-card border border-cyclo-cardBorder shadow-card">
        {/* Storm Selector */}
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-cyclo-cyan" />
          <span className="text-xs font-mono text-cyclo-muted">Select Cyclone:</span>
          <select
            value={selectedStorm?.summary.sid || ''}
            onChange={(e) => onSelectStorm(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-cyclo-darkest border border-cyclo-cardBorder text-xs font-mono text-white focus:outline-none focus:border-cyclo-cyan"
          >
            {historicalList.map((s) => (
              <option key={s.sid} value={s.sid}>
                Cyclone {s.name} ({s.season} • {s.subbasin === 'BB' ? 'Bay of Bengal' : 'Arabian Sea'})
              </option>
            ))}
          </select>
        </div>

        {/* Toggles */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            onClick={() => setShowSatellite(!showSatellite)}
            className={`px-2.5 py-1 rounded-lg border font-mono flex items-center gap-1.5 transition-all ${
              showSatellite 
                ? 'bg-cyclo-cyan/20 border-cyclo-cyan text-cyclo-cyan' 
                : 'bg-cyclo-dark border-cyclo-cardBorder text-cyclo-muted'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>NASA GIBS Overlay</span>
          </button>

          <button
            onClick={() => setShowUncertainty(!showUncertainty)}
            className={`px-2.5 py-1 rounded-lg border font-mono flex items-center gap-1.5 transition-all ${
              showUncertainty 
                ? 'bg-sky-500/20 border-sky-500 text-sky-400' 
                : 'bg-cyclo-dark border-cyclo-cardBorder text-cyclo-muted'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Uncertainty Cones (80%/95%)</span>
          </button>

          <button
            onClick={() => setShowPredicted(!showPredicted)}
            className={`px-2.5 py-1 rounded-lg border font-mono flex items-center gap-1.5 transition-all ${
              showPredicted 
                ? 'bg-amber-500/20 border-amber-500 text-amber-300' 
                : 'bg-cyclo-dark border-cyclo-cardBorder text-cyclo-muted'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Predicted Track</span>
          </button>

          <button
            onClick={handleCenterOnStorm}
            className="p-1.5 rounded-lg bg-cyclo-dark hover:bg-slate-800 border border-cyclo-cardBorder text-slate-300"
            title="Center Map on Latest Position"
          >
            <Maximize2 className="w-4 h-4" />
          </button>

          <button
            onClick={onRunPrediction}
            disabled={isPredicting}
            className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyclo-cyan to-blue-600 hover:opacity-95 text-black font-semibold font-mono text-xs shadow-glow flex items-center gap-1.5 transition-all disabled:opacity-50"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>{isPredicting ? 'Computing Forecast...' : 'Run Track AI'}</span>
          </button>
        </div>
      </div>

      {/* Map Canvas */}
      <div className="relative rounded-2xl overflow-hidden border border-cyclo-cardBorder bg-cyclo-darkest shadow-card h-[580px]">
        <div ref={mapContainerRef} className="w-full h-full" />

        {/* Floating Storm Info Box */}
        {selectedStorm && (
          <div className="absolute top-4 right-4 z-[1000] p-4 rounded-xl bg-cyclo-dark/90 backdrop-blur-md border border-cyclo-cardBorder max-w-xs space-y-2.5 shadow-card pointer-events-auto">
            <div className="flex items-center justify-between border-b border-cyclo-cardBorder/60 pb-2">
              <div>
                <h4 className="text-sm font-bold text-white font-mono flex items-center gap-1.5">
                  <Wind className="w-4 h-4 text-cyclo-cyan" />
                  Cyclone {selectedStorm.summary.name}
                </h4>
                <span className="text-[11px] text-cyclo-muted font-mono">
                  {selectedStorm.summary.subbasin === 'BB' ? 'Bay of Bengal' : 'Arabian Sea'} • {selectedStorm.summary.season}
                </span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyclo-cyan/15 text-cyclo-cyan border border-cyclo-cyan/30">
                {selectedStorm.status_label}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 rounded bg-cyclo-darkest/70 border border-cyclo-cardBorder/40">
                <span className="text-[10px] text-cyclo-muted block">Max Wind</span>
                <span className="text-sm font-bold text-sky-400">{selectedStorm.summary.max_wind_kts} kts</span>
                <span className="text-[10px] text-slate-400 block">{Math.round(selectedStorm.summary.max_wind_kts * 1.852)} km/h</span>
              </div>
              <div className="p-2 rounded bg-cyclo-darkest/70 border border-cyclo-cardBorder/40">
                <span className="text-[10px] text-cyclo-muted block">Min Pressure</span>
                <span className="text-sm font-bold text-rose-400">{selectedStorm.summary.min_pressure_hpa} hPa</span>
                <span className="text-[10px] text-slate-400 block">Deep Eyewall</span>
              </div>
            </div>

            <div className="text-[11px] text-slate-400 space-y-1 pt-1 font-mono">
              <div className="flex justify-between">
                <span>Total Observations:</span>
                <span className="text-white">{selectedStorm.summary.observation_count} points</span>
              </div>
              <div className="flex justify-between">
                <span>Start Date:</span>
                <span className="text-white">{selectedStorm.summary.start_time.slice(0, 10)}</span>
              </div>
              <div className="flex justify-between">
                <span>End Date:</span>
                <span className="text-white">{selectedStorm.summary.end_time.slice(0, 10)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Map Legend Overlay */}
        <div className="absolute bottom-4 left-4 z-[1000] p-3 rounded-xl bg-cyclo-dark/90 backdrop-blur-md border border-cyclo-cardBorder text-xs space-y-2 pointer-events-auto">
          <span className="text-[11px] font-mono text-cyclo-muted font-bold block uppercase tracking-wider">
            Meteorological Trajectory Legend
          </span>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-cyclo-cyan"></span>
              <span className="text-slate-300">Observed Track (IBTrACS)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-b border-dashed border-amber-400"></span>
              <span className="text-amber-300">AI Predicted Track (+24h)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-cyclo-cyan/30 border border-cyclo-cyan"></span>
              <span className="text-slate-300">80% Calibrated Cone</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-sky-500/15 border border-sky-500/50"></span>
              <span className="text-slate-300">95% Outer Envelope</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
