'use client';

import React, { useState } from 'react';
import { Search, Loader2, Sparkles, AlertCircle, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface Props {
  onScan: (keyword: string, autoPost: boolean) => void;
  scanning: boolean;
  stats: {
    total_matches: number;
    pending: number;
    posted: number;
    high_confidence: number;
  } | undefined;
}

const PRESET_KEYWORDS = [
  'Coldplay World Tour',
  'Oasis Live 25',
  'Taylor Swift Eras',
  'Coachella 2025',
  'Champions League Final'
];

export const SearchBar: React.FC<Props> = ({ onScan, scanning, stats }) => {
  const [keyword, setKeyword] = useState('Coldplay World Tour');
  const [autoPost, setAutoPost] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword.trim() || scanning) return;
    onScan(keyword.trim(), autoPost);
  };

  return (
    <div className="space-y-4">
      {/* Search Input Card */}
      <div className="bg-[#10141e] border border-slate-800 rounded-2xl p-5 shadow-xl shadow-black/40">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col md:flex-row items-stretch gap-3">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-400" />
              </div>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="Enter event, artist, or team keyword (e.g., Coldplay, Oasis 25, Eras Tour)..."
                disabled={scanning}
                className="block w-full pl-11 pr-4 py-3.5 bg-[#0b0e15] border border-slate-700/80 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent text-sm font-medium transition"
              />
            </div>

            <button
              type="submit"
              disabled={scanning || !keyword.trim()}
              className="inline-flex items-center justify-center px-6 py-3.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-sm transition-all shadow-lg shadow-sky-500/25 active:scale-[0.98]"
            >
              {scanning ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Scanning X & Matching...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Scan X & Match
                </>
              )}
            </button>
          </div>

          {/* Quick presets & Auto-post Toggle */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1 border-t border-slate-800/60">
            {/* Presets */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-slate-500 font-medium mr-1">Trending:</span>
              {PRESET_KEYWORDS.map((kw) => (
                <button
                  key={kw}
                  type="button"
                  disabled={scanning}
                  onClick={() => setKeyword(kw)}
                  className={`text-xs px-2.5 py-1 rounded-lg border transition ${
                    keyword === kw
                      ? 'bg-sky-500/20 text-sky-300 border-sky-500/40 font-semibold'
                      : 'bg-[#141923] text-slate-400 border-slate-800 hover:text-white hover:border-slate-700'
                  }`}
                >
                  {kw}
                </button>
              ))}
            </div>

            {/* Auto-post toggle (Human in the loop safety) */}
            <label className="flex items-center space-x-2.5 cursor-pointer select-none group bg-[#141923] px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700 transition">
              <input
                type="checkbox"
                checked={autoPost}
                onChange={(e) => setAutoPost(e.target.checked)}
                disabled={scanning}
                className="w-4 h-4 rounded bg-[#0b0e15] border-slate-600 text-sky-500 focus:ring-sky-500 focus:ring-offset-0 focus:ring-1"
              />
              <span className="text-xs text-slate-300 font-medium group-hover:text-white">
                Auto-post AI replies when confidence &ge; 70%
              </span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                autoPost ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-400'
              }`}>
                {autoPost ? 'AUTO' : 'HITL'}
              </span>
            </label>
          </div>
        </form>
      </div>

      {/* Metrics Row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-[#10141e] border border-slate-800/80 rounded-xl p-3.5">
            <div className="text-xs text-slate-400 font-medium">Total Matches</div>
            <div className="text-xl font-bold text-white mt-0.5">{stats.total_matches}</div>
          </div>
          <div className="bg-[#10141e] border border-slate-800/80 rounded-xl p-3.5">
            <div className="text-xs text-amber-400/90 font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
              Pending Approval
            </div>
            <div className="text-xl font-bold text-amber-300 mt-0.5">{stats.pending}</div>
          </div>
          <div className="bg-[#10141e] border border-slate-800/80 rounded-xl p-3.5">
            <div className="text-xs text-emerald-400/90 font-medium flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              Posted on X
            </div>
            <div className="text-xl font-bold text-emerald-300 mt-0.5">{stats.posted}</div>
          </div>
          <div className="bg-[#10141e] border border-slate-800/80 rounded-xl p-3.5">
            <div className="text-xs text-purple-400/90 font-medium flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-purple-400" />
              High Confidence (&ge;70%)
            </div>
            <div className="text-xl font-bold text-purple-300 mt-0.5">{stats.high_confidence}</div>
          </div>
        </div>
      )}
    </div>
  );
};
