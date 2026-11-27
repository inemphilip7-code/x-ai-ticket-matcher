'use client';

import React, { useState } from 'react';
import { MonitoredKeyword, SystemStatus } from '@/types';
import { Radio, Plus, Trash2, Play, Pause, Zap, Clock, ShieldCheck, Flame } from 'lucide-react';

interface Props {
  status: SystemStatus | null;
  keywords: MonitoredKeyword[];
  onAddKeyword: (kw: string) => Promise<void>;
  onRemoveKeyword: (id: number) => Promise<void>;
  onToggleScanner: () => Promise<void>;
  onUpdateConfig: (interval: number, threshold: number) => Promise<void>;
  onTriggerManualSweep: (kw: string) => Promise<void>;
  scanning: boolean;
}

export const AutonomousControls: React.FC<Props> = ({
  status,
  keywords,
  onAddKeyword,
  onRemoveKeyword,
  onToggleScanner,
  onUpdateConfig,
  onTriggerManualSweep,
  scanning
}) => {
  const [newKw, setNewKw] = useState('');
  const [addingKw, setAddingKw] = useState(false);
  const [intervalSec, setIntervalSec] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('CUSTOM_SCAN_INTERVAL');
      if (saved) return parseInt(saved, 10);
    }
    return status?.autonomous_scanner.interval_seconds || 1500;
  });
  const [threshold, setThreshold] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('CUSTOM_SCAN_THRESHOLD');
      if (saved) return parseInt(saved, 10);
    }
    return status?.autonomous_scanner.confidence_threshold || 70;
  });

  // Dynamically sync controls with current saved settings from backend
  React.useEffect(() => {
    if (status?.autonomous_scanner) {
      if (status.autonomous_scanner.interval_seconds) {
        setIntervalSec(status.autonomous_scanner.interval_seconds);
        if (typeof window !== 'undefined') {
          localStorage.setItem('CUSTOM_SCAN_INTERVAL', status.autonomous_scanner.interval_seconds.toString());
        }
      }
      if (status.autonomous_scanner.confidence_threshold) {
        setThreshold(status.autonomous_scanner.confidence_threshold);
        if (typeof window !== 'undefined') {
          localStorage.setItem('CUSTOM_SCAN_THRESHOLD', status.autonomous_scanner.confidence_threshold.toString());
        }
      }
    }
  }, [status?.autonomous_scanner?.interval_seconds, status?.autonomous_scanner?.confidence_threshold]);

  const isRunning = status?.autonomous_scanner.is_running;

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKw.trim() || addingKw) return;
    setAddingKw(true);
    try {
      await onAddKeyword(newKw.trim());
      setNewKw('');
    } finally {
      setAddingKw(false);
    }
  };

  const handleConfigChange = (newInt: number, newThresh: number) => {
    setIntervalSec(newInt);
    setThreshold(newThresh);
    if (typeof window !== 'undefined') {
      localStorage.setItem('CUSTOM_SCAN_INTERVAL', newInt.toString());
      localStorage.setItem('CUSTOM_SCAN_THRESHOLD', newThresh.toString());
    }
    onUpdateConfig(newInt, newThresh);
  };

  return (
    <div className="space-y-4">
      {/* Top Banner: Autonomous Mode State */}
      <div className={`border rounded-2xl p-5 shadow-xl transition-all ${
        isRunning 
          ? 'bg-gradient-to-r from-[#0c1824] via-[#0f1d2c] to-[#0c141f] border-sky-500/30' 
          : 'bg-[#10141e] border-slate-800'
      }`}>
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className={`flex h-3 w-3 relative`}>
                {isRunning && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                )}
                <span className={`relative inline-flex rounded-full h-3 w-3 ${isRunning ? 'bg-sky-500' : 'bg-slate-600'}`}></span>
              </span>
              <h3 className="text-base font-bold text-white tracking-tight">
                {isRunning ? 'Autonomous X Sweeper: Active' : 'Autonomous X Sweeper: Paused'}
              </h3>
              <span className="text-[10px] uppercase tracking-wider font-extrabold px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                Zero Approval Mode
              </span>
            </div>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Continuously queries live X for buyers and sellers across all monitored keywords, performs instant AI fraud scoring, and <strong>automatically publishes tweets to X</strong> whenever confidence &ge; {threshold}%.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={onToggleScanner}
              className={`inline-flex items-center px-4 py-2 rounded-xl text-xs font-bold transition shadow-lg ${
                isRunning
                  ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40'
                  : 'bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white shadow-sky-500/20'
              }`}
            >
              {isRunning ? (
                <>
                  <Pause className="w-3.5 h-3.5 mr-1.5" />
                  Pause Auto-Scanner
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 mr-1.5" />
                  Resume Auto-Scanner
                </>
              )}
            </button>
          </div>
        </div>

        {/* Scanner Tuning Controls */}
        <div className="mt-4 pt-4 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          {/* Interval setting */}
          <div className="bg-[#0a0d14] p-3 rounded-xl border border-slate-800 flex items-center justify-between">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-sky-400" />
              Sweep Interval:
            </span>
            <select
              value={intervalSec}
              onChange={(e) => handleConfigChange(Number(e.target.value), threshold)}
              className="bg-[#141924] border border-slate-700 text-white rounded-lg px-2 py-1 font-semibold focus:outline-none"
            >
              <option value={1500}>Every 25 mins (Default)</option>
              <option value={900}>Every 15 mins</option>
              <option value={1800}>Every 30 mins</option>
              <option value={2700}>Every 45 mins</option>
              <option value={3600}>Every 60 mins</option>
              <option value={300}>Every 5 mins (Fast sweep)</option>
            </select>
          </div>

          {/* Auto-post confidence threshold */}
          <div className="bg-[#0a0d14] p-3 rounded-xl border border-slate-800 flex items-center justify-between">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Auto-Post Threshold:
            </span>
            <select
              value={threshold}
              onChange={(e) => handleConfigChange(intervalSec, Number(e.target.value))}
              className="bg-[#141924] border border-slate-700 text-white rounded-lg px-2 py-1 font-semibold focus:outline-none"
            >
              <option value={60}>&ge; 60% (Aggressive)</option>
              <option value={70}>&ge; 70% (Standard)</option>
              <option value={80}>&ge; 80% (Conservative)</option>
              <option value={90}>&ge; 90% (Strict Only)</option>
            </select>
          </div>

          {/* Instant Sweep on first keyword */}
          <div className="bg-[#0a0d14] p-3 rounded-xl border border-slate-800 flex items-center justify-between">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5 text-amber-400" />
              Manual Sweep:
            </span>
            <button
              onClick={() => keywords.length > 0 && onTriggerManualSweep(keywords[0].keyword)}
              disabled={scanning || keywords.length === 0}
              className="px-3 py-1 bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/30 rounded-lg text-xs font-semibold disabled:opacity-40 transition"
            >
              {scanning ? 'Sweeping...' : 'Sweep Now'}
            </button>
          </div>
        </div>
      </div>

      {/* Monitored Keywords Card */}
      <div className="bg-[#10141e] border border-slate-800 rounded-2xl p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
          <div>
            <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
              <span>Monitored Event Keywords on X</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                {keywords.length} active
              </span>
            </h4>
            <p className="text-xs text-slate-400">Add any concert, tour, festival, or sports match to scan automatically</p>
          </div>

          {/* Add Keyword Form */}
          <form onSubmit={handleAddSubmit} className="flex items-center gap-2 w-full sm:w-auto">
            <input
              type="text"
              value={newKw}
              onChange={(e) => setNewKw(e.target.value)}
              placeholder="e.g. Coldplay, Oasis 25, Eras..."
              className="px-3 py-1.5 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
            <button
              type="submit"
              disabled={addingKw || !newKw.trim()}
              className="px-3 py-1.5 bg-sky-500 hover:bg-sky-400 text-white rounded-xl text-xs font-semibold disabled:opacity-40 transition inline-flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add</span>
            </button>
          </form>
        </div>

        {/* Keywords chips list */}
        <div className="flex flex-wrap gap-2">
          {keywords.map((k) => (
            <div
              key={k.id}
              className="inline-flex items-center space-x-2 bg-[#141924] border border-slate-700/80 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-200 group"
            >
              <span>{k.keyword}</span>
              <button
                onClick={() => onTriggerManualSweep(k.keyword)}
                disabled={scanning}
                title={`Run instant scan for ${k.keyword}`}
                className="text-[10px] text-sky-400 hover:text-sky-300 font-normal underline ml-1"
              >
                sweep
              </button>
              <button
                onClick={() => onRemoveKeyword(k.id)}
                title="Remove keyword from monitoring"
                className="text-slate-500 hover:text-rose-400 transition"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
          {keywords.length === 0 && (
            <span className="text-xs text-slate-500 italic">No monitored keywords yet. Add one above!</span>
          )}
        </div>
      </div>
    </div>
  );
};
