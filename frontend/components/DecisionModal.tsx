'use client';

import React, { useEffect, useState } from 'react';
import { api, DecisionLogRecord, User } from '@/lib/api';
import { X, Sparkles, RefreshCw, AlertCircle, HelpCircle, Clock } from 'lucide-react';

interface DecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
}

export const DecisionModal: React.FC<DecisionModalProps> = ({ isOpen, onClose, user }) => {
  const [decisions, setDecisions] = useState<DecisionLogRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDecisions = async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStudentDecisions(user.id, 25);
      setDecisions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load explainable decision logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && user) {
      fetchDecisions();
    }
  }, [isOpen, user]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl relative text-slate-100 flex flex-col max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                &quot;Why am I seeing this?&quot; Decision Trace Audit
              </h2>
              <p className="text-xs text-slate-400">
                Immutable decision traces stored in the database (<code className="text-slate-300 font-mono">decision_log</code>).
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="overflow-y-auto py-4 space-y-3 flex-1 pr-1">
          {loading && (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-slate-800/60 rounded-xl animate-pulse" />
              ))}
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center space-x-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && decisions.length === 0 && (
            <div className="py-12 text-center text-xs text-slate-500">
              No decisions recorded yet for this user.
            </div>
          )}

          {!loading &&
            !error &&
            decisions.map((d) => (
              <div
                key={d.id}
                className="p-4 rounded-xl bg-slate-850 border border-slate-800 hover:border-slate-700 transition-all text-xs"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                      {d.decision_type}
                    </span>
                    <span className="font-mono font-bold text-emerald-400">
                      {d.payload?.rule || 'rule_triggered'}
                    </span>
                    {d.payload?.concept && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                        {d.payload.concept}
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono flex items-center space-x-1">
                    <Clock className="h-3 w-3" />
                    <span>{new Date(d.created_at).toLocaleTimeString()}</span>
                  </span>
                </div>

                <p className="text-slate-300 leading-relaxed font-sans mb-2">
                  {d.payload?.detail || JSON.stringify(d.payload)}
                </p>

                {d.payload?.mastery !== undefined && (
                  <div className="text-[11px] font-mono text-slate-400 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800 inline-block">
                    Student Latent Mastery at Decision: <strong className="text-white">{(d.payload.mastery * 100).toFixed(1)}%</strong>
                  </div>
                )}
              </div>
            ))}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-800 flex items-center justify-between shrink-0">
          <span className="text-[11px] text-slate-500 font-mono">
            Audit standard: Section 2(a) Explainability Guarantee
          </span>
          <button
            onClick={fetchDecisions}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium border border-slate-700 transition-colors flex items-center space-x-1"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>
    </div>
  );
};
