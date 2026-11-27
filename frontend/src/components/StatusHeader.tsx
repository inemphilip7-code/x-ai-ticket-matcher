'use client';

import React from 'react';
import { SystemStatus } from '@/types';
import { Sparkles, Key, Zap, RefreshCw, Radio, CheckCircle2, AlertTriangle } from 'lucide-react';

interface Props {
  status: SystemStatus | null;
  loading: boolean;
  onRefresh: () => void;
  onOpenSettings: () => void;
}

export const StatusHeader: React.FC<Props> = ({ status, loading, onRefresh, onOpenSettings }) => {
  const isXConnected = status?.live_x_connected;
  const isScannerRunning = status?.autonomous_scanner.is_running;

  return (
    <header className="border-b border-slate-800 bg-[#0d1118]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <span className="text-white font-extrabold text-xl tracking-tighter">𝕏</span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold text-white tracking-tight">AI Ticket-Matcher Bot</h1>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
                Real-Time Autonomous
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous live X secondary market search, AI fraud analysis & automatic replies</p>
          </div>
        </div>

        {/* Realtime Status Badges & Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Live X Connection Status */}
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-semibold ${
            isXConnected
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-slate-800/80 border-slate-700 text-slate-300'
          }`}>
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isXConnected ? 'bg-emerald-400' : 'bg-slate-400'
              }`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${
                isXConnected ? 'bg-emerald-500' : 'bg-slate-500'
              }`}></span>
            </span>
            <span>{isXConnected ? 'Live X Active' : (loading ? 'Connecting...' : 'Live X Ready')}</span>
          </div>

          {/* Autonomous Scanner Indicator */}
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${
            isScannerRunning
              ? 'bg-sky-500/10 border-sky-500/30 text-sky-300'
              : 'bg-slate-800/80 border-slate-700 text-slate-400'
          }`}>
            <Radio className={`w-3.5 h-3.5 ${isScannerRunning ? 'text-sky-400 animate-pulse' : 'text-slate-500'}`} />
            <span>
              {isScannerRunning
                ? `Auto-Scanner: Every ${Math.round((status?.autonomous_scanner.interval_seconds || 300) / 60)}m`
                : 'Auto-Scanner Paused'}
            </span>
          </div>

          {/* AI Status */}
          <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium bg-[#141923] border-slate-700/80">
            {status?.ai_configured ? (
              <>
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-purple-300 font-semibold">AI ({status.ai_model})</span>
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-cyan-300">Rule-Based Fallback</span>
              </>
            )}
          </div>

          {/* Settings / API Keys Button */}
          <button
            onClick={onOpenSettings}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-[#141923] hover:bg-slate-800 text-xs text-slate-300 hover:text-white font-medium transition"
          >
            <Key className="w-3.5 h-3.5 text-amber-400" />
            <span>Settings / Keys</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1.5 rounded-lg border border-slate-700/80 bg-[#141923] hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh Realtime Status"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
