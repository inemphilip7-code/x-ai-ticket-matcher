'use client';

import React, { useState } from 'react';
import { MatchRecord } from '@/types';
import { 
  MessageSquare, 
  CheckCircle2, 
  ExternalLink, 
  Clock, 
  Sparkles,
  Trash2,
  Send,
  CornerDownRight,
  ShieldCheck
} from 'lucide-react';

interface Props {
  match: MatchRecord;
  onPost: (matchId: number, text: string) => Promise<void>;
  onDelete: (matchId: number) => Promise<void>;
}

export const MatchCard: React.FC<Props> = ({ match, onPost, onDelete }) => {
  const [replyText, setReplyText] = useState(match.suggested_reply);
  const [isPosting, setIsPosting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isPosted = match.status === 'approved' || match.status === 'auto_posted';
  const charLimit = 240;
  const charsRemaining = charLimit - replyText.length;
  const isOverLimit = charsRemaining < 0;

  const getConfidenceBadge = (score: number) => {
    if (score >= 70) {
      return {
        bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
        dot: 'bg-emerald-400',
        label: 'High Match'
      };
    }
    if (score >= 50) {
      return {
        bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
        dot: 'bg-amber-400',
        label: 'Medium Match'
      };
    }
    return {
      bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
      dot: 'bg-rose-400',
      label: 'Low Match'
    };
  };

  const conf = getConfidenceBadge(match.confidence_score);

  const handlePostClick = async () => {
    if (isPosting || isPosted || isOverLimit) return;
    setIsPosting(true);
    try {
      await onPost(match.id, replyText);
    } finally {
      setIsPosting(false);
    }
  };

  const handleDeleteClick = async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    try {
      await onDelete(match.id);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className={`bg-[#10141e] border rounded-2xl p-5 sm:p-6 transition-all duration-200 shadow-lg ${
      isPosted ? 'border-emerald-500/30 bg-[#0c131d]/60' : 'border-slate-800 hover:border-slate-700/80'
    }`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
        <div className="flex items-center space-x-3">
          <span className="px-3 py-1 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20 text-xs font-semibold uppercase tracking-wider">
            {match.event_keyword}
          </span>
          <span className="text-xs text-slate-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {match.created_at.split('T')[1]?.substring(0, 5) || 'Recent'}
          </span>
        </div>

        <div className="flex items-center space-x-2.5">
          <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-full border text-xs font-bold ${conf.bg}`}>
            <span className={`w-2 h-2 rounded-full ${conf.dot}`}></span>
            <span>{match.confidence_score}% Match</span>
          </div>

          {match.status === 'auto_posted' && (
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-purple-400" />
              Auto-Commented on X
            </span>
          )}
          {match.status === 'approved' && (
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              Commented
            </span>
          )}

          <button
            onClick={handleDeleteClick}
            disabled={isDeleting}
            title="Dismiss match"
            className="p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Side-by-Side Buyer and Seller Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-5">
        {/* Buyer Card */}
        <div className="bg-[#0b0e15] border border-blue-500/20 rounded-xl p-4 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 px-2.5 py-0.5 bg-blue-500/20 border-b border-l border-blue-500/30 text-blue-300 text-[10px] font-bold rounded-bl-lg uppercase tracking-wider">
            Target Buyer Post
          </div>
          <div>
            <div className="flex items-center space-x-2 mb-2.5">
              <div className="w-7 h-7 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-300 font-bold text-xs">
                @
              </div>
              <div>
                <a
                  href={`https://x.com/${match.buyer_username}/status/${match.buyer_tweet_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm font-bold text-white hover:text-blue-400 flex items-center gap-1 group"
                >
                  <span>@{match.buyer_username}</span>
                  <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                </a>
                <span className="text-[11px] text-slate-500">{match.buyer_timestamp}</span>
              </div>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed font-normal bg-[#111622] p-3 rounded-lg border border-slate-800/80">
              "{match.buyer_text}"
            </p>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Tweet ID: {match.buyer_tweet_id}</span>
            <span className="text-blue-400/80">Looking for tickets</span>
          </div>
        </div>

        {/* Seller Card */}
        <div className="bg-[#0b0e15] border border-emerald-500/20 rounded-xl p-4 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 px-2.5 py-0.5 bg-emerald-500/20 border-b border-l border-emerald-500/30 text-emerald-300 text-[10px] font-bold rounded-bl-lg uppercase tracking-wider">
            Verified Seller Offer
          </div>
          <div>
            <div className="flex items-center space-x-2 mb-2.5">
              <div className="w-7 h-7 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-300 font-bold text-xs">
                @
              </div>
              <div>
                <a
                  href={`https://x.com/${match.seller_username}/status/${match.seller_tweet_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm font-bold text-white hover:text-emerald-400 flex items-center gap-1 group"
                >
                  <span>@{match.seller_username}</span>
                  <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                </a>
                <span className="text-[11px] text-slate-500">{match.seller_timestamp}</span>
              </div>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed font-normal bg-[#111622] p-3 rounded-lg border border-slate-800/80">
              "{match.seller_text}"
            </p>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Tweet ID: {match.seller_tweet_id}</span>
            <span className="text-emerald-400/80">Selling at discount/face value</span>
          </div>
        </div>
      </div>

      {/* AI Reasoning */}
      <div className="bg-[#0d121c] border border-purple-500/20 rounded-xl p-3.5 mb-5">
        <div className="flex items-center space-x-1.5 text-xs font-semibold text-purple-300 mb-1">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span>AI Buyer & Seller Intent Analysis</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed font-mono">
          {match.ai_reasoning}
        </p>
      </div>

      {/* Direct Comment Textarea */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <CornerDownRight className="w-3.5 h-3.5 text-sky-400" />
            <span>Direct Comment Replying to @{match.buyer_username}</span>
            <span className="text-[10px] text-slate-500 font-normal">(Informs buyer that seller is selling at a discount)</span>
          </label>
          <span className={`text-xs font-mono font-medium ${
            isOverLimit ? 'text-rose-400 font-bold' : charsRemaining < 20 ? 'text-amber-400' : 'text-slate-500'
          }`}>
            {replyText.length} / {charLimit} chars
          </span>
        </div>

        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          disabled={isPosted || isPosting}
          rows={2}
          className={`w-full p-3 bg-[#0b0e15] border rounded-xl text-sm text-white placeholder-slate-500 font-medium focus:outline-none focus:ring-2 focus:ring-sky-500 transition resize-none ${
            isOverLimit ? 'border-rose-500/70' : 'border-slate-700/80'
          } ${isPosted ? 'opacity-70 bg-[#090b10] cursor-not-allowed' : ''}`}
          placeholder="Comment text tagging buyer & seller..."
        />
      </div>

      {/* Action Row */}
      <div className="mt-4 pt-3.5 border-t border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="text-xs text-slate-400">
          {isPosted ? (
            <div className="flex items-center space-x-2 text-emerald-400 font-medium">
              <CheckCircle2 className="w-4 h-4" />
              <span>Commented directly underneath buyer tweet</span>
              {match.posted_tweet_id && (
                <span className="font-mono text-slate-400 text-[11px] bg-slate-800/80 px-2 py-0.5 rounded">
                  Comment ID: {match.posted_tweet_id}
                </span>
              )}
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 text-slate-400">
              <MessageSquare className="w-4 h-4 text-sky-400" />
              <span>Will publish directly underneath @{match.buyer_username}'s post.</span>
            </div>
          )}
        </div>

        {!isPosted && (
          <button
            onClick={handlePostClick}
            disabled={isPosting || isOverLimit || !replyText.trim()}
            className="w-full sm:w-auto inline-flex items-center justify-center px-5 py-2.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-xs transition shadow-md shadow-sky-500/20 active:scale-[0.98]"
          >
            {isPosting ? (
              <>
                <span className="animate-spin mr-2">⚙️</span>
                Commenting on X...
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5 mr-2" />
                Comment Directly on Buyer's Tweet
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
