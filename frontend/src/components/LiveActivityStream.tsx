'use client';

import React from 'react';
import { ActivityLog } from '@/types';
import { Terminal, CheckCircle2, AlertCircle, Info, AlertTriangle, Clock } from 'lucide-react';

interface Props {
  logs: ActivityLog[];
  onClear?: () => void;
}

export const LiveActivityStream: React.FC<Props> = ({ logs }) => {
  return (
    <div className="bg-[#0b0e15] border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
      {/* Terminal Title Bar */}
      <div className="bg-[#121622] px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-bold text-slate-200 tracking-wide font-mono">
            LIVE X ACTIVITY & AUTO-POST DISPATCH STREAM
          </span>
          <span className="relative flex h-2 w-2 ml-1">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        </div>
        <span className="text-[11px] font-mono text-slate-500">
          Showing latest {logs.length} events
        </span>
      </div>

      {/* Logs Window */}
      <div className="p-4 space-y-2 font-mono text-xs max-h-72 overflow-y-auto">
        {logs.length > 0 ? (
          logs.map((log) => (
            <div
              key={log.id}
              className={`p-2 rounded-lg border flex items-start space-x-2.5 transition-colors ${
                log.level === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                  : log.level === 'error'
                  ? 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                  : log.level === 'warning'
                  ? 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                  : 'bg-[#121622] border-slate-800 text-slate-300'
              }`}
            >
              <div className="flex-shrink-0 mt-0.5">
                {log.level === 'success' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                {log.level === 'error' && <AlertCircle className="w-3.5 h-3.5 text-rose-400" />}
                {log.level === 'warning' && <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                {log.level === 'info' && <Info className="w-3.5 h-3.5 text-sky-400" />}
              </div>
              <div className="flex-1 space-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{log.message}</span>
                  <span className="text-[10px] text-slate-500">{log.timestamp.split(' ')[1] || log.timestamp}</span>
                </div>
                {log.details && (
                  <p className="text-[11px] opacity-80 break-all">{log.details}</p>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="py-6 text-center text-slate-500 italic text-xs">
            Autonomous background sweep waiting for next cycle... Live stream will display events here.
          </div>
        )}
      </div>
    </div>
  );
};
