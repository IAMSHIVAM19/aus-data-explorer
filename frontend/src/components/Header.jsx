import React from 'react';
import { TrendingUp, Database, Settings2 } from 'lucide-react';

export default function Header({ apiKey, onOpenSettings, healthInfo }) {
  const totalObs = healthInfo?.database?.total_observations
    ? `${Math.round(healthInfo.database.total_observations / 1000)}k`
    : '489k';

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-lg text-slate-900 tracking-tight">Aus Gov Data Explorer</h1>
              <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded-full border border-emerald-200">
                ABS 6202.0
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Grounded Natural Language Analytics on Australian Labour Force Statistics
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden md:flex items-center text-xs text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
            <Database className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
            <span>{totalObs} Observations (1978 – 2026)</span>
          </div>

          <button
            onClick={onOpenSettings}
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
          >
            <Settings2 className="w-4 h-4 text-slate-500" />
            <span>{apiKey ? 'OpenRouter Active' : 'Model Settings'}</span>
            {apiKey && <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>}
          </button>
        </div>
      </div>
    </header>
  );
}
