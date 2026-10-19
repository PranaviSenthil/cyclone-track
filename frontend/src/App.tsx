import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { OverviewSection } from './components/OverviewSection';
import { InteractiveMapSection } from './components/InteractiveMapSection';
import { SatelliteExplorerSection } from './components/SatelliteExplorerSection';
import { AIVisionSection } from './components/AIVisionSection';
import { TrackIntensitySection } from './components/TrackIntensitySection';
import { MultiSourceFusionSection } from './components/MultiSourceFusionSection';
import { HistoricalArchiveSection } from './components/HistoricalArchiveSection';
import { RiskImpactSection } from './components/RiskImpactSection';
import { ModelReadinessSection } from './components/ModelReadinessSection';

import { api } from './services/api';
import { 
  CycloneSummary, 
  CycloneDetail, 
  ActiveCycloneResponse, 
  DataSourceStatus, 
  SatelliteLayerInfo, 
  SampleBenchmark, 
  PredictionResult, 
  ModelStatusResponse, 
  AblationConfig 
} from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [apiOnline, setApiOnline] = useState<boolean>(false);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);

  // Data states
  const [dataSources, setDataSources] = useState<DataSourceStatus[]>([]);
  const [activeData, setActiveData] = useState<ActiveCycloneResponse | null>(null);
  const [historicalList, setHistoricalList] = useState<CycloneSummary[]>([]);
  const [selectedStorm, setSelectedStorm] = useState<CycloneDetail | null>(null);
  const [satelliteLayers, setSatelliteLayers] = useState<SatelliteLayerInfo[]>([]);
  const [benchmarks, setBenchmarks] = useState<SampleBenchmark[]>([]);
  const [predictionData, setPredictionData] = useState<PredictionResult | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [ablationConfigs, setAblationConfigs] = useState<AblationConfig[]>([]);
  const [isPredicting, setIsPredicting] = useState<boolean>(false);

  // Initialize data from FastAPI backend
  useEffect(() => {
    const initApp = async () => {
      try {
        const health = await api.getHealth();
        if (health.status === 'HEALTHY') {
          setApiOnline(true);
        }

        // Fetch core datasets concurrently
        const [sources, active, historical, satAvail, models, metrics] = await Promise.all([
          api.getDataSources().catch(() => []),
          api.getActiveCyclones().catch(() => null),
          api.getHistoricalCyclones().catch(() => []),
          api.getSatelliteAvailable().catch(() => null),
          api.getModelsStatus().catch(() => null),
          api.getModelsMetrics().catch(() => null)
        ]);

        setDataSources(sources);
        setActiveData(active);
        setHistoricalList(historical);
        if (satAvail) {
          setSatelliteLayers(satAvail.layers || []);
          setBenchmarks(satAvail.sample_benchmarks || []);
        }
        setModelStatus(models);
        if (metrics?.fusion_ablation_study?.configurations) {
          setAblationConfigs(metrics.fusion_ablation_study.configurations);
        }

        // Default load Cyclone BIPARJOY
        const defaultStormId = 'BIPARJOY';
        const stormDetail = await api.getCycloneById(defaultStormId).catch(() => null);
        if (stormDetail) {
          setSelectedStorm(stormDetail);
          // Run initial prediction for default storm
          runStormPrediction(stormDetail);
        }
      } catch (err) {
        console.warn('Initial backend connection failed, falling back to local defaults:', err);
        setApiOnline(false);
      }
    };

    initApp();
  }, []);

  const runStormPrediction = async (storm: CycloneDetail) => {
    setIsPredicting(true);
    try {
      const pred = await api.predictCyclone({
        stormId: storm.summary.name,
        trajectoryHistory: storm.trajectory.slice(-6),
        currentWindKts: storm.summary.max_wind_kts,
        currentPressureHpa: storm.summary.min_pressure_hpa
      });
      setPredictionData(pred);
    } catch (err) {
      console.error('Failed to run cyclone prediction:', err);
    } finally {
      setIsPredicting(false);
    }
  };

  const handleSelectStorm = async (stormId: string) => {
    try {
      const detail = await api.getCycloneById(stormId);
      setSelectedStorm(detail);
      runStormPrediction(detail);
    } catch (err) {
      console.error(`Failed to load storm ${stormId}:`, err);
    }
  };

  return (
    <div className="min-h-screen bg-cyclo-darkest flex flex-col selection:bg-cyclo-cyan selection:text-black">
      {/* Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        apiOnline={apiOnline}
        isDemoMode={isDemoMode}
        setIsDemoMode={setIsDemoMode}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'overview' && (
          <OverviewSection
            dataSources={dataSources}
            activeData={activeData}
            models={modelStatus?.models || []}
            selectedStorm={selectedStorm}
            onSelectStorm={handleSelectStorm}
            onNavigate={setActiveTab}
            isDemoMode={isDemoMode}
          />
        )}

        {activeTab === 'map' && (
          <InteractiveMapSection
            selectedStorm={selectedStorm}
            historicalList={historicalList}
            onSelectStorm={handleSelectStorm}
            predictionData={predictionData}
            onRunPrediction={() => selectedStorm && runStormPrediction(selectedStorm)}
            isPredicting={isPredicting}
          />
        )}

        {activeTab === 'satellite' && (
          <SatelliteExplorerSection
            layers={satelliteLayers}
            benchmarks={benchmarks}
            providerStatus={dataSources}
          />
        )}

        {activeTab === 'vision' && (
          <AIVisionSection benchmarks={benchmarks} />
        )}

        {activeTab === 'forecast' && (
          <TrackIntensitySection
            selectedStorm={selectedStorm}
            predictionData={predictionData}
            onRunPrediction={() => selectedStorm && runStormPrediction(selectedStorm)}
            isPredicting={isPredicting}
          />
        )}

        {activeTab === 'fusion' && (
          <MultiSourceFusionSection ablationConfigs={ablationConfigs} />
        )}

        {activeTab === 'historical' && (
          <HistoricalArchiveSection
            historicalList={historicalList}
            selectedStorm={selectedStorm}
            onSelectStorm={handleSelectStorm}
            onNavigateToMap={() => setActiveTab('map')}
          />
        )}

        {activeTab === 'risk' && (
          <RiskImpactSection
            selectedStorm={selectedStorm}
            predictionData={predictionData}
          />
        )}

        {activeTab === 'models' && (
          <ModelReadinessSection modelStatus={modelStatus} />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-cyclo-dark border-t border-cyclo-cardBorder py-6 px-4 text-xs font-mono text-cyclo-muted">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div>
            <div className="text-white font-bold">CYCLOTRACK — SIH26070 Prototype</div>
            <div className="text-[11px] text-slate-400">Team MISSION_POSSIBLE • Smart India Hackathon 2026</div>
          </div>
          <div className="text-[11px] max-w-md text-slate-400">
            Research and decision support twin. Multi-source fusion combining NASA GIBS, ISRO MOSDAC adapter, and NOAA IBTrACS.
          </div>
          <div className="text-[10px] text-slate-500">
            PyTorch 2.10 • Leaflet • FastAPI • React 19
          </div>
        </div>
      </footer>
    </div>
  );
}
export default App;
