import React, { useEffect, useState } from 'react';
import { 
  Compass, 
  Activity, 
  Satellite, 
  Eye, 
  TrendingUp, 
  Layers, 
  Database, 
  AlertTriangle, 
  Cpu,
  Clock,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  apiOnline: boolean;
  isDemoMode: boolean;
  setIsDemoMode: (val: boolean) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  apiOnline,
  isDemoMode,
  setIsDemoMode
}) => {
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'overview', label: 'Overview', icon: Compass },
    { id: 'map', label: 'Cyclone Map', icon: Activity },
    { id: 'satellite', label: 'Satellite Explorer', icon: Satellite },
    { id: 'vision', label: 'AI Vision & Center', icon: Eye },
    { id: 'forecast', label: 'Track & Intensity', icon: TrendingUp },
    { id: 'fusion', label: 'Multi-Source Fusion', icon: Layers },
    { id: 'historical', label: 'Historical Archive', icon: Database },
    { id: 'risk', label: 'Risk & Impact', icon: AlertTriangle },
    { id: 'models', label: 'Model Readiness', icon: Cpu },
  ];

  return (
    <header className="sticky top-0 z-50 bg-cyclo-dark/95 backdrop-blur-md border-b border-cyclo-cardBorder">
      {/* Top Banner */}
      <div className="px-4 py-2 flex flex-wrap items-center justify-between border-b border-cyclo-cardBorder/40 text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyclo-cyan animate-ping"></span>
            <span className="font-mono text-cyclo-cyan font-semibold tracking-wider">SIH 2026 | SIH26070</span>
          </div>
          <span className="text-cyclo-muted hidden sm:inline">•</span>
          <span className="text-slate-300 font-medium hidden sm:inline">Team: MISSION_POSSIBLE</span>
          <span className="text-cyclo-muted hidden md:inline">•</span>
          <span className="text-slate-400 hidden md:inline">Theme: Disaster Management</span>
        </div>

        <div className="flex items-center gap-4">
          {/* UTC Clock */}
          <div className="flex items-center gap-1.5 text-slate-300 font-mono">
            <Clock className="w-3.5 h-3.5 text-cyclo-cyan" />
            <span>{utcTime}</span>
          </div>

          {/* Backend Status Pill */}
          <div className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border font-mono text-[11px] ${
            apiOnline 
              ? 'bg-emerald-950/50 border-emerald-500/40 text-emerald-400' 
              : 'bg-rose-950/50 border-rose-500/40 text-rose-400'
          }`}>
            {apiOnline ? (
              <>
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span>API ONLINE</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3 h-3 text-rose-400" />
                <span>API CONNECTING</span>
              </>
            )}
          </div>

          {/* Demo Mode Toggle */}
          <button
            onClick={() => setIsDemoMode(!isDemoMode)}
            className={`px-2 py-0.5 rounded border text-[11px] font-mono transition-all ${
              isDemoMode
                ? 'bg-amber-500/20 border-amber-500 text-amber-300 font-bold'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle between live providers and offline verified demonstration mode"
          >
            {isDemoMode ? 'DEMO MODE: ACTIVE' : 'LIVE / VERIFIED'}
          </button>
        </div>
      </div>

      {/* Main Navbar */}
      <div className="px-4 py-3 flex items-center justify-between">
        {/* Brand */}
        <div 
          onClick={() => setActiveTab('overview')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyclo-cyan to-blue-600 flex items-center justify-center shadow-glow group-hover:scale-105 transition-transform">
            <svg className="w-6 h-6 text-black animate-spin" style={{ animationDuration: '12s' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z" />
              <path d="M12 6a6 6 0 0 0-6 6c0 3.31 2.69 6 6 6s6-2.69 6-6" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black tracking-tight text-white font-mono">CYCLOTRACK</h1>
              <span className="px-1.5 py-0.2 bg-cyclo-cyan/20 text-cyclo-cyan text-[10px] font-mono rounded border border-cyclo-cyan/30">v1.0</span>
            </div>
            <p className="text-[11px] text-cyclo-muted">AI-Driven Digital Twin for Tropical Cyclone Prediction</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden lg:flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyclo-cyan/15 text-cyclo-cyan border border-cyclo-cyan/30 shadow-glow'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyclo-cyan' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Mobile Nav Bar */}
      <div className="lg:hidden px-2 pb-2 flex gap-1 overflow-x-auto text-xs">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded whitespace-nowrap text-[11px] font-medium ${
                isActive
                  ? 'bg-cyclo-cyan/20 text-cyclo-cyan border border-cyclo-cyan/40'
                  : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              <Icon className="w-3 h-3" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
};
