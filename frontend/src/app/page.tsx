'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { StatusHeader } from '@/components/StatusHeader';
import { SellerUsernameBox } from '@/components/SellerUsernameBox';
import { AutonomousControls } from '@/components/AutonomousControls';
import { LiveActivityStream } from '@/components/LiveActivityStream';
import { MatchCard } from '@/components/MatchCard';
import { CredentialsModal } from '@/components/CredentialsModal';
import { ToastContainer, ToastMessage } from '@/components/Toast';
import { MatchRecord, SystemStatus, MonitoredKeyword, ActivityLog } from '@/types';
import { Layers, Sparkles, CheckCircle2, Clock, Filter, Radio, AlertCircle } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [matches, setMatches] = useState<MatchRecord[]>([]);
  const [keywords, setKeywords] = useState<MonitoredKeyword[]>([]);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [filter, setFilter] = useState<'all' | 'auto_posted' | 'high_confidence'>('all');
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Add toast helper
  const addToast = (type: 'success' | 'error' | 'info', title: string, description?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, title, description }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Check query params for OAuth return status
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('connected') === 'true') {
        addToast('success', 'Connected to 𝕏 Successfully!', 'Access tokens authorized and saved. Ready to comment live.');
        window.history.replaceState({}, '', '/');
      } else if (urlParams.get('error')) {
        addToast('error', 'OAuth Connection Failed', urlParams.get('error') || 'Unknown error');
        window.history.replaceState({}, '', '/');
      }
    }
  }, []);

  // Fetch all state
  const fetchData = useCallback(async () => {
    try {
      // 1. Status
      const statusRes = await fetch(`${API_BASE}/api/status`);
      if (statusRes.ok) {
        const statusData: SystemStatus = await statusRes.json();
        setStatus(statusData);
      }

      // 2. Matches
      const matchesRes = await fetch(`${API_BASE}/api/matches?limit=100`);
      if (matchesRes.ok) {
        const matchesData: MatchRecord[] = await matchesRes.json();
        setMatches(matchesData);
      }

      // 3. Monitored Keywords
      const kwRes = await fetch(`${API_BASE}/api/keywords`);
      if (kwRes.ok) {
        const kwData: MonitoredKeyword[] = await kwRes.json();
        setKeywords(kwData);
      }

      // 4. Activity Logs
      const logsRes = await fetch(`${API_BASE}/api/logs?limit=40`);
      if (logsRes.ok) {
        const logsData: ActivityLog[] = await logsRes.json();
        setLogs(logsData);
      }
    } catch (err: any) {
      console.error('Error fetching system data:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Handle Save Target Seller
  const handleSaveSeller = async (seller: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/seller`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seller_username: seller }),
      });
      if (!res.ok) throw new Error('Failed to update seller username');
      await fetchData();
      if (seller) {
        addToast('success', 'Target Seller Updated', `All buyer comments will now recommend @${seller}`);
      } else {
        addToast('info', 'Target Seller Cleared', 'Now matching with open sellers found on X.');
      }
    } catch (err: any) {
      addToast('error', 'Could not save seller', err.message);
      throw err;
    }
  };

  // Handle Add Keyword
  const handleAddKeyword = async (keyword: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/keywords`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to add keyword');
      }
      await fetchData();
      addToast('success', 'Keyword Added to Sweep', `Monitoring live X for "${keyword}"`);
    } catch (err: any) {
      addToast('error', 'Could not add keyword', err.message);
    }
  };

  // Handle Remove Keyword
  const handleRemoveKeyword = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/keywords/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to remove keyword');
      await fetchData();
      addToast('info', 'Keyword Removed', 'Stopped monitoring this keyword.');
    } catch (err: any) {
      addToast('error', 'Error removing keyword', err.message);
    }
  };

  // Handle Toggle Autonomous Scanner
  const handleToggleScanner = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scanner/toggle`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to toggle scanner');
      const data = await res.json();
      await fetchData();
      addToast(
        data.is_running ? 'success' : 'info',
        data.is_running ? 'Autonomous Auto-Posting Resumed' : 'Autonomous Auto-Posting Paused',
        data.is_running ? 'Background engine sweeps live X every 25 mins.' : 'Background sweeps paused.'
      );
    } catch (err: any) {
      addToast('error', 'Error toggling scanner', err.message);
    }
  };

  // Handle Update Scanner Config
  const handleUpdateConfig = async (interval: number, threshold: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/scanner/config?interval=${interval}&threshold=${threshold}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Failed to update config');
      await fetchData();
      const mins = Math.round(interval / 60);
      addToast('success', 'Scanner Settings Updated', `Interval: Every ${mins} mins | Auto-Post: &ge;${threshold}%`);
    } catch (err: any) {
      addToast('error', 'Error updating configuration', err.message);
    }
  };

  // Handle Manual Instant Sweep
  const handleTriggerManualSweep = async (keyword: string) => {
    setScanning(true);
    try {
      const res = await fetch(`${API_BASE}/api/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword, count: 10 }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Sweep failed.');
      }
      await fetchData();
      addToast('success', `Live Sweep Completed for "${keyword}"`, 'Checked live X for ticket buyers and sellers.');
    } catch (err: any) {
      addToast('error', 'Sweep Failed', err.message);
    } finally {
      setScanning(false);
    }
  };

  // Handle Manual Post / Retry
  const handlePost = async (matchId: number, text: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/matches/${matchId}/post`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reply_text: text }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Commenting on X failed.');
      }
      const data = await res.json();
      await fetchData();
      addToast('success', 'Commented on Live X', data.message);
    } catch (err: any) {
      addToast('error', 'Comment Dispatch Failed', err.message);
      throw err;
    }
  };

  // Handle Delete Match
  const handleDelete = async (matchId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/matches/${matchId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete match');
      await fetchData();
      addToast('info', 'Match Removed', `Candidate #${matchId} deleted.`);
    } catch (err: any) {
      addToast('error', 'Error deleting match', err.message);
    }
  };

  // Filter matches
  const filteredMatches = matches.filter((m) => {
    if (filter === 'auto_posted') return m.status === 'auto_posted' || m.status === 'approved';
    if (filter === 'high_confidence') return m.confidence_score >= 70;
    return true;
  });

  return (
    <div className="min-h-screen flex flex-col bg-[#080b10]">
      {/* Top Header */}
      <StatusHeader
        status={status}
        loading={loadingStatus}
        onRefresh={fetchData}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Real-time Notice if X credentials missing */}
        {!status?.live_x_connected && (
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start justify-between gap-4">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-amber-300">Live X Connection Incomplete</h4>
                <p className="text-xs text-slate-300 mt-0.5">
                  Connect your X Developer account to start live scanning and auto-commenting directly on buyer tweets.
                </p>
              </div>
            </div>
            <button
              onClick={() => setSettingsOpen(true)}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-black font-bold rounded-xl text-xs flex-shrink-0 transition"
            >
              Connect with 𝕏 / Keys
            </button>
          </div>
        )}

        {/* ALWAYS-VISIBLE SELLER USERNAME INPUT BOX */}
        <SellerUsernameBox
          currentSeller={status?.target_seller_username || ''}
          onSaveSeller={handleSaveSeller}
          apiUrl={API_BASE}
        />

        {/* Autonomous Scanner & Keyword Controls */}
        <AutonomousControls
          status={status}
          keywords={keywords}
          onAddKeyword={handleAddKeyword}
          onRemoveKeyword={handleRemoveKeyword}
          onToggleScanner={handleToggleScanner}
          onUpdateConfig={handleUpdateConfig}
          onTriggerManualSweep={handleTriggerManualSweep}
          scanning={scanning}
        />

        {/* Live Activity Stream Terminal */}
        <LiveActivityStream logs={logs} />

        {/* Real-time Matches Section */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="w-5 h-5 text-sky-400" />
              <h3 className="text-lg font-bold text-white tracking-tight">
                Live Discovered Matches & Dispatched Comments
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                {filteredMatches.length}
              </span>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center space-x-1.5 bg-[#10141e] p-1 rounded-xl border border-slate-800 text-xs font-medium">
              <button
                onClick={() => setFilter('all')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filter === 'all'
                    ? 'bg-sky-500 text-white font-semibold shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                All Live ({matches.length})
              </button>
              <button
                onClick={() => setFilter('auto_posted')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filter === 'auto_posted'
                    ? 'bg-emerald-600 text-white font-semibold shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Auto-Commented on X ({matches.filter((m) => m.status === 'auto_posted' || m.status === 'approved').length})
              </button>
              <button
                onClick={() => setFilter('high_confidence')}
                className={`px-3 py-1.5 rounded-lg transition ${
                  filter === 'high_confidence'
                    ? 'bg-purple-600 text-white font-semibold shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                High Conf &ge;70% ({matches.filter((m) => m.confidence_score >= 70).length})
              </button>
            </div>
          </div>

          {/* Matches List */}
          {filteredMatches.length > 0 ? (
            <div className="space-y-4">
              {filteredMatches.map((match) => (
                <MatchCard
                  key={match.id}
                  match={match}
                  onPost={handlePost}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          ) : (
            <div className="bg-[#10141e] border border-slate-800 rounded-2xl p-12 text-center space-y-4">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
                <Radio className="w-7 h-7 animate-pulse" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h4 className="text-base font-bold text-white">Autonomous scanner is sweeping live X</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Every 25 minutes, the engine checks for buyers looking for tickets to your monitored events, matches them with your target seller handle, and comments directly on their posts with unique, human-like recommendations.
                </p>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#090c12] py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>X AI Ticket-Matcher Direct Comment Bot &bull; Autonomous Secondary Market Engine</span>
          <span>FastAPI &bull; SQLite &bull; Tweepy &bull; OpenAI SDK &bull; Next.js 14 App Router</span>
        </div>
      </footer>

      {/* Credentials Modal */}
      <CredentialsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        status={status}
        onSaved={fetchData}
        apiUrl={API_BASE}
      />

      {/* Floating Notifications */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}
