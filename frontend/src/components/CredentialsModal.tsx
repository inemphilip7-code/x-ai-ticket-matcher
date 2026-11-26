'use client';

import React, { useState } from 'react';
import { SystemStatus } from '@/types';
import { X, Key, ShieldCheck, Check, AlertCircle, Save, ExternalLink, HelpCircle, Sparkles, Radio } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  status: SystemStatus | null;
  onSaved: () => void;
  apiUrl: string;
}

export const CredentialsModal: React.FC<Props> = ({ isOpen, onClose, status, onSaved, apiUrl }) => {
  const [activeTab, setActiveTab] = useState<'oauth2' | 'oauth1' | 'direct' | 'gemini' | 'deploy'>('oauth2');
  
  // Credentials state
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [bearerToken, setBearerToken] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [accessTokenSecret, setAccessTokenSecret] = useState('');
  
  // Gemini AI state
  const [geminiKey, setGeminiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState(status?.ai_model || 'gemini-1.5-flash');
  
  const [saving, setSaving] = useState(false);
  const [connectingOAuth, setConnectingOAuth] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isOpen) return null;

  // 1-Click Connect with X OAuth Flow
  const handleConnectWithX = async () => {
    setMsg(null);
    setConnectingOAuth(true);
    try {
      // 1. Save whatever keys were entered first
      const payload: any = {};
      if (clientId.trim()) payload.twitter_client_id = clientId.trim();
      if (clientSecret.trim()) payload.twitter_client_secret = clientSecret.trim();
      if (apiKey.trim()) payload.twitter_api_key = apiKey.trim();
      if (apiSecret.trim()) payload.twitter_api_secret = apiSecret.trim();
      if (bearerToken.trim()) payload.twitter_bearer_token = bearerToken.trim();

      if (Object.keys(payload).length > 0) {
        await fetch(`${apiUrl}/api/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      // 2. Request Authorization URL from backend
      const res = await fetch(`${apiUrl}/api/auth/twitter/connect`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not initiate X OAuth. Check your Client ID or API Key.');
      }
      const data = await res.json();
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message });
      setConnectingOAuth(false);
    }
  };

  const handleSubmitManual = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const payload: any = {};
      if (clientId.trim()) payload.twitter_client_id = clientId.trim();
      if (clientSecret.trim()) payload.twitter_client_secret = clientSecret.trim();
      if (apiKey.trim()) payload.twitter_api_key = apiKey.trim();
      if (apiSecret.trim()) payload.twitter_api_secret = apiSecret.trim();
      if (bearerToken.trim()) payload.twitter_bearer_token = bearerToken.trim();
      if (accessToken.trim()) payload.twitter_access_token = accessToken.trim();
      if (accessTokenSecret.trim()) payload.twitter_access_token_secret = accessTokenSecret.trim();
      if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();
      if (geminiModel.trim()) payload.gemini_model = geminiModel.trim();

      const res = await fetch(`${apiUrl}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error('Failed to update credentials');
      setMsg({ type: 'success', text: 'Saved! Configuration applied live to the bot.' });
      setTimeout(() => {
        onSaved();
        onClose();
      }, 1000);
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message || 'Failed to save configuration' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-[#0f131c] border border-slate-700/80 rounded-2xl p-6 shadow-2xl overflow-y-auto max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">𝕏 Connection & Google Gemini AI Setup</h3>
              <p className="text-xs text-slate-400">Where to find your tokens on X and configure Gemini AI</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Navigation Tabs */}
        <div className="flex border-b border-slate-800 mt-4 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('oauth2')}
            className={`pb-2.5 px-3 border-b-2 transition ${
              activeTab === 'oauth2'
                ? 'border-sky-500 text-sky-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            1. 1-Click Connect (OAuth 2.0)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('oauth1')}
            className={`pb-2.5 px-3 border-b-2 transition ${
              activeTab === 'oauth1'
                ? 'border-sky-500 text-sky-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            2. API Keys (OAuth 1.0a)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('direct')}
            className={`pb-2.5 px-3 border-b-2 transition ${
              activeTab === 'direct'
                ? 'border-sky-500 text-sky-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            3. Direct Tokens
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('gemini')}
            className={`pb-2.5 px-3 border-b-2 transition ${
              activeTab === 'gemini'
                ? 'border-purple-500 text-purple-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            4. Google Gemini AI ✨
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('deploy')}
            className={`pb-2.5 px-3 border-b-2 transition ${
              activeTab === 'deploy'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            5. Render + Vercel Guide 🚀
          </button>
        </div>

        {msg && (
          <div className={`mt-3 p-3 rounded-xl border text-xs flex items-center space-x-2 ${
            msg.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}>
            {msg.type === 'success' ? <Check className="w-4 h-4 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
            <span>{msg.text}</span>
          </div>
        )}

        {/* TAB 1: 1-Click Connect (OAuth 2.0 PKCE) */}
        {activeTab === 'oauth2' && (
          <div className="mt-4 space-y-4">
            <div className="p-4 rounded-xl bg-gradient-to-r from-sky-950/50 via-[#101b2a] to-[#0c1320] border border-sky-500/30 space-y-3">
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-sm text-white">Where do I find my Client ID on X?</span>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-bold">
                  Fastest Option
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                In the X Developer Portal, you only need <strong>ONE</strong> value: your <strong>Client ID</strong>!
              </p>
              
              <div className="bg-[#090c12] p-3 rounded-lg border border-slate-800 text-[11px] text-slate-300 space-y-1.5 font-mono">
                <div className="text-sky-300 font-bold font-sans flex items-center justify-between">
                  <span>Exact steps on developer.x.com:</span>
                  <a
                    href="https://developer.x.com/en/portal/dashboard"
                    target="_blank"
                    rel="noreferrer"
                    className="text-sky-400 hover:text-sky-300 underline font-normal font-sans inline-flex items-center gap-1"
                  >
                    Open Developer Portal <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div>1. Click <strong className="text-white">Projects & Apps</strong> &rarr; click your App.</div>
                <div>2. Under <strong className="text-white">User authentication settings</strong> &rarr; click <strong className="text-sky-300">Set up</strong> (or Edit).</div>
                <div>3. Set Permissions to <strong className="text-emerald-400">Read and write</strong>, App type to <strong className="text-white">Web App</strong>, and Redirect URL to:</div>
                <div className="bg-slate-900 p-1.5 rounded text-sky-400 select-all font-bold">
                  {apiUrl ? `${apiUrl.replace(/\/$/, '')}/api/auth/twitter/callback` : 'http://localhost:8000/api/auth/twitter/callback'}
                </div>
                <div className="text-[10px] text-slate-400">
                  (When deployed on Render, this automatically becomes <code className="text-emerald-400">https://your-backend.onrender.com/api/auth/twitter/callback</code>)
                </div>
                <div>4. Click Save, then copy the <strong className="text-amber-300">OAuth 2.0 Client ID</strong> shown on the confirmation screen!</div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-200 mb-1">
                  Paste OAuth 2.0 Client ID:
                </label>
                <input
                  type="text"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder={status?.credentials.has_client_id ? '•••••••••••• (Saved in .env)' : 'e.g. TG1vOG5hNlB6...'}
                  className="w-full px-3.5 py-2.5 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
                />
              </div>

              <div className="pt-2 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">
                  Ready? Click to open X's official sign-in page:
                </span>
                <button
                  type="button"
                  onClick={handleConnectWithX}
                  disabled={connectingOAuth || (!clientId.trim() && !status?.credentials.has_client_id)}
                  className="px-5 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold rounded-xl text-xs transition shadow-lg shadow-sky-500/20 disabled:opacity-40 inline-flex items-center space-x-1.5"
                >
                  <span className="font-extrabold text-sm">𝕏</span>
                  <span>{connectingOAuth ? 'Redirecting to 𝕏...' : 'Connect with 𝕏'}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Consumer Keys (OAuth 1.0a) */}
        {activeTab === 'oauth1' && (
          <div className="mt-4 space-y-4">
            <div className="p-3.5 rounded-xl bg-[#141924] border border-slate-800 text-xs space-y-2">
              <span className="text-sky-300 font-bold">Where to find Consumer Keys:</span>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                In your App on <a href="https://developer.x.com/en/portal/dashboard" target="_blank" rel="noreferrer" className="text-sky-400 underline">developer.x.com</a>, click the <strong>"Keys and Tokens"</strong> tab &rarr; under <strong>Consumer Keys</strong>, click <strong>"Regenerate"</strong> to see your <strong>API Key</strong> and <strong>API Key Secret</strong>.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  API Key (Consumer Key)
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={status?.credentials.has_api_key ? '•••••••••••• (Saved)' : 'Enter API Key...'}
                  className="w-full px-3.5 py-2 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  API Key Secret (Consumer Secret)
                </label>
                <input
                  type="password"
                  value={apiSecret}
                  onChange={(e) => setApiSecret(e.target.value)}
                  placeholder={status?.credentials.has_api_secret ? '•••••••••••• (Saved)' : 'Enter API Secret...'}
                  className="w-full px-3.5 py-2 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
                />
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleConnectWithX}
                disabled={connectingOAuth || (!apiKey.trim() && !status?.credentials.has_api_key)}
                className="px-5 py-2.5 bg-sky-500 hover:bg-sky-400 text-white font-bold rounded-xl text-xs transition shadow-md disabled:opacity-40"
              >
                {connectingOAuth ? 'Opening Auth...' : 'Connect with 𝕏 via API Key'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: Direct Manual Tokens */}
        {activeTab === 'direct' && (
          <form onSubmit={handleSubmitManual} className="mt-4 space-y-3">
            <div className="p-3.5 rounded-xl bg-[#141924] border border-slate-800 text-xs space-y-1">
              <span className="text-slate-200 font-bold">Already generated tokens manually?</span>
              <p className="text-slate-400 text-[11px]">
                Under <strong>Keys and Tokens</strong> on developer.x.com, you can directly generate your Bearer Token and User Access Token & Secret, and paste them here without using the Connect button:
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Bearer Token <span className="text-slate-500 font-normal">(Used for live search & buyer detection)</span>
              </label>
              <input
                type="password"
                value={bearerToken}
                onChange={(e) => setBearerToken(e.target.value)}
                placeholder={status?.credentials.has_bearer_token ? '•••••••••••••••••••••••• (Active)' : 'Paste Bearer Token...'}
                className="w-full px-3.5 py-2 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Access Token
                </label>
                <input
                  type="password"
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  placeholder={status?.credentials.has_access_token ? '•••••••••••• (Active)' : 'Paste Access Token...'}
                  className="w-full px-3.5 py-2 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Access Token Secret
                </label>
                <input
                  type="password"
                  value={accessTokenSecret}
                  onChange={(e) => setAccessTokenSecret(e.target.value)}
                  placeholder={status?.credentials.has_access_token_secret ? '•••••••••••• (Active)' : 'Paste Token Secret...'}
                  className="w-full px-3.5 py-2 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500 font-mono"
                />
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2 bg-sky-500 hover:bg-sky-400 text-white font-bold rounded-xl text-xs transition shadow-md disabled:opacity-40"
              >
                {saving ? 'Saving...' : 'Save Manual Tokens'}
              </button>
            </div>
          </form>
        )}

        {/* TAB 4: Google Gemini AI Settings */}
        {activeTab === 'gemini' && (
          <form onSubmit={handleSubmitManual} className="mt-4 space-y-4">
            <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/50 via-[#191124] to-[#120d1a] border border-purple-500/30 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-extrabold text-sm text-purple-300 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  Google Gemini AI Engine
                </span>
                <a
                  href="https://aistudio.google.com/app/apikey"
                  target="_blank"
                  rel="noreferrer"
                  className="text-purple-300 hover:text-purple-200 underline text-xs font-semibold inline-flex items-center gap-1"
                >
                  Get Free Gemini API Key <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Powered by Google Gemini 1.5 Flash. Analyzes buyer tweets for ticket requests, ensures unique non-repetitive comments, and strictly excludes buyer usernames & payment methods.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Google Gemini API Key
                </label>
                <input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder={status?.ai_configured ? '•••••••••••• (Gemini Active)' : 'Paste Gemini API Key...'}
                  className="w-full px-3.5 py-2.5 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-purple-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Gemini Model
                </label>
                <input
                  type="text"
                  value={geminiModel}
                  onChange={(e) => setGeminiModel(e.target.value)}
                  placeholder="gemini-1.5-flash"
                  className="w-full px-3.5 py-2.5 bg-[#090c12] border border-slate-700 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none focus:ring-1 focus:ring-purple-500 font-mono"
                />
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold rounded-xl text-xs transition shadow-md shadow-purple-500/20 disabled:opacity-40"
              >
                {saving ? 'Saving...' : 'Save Gemini AI Configuration'}
              </button>
            </div>
          </form>
        )}

        {/* TAB 5: Render + Vercel Deployment & UptimeRobot Guide */}
        {activeTab === 'deploy' && (
          <div className="mt-4 space-y-4 text-xs">
            {/* Vercel Frontend Box */}
            <div className="p-4 rounded-xl bg-[#101b2a] border border-sky-500/30 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-sky-400"></span>
                  1. Deploy Frontend on Vercel
                </span>
                <span className="text-[10px] text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20 font-mono">vercel.com</span>
              </div>
              <p className="text-slate-300">
                Push the <code className="text-white">frontend/</code> directory to GitHub and import it on Vercel.
              </p>
              <div className="bg-[#090c12] p-2.5 rounded-lg border border-slate-800 space-y-1">
                <div className="text-slate-400 font-semibold">Required Environment Variable on Vercel:</div>
                <div className="font-mono text-sky-300 text-[11px] select-all">
                  NEXT_PUBLIC_API_URL = https://your-backend.onrender.com
                </div>
              </div>
            </div>

            {/* Render Backend Box */}
            <div className="p-4 rounded-xl bg-[#151b1e] border border-emerald-500/30 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  2. Deploy Backend on Render
                </span>
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-mono">render.com</span>
              </div>
              <p className="text-slate-300">
                Create a new <strong>Web Service</strong> connected to your repo (Root Directory: <code className="text-white">backend</code>).
              </p>
              <div className="bg-[#090c12] p-2.5 rounded-lg border border-slate-800 space-y-1 font-mono text-[11px]">
                <div><span className="text-slate-400 font-sans font-semibold">Build Command:</span> <span className="text-emerald-300">pip install -r requirements.txt</span></div>
                <div><span className="text-slate-400 font-sans font-semibold">Start Command:</span> <span className="text-emerald-300">uvicorn main:app --host 0.0.0.0 --port $PORT</span></div>
                <div className="pt-1 text-slate-400 font-sans font-semibold">Recommended Env Vars on Render:</div>
                <div className="text-emerald-400 select-all">BACKEND_URL=https://your-backend.onrender.com</div>
                <div className="text-emerald-400 select-all">FRONTEND_URL=https://your-frontend.vercel.app</div>
                <div className="text-emerald-400 select-all">CORS_ORIGIN=https://your-frontend.vercel.app</div>
              </div>
            </div>

            {/* UptimeRobot Health Check Keepalive */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-amber-950/40 to-[#19150e] border border-amber-500/30 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-amber-300 text-sm flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                  3. Keep Alive 24/7 with UptimeRobot
                </span>
                <a
                  href="https://uptimerobot.com"
                  target="_blank"
                  rel="noreferrer"
                  className="text-amber-400 hover:text-amber-300 underline text-xs font-semibold inline-flex items-center gap-1"
                >
                  uptimerobot.com <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <p className="text-slate-300 leading-relaxed">
                Render free tier spins down after 15 minutes of inactivity. Add an UptimeRobot monitor to ping your health API every 5 minutes so your 25-minute autonomous ticket sweeps never sleep!
              </p>
              <div className="bg-[#090c12] p-2.5 rounded-lg border border-slate-800 space-y-1.5 font-mono text-[11px]">
                <div><span className="text-slate-400 font-sans font-semibold">Monitor Type:</span> <span className="text-amber-300">HTTP(s)</span></div>
                <div><span className="text-slate-400 font-sans font-semibold">URL to Monitor:</span></div>
                <div className="p-1 bg-slate-900 rounded text-amber-400 select-all font-bold">
                  {apiUrl ? `${apiUrl.replace(/\/$/, '')}/health` : 'https://your-backend.onrender.com/health'}
                </div>
                <div><span className="text-slate-400 font-sans font-semibold">Monitoring Interval:</span> <span className="text-amber-300">Every 5 minutes</span></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
