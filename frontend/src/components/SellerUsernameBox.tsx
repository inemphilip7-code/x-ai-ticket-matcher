'use client';

import React, { useState, useEffect } from 'react';
import { UserCheck, AtSign, Check, Save, Sparkles, XCircle } from 'lucide-react';

interface Props {
  currentSeller: string;
  onSaveSeller: (seller: string) => Promise<void>;
  apiUrl: string;
}

export const SellerUsernameBox: React.FC<Props> = ({ currentSeller, onSaveSeller, apiUrl }) => {
  const [handle, setHandle] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('CUSTOM_SELLER_HANDLE');
      if (saved !== null) return saved;
    }
    return currentSeller || '';
  });
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    setHandle(currentSeller || '');
    if (typeof window !== 'undefined' && currentSeller !== undefined) {
      localStorage.setItem('CUSTOM_SELLER_HANDLE', currentSeller);
    }
  }, [currentSeller]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setSavedSuccess(false);
    try {
      const clean = handle.trim().replace(/^@/, '');
      await onSaveSeller(clean);
      if (typeof window !== 'undefined') {
        localStorage.setItem('CUSTOM_SELLER_HANDLE', clean);
      }
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    if (saving) return;
    setSaving(true);
    try {
      await onSaveSeller('');
      setHandle('');
      if (typeof window !== 'undefined') {
        localStorage.setItem('CUSTOM_SELLER_HANDLE', '');
      }
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } finally {
      setSaving(false);
    }
  };

  const cleanHandle = handle.trim().replace(/^@/, '');

  return (
    <div className="bg-[#10141e] border border-sky-500/20 rounded-2xl p-5 shadow-xl">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Left Explanation */}
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <UserCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Target Seller Account (@username) &bull; Optional
            </h3>
            {cleanHandle ? (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                Active Seller: @{cleanHandle}
              </span>
            ) : (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                No Account Required &bull; Open Market Mode
              </span>
            )}
          </div>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            Enter an 𝕏 handle to recommend in comments, or leave empty if you don&apos;t want to promote a specific account. You can change or clear this anytime dynamically.
          </p>
        </div>

        {/* Input Box Form */}
        <form onSubmit={handleSubmit} className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <AtSign className="w-4 h-4 text-sky-400" />
            </div>
            <input
              type="text"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              placeholder="e.g. MyTickets or leave blank"
              className="w-full pl-9 pr-3 py-2 bg-[#090c12] border border-slate-700 rounded-xl text-xs font-semibold text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-semibold rounded-xl text-xs transition shadow-md shadow-sky-500/20 disabled:opacity-50 inline-flex items-center gap-1.5 flex-shrink-0"
          >
            {savedSuccess ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-300" />
                <span>Saved!</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? 'Saving...' : 'Set Seller'}</span>
              </>
            )}
          </button>

          {cleanHandle && (
            <button
              type="button"
              onClick={handleClear}
              disabled={saving}
              title="Clear seller handle (Open market mode)"
              className="px-3 py-2 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white rounded-xl text-xs transition inline-flex items-center gap-1 flex-shrink-0"
            >
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
              <span>Clear</span>
            </button>
          )}
        </form>
      </div>

      {/* Live Preview Box */}
      {cleanHandle ? (
        <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Target seller comment preview:</span>
            <code className="text-slate-200 bg-[#0b0e15] px-2 py-0.5 rounded border border-slate-800 font-mono">
              Hey! Check with @{cleanHandle}, they have tickets available.
            </code>
          </span>
        </div>
      ) : (
        <div className="mt-3 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            <span>Open market mode active:</span>
            <code className="text-slate-200 bg-[#0b0e15] px-2 py-0.5 rounded border border-slate-800 font-mono">
              The bot matches buyers with open verified sellers found on X without promoting any fixed handle.
            </code>
          </span>
        </div>
      )}
    </div>
  );
};
