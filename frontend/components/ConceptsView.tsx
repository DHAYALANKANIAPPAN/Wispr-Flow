'use client';

import React, { useEffect, useState } from 'react';
import { api, Concept, User } from '@/lib/api';
import { Lock, Unlock, ArrowRight, RefreshCw, AlertTriangle, BookOpen, CheckCircle, Zap } from 'lucide-react';

interface ConceptsViewProps {
  user: User | null;
  onOpenAuth: () => void;
  onStartQuiz: () => void;
}

export const ConceptsView: React.FC<ConceptsViewProps> = ({ user, onOpenAuth, onStartQuiz }) => {
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConcepts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getConcepts();
      setConcepts(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load CBSE Class 10 concepts from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchConcepts();
    } else {
      setLoading(false);
    }
  }, [user]);

  if (!user) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <div className="inline-flex p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-6">
          <BookOpen className="h-10 w-10" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-3">
          CBSE Class 10 Physics: Electricity
        </h1>
        <p className="text-slate-400 max-w-xl mx-auto mb-8 text-sm">
          Gate 1 Contract: Sign in as a student to inspect the chapter&apos;s Knowledge Graph,
          view prerequisite unlock statuses, and begin adaptive concept mastery.
        </p>
        <button
          onClick={onOpenAuth}
          className="px-6 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-emerald-500/25 inline-flex items-center space-x-2"
        >
          <span>Sign In as Student or Teacher</span>
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
      {/* Header Banner */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center space-x-2.5 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              CBSE Class 10 Physics
            </span>
            <span className="text-xs text-slate-400 font-mono">Chapter: Electricity</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Curriculum Knowledge Graph & Prerequisites
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Root concepts are unlocked by default. Dependent concepts remain strictly locked
            until prerequisite mastery reaches <strong className="text-slate-200">60%</strong>, enforced deterministically via NetworkX DAG validation.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={fetchConcepts}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="Refresh Curriculum Status"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onStartQuiz}
            className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-sm transition-all shadow-md shadow-emerald-500/20 flex items-center space-x-2"
          >
            <Zap className="h-4 w-4" />
            <span>Launch Adaptive Session</span>
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div key={i} className="animate-pulse bg-slate-900/60 border border-slate-800 p-5 rounded-2xl h-44 flex flex-col justify-between">
              <div>
                <div className="h-4 bg-slate-800 rounded w-1/3 mb-3" />
                <div className="h-5 bg-slate-700 rounded w-3/4 mb-2" />
                <div className="h-3 bg-slate-800 rounded w-full mb-1" />
                <div className="h-3 bg-slate-800 rounded w-2/3" />
              </div>
              <div className="h-6 bg-slate-800 rounded w-1/4 mt-4" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-slate-200 mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-rose-300 text-sm">Failed to Load Knowledge Graph</h3>
              <p className="text-xs text-slate-400 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchConcepts}
            className="px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-semibold border border-rose-500/30 transition-colors shrink-0"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Concept Grid */}
      {!loading && !error && concepts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {concepts.map((concept) => {
            const unlocked = concept.is_unlocked ?? concept.unlocked ?? false;
            return (
            <div
              key={concept.id}
              className={`rounded-2xl p-5 border transition-all flex flex-col justify-between relative overflow-hidden ${
                unlocked
                  ? 'bg-slate-900/80 border-slate-700/80 hover:border-emerald-500/50 shadow-lg shadow-black/20'
                  : 'bg-slate-950/60 border-slate-850 opacity-70'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase tracking-wider ${
                      unlocked
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {unlocked ? (
                      <>
                        <Unlock className="h-3 w-3" />
                        <span>Unlocked</span>
                      </>
                    ) : (
                      <>
                        <Lock className="h-3 w-3" />
                        <span>Locked</span>
                      </>
                    )}
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">ID: {concept.id}</span>
                </div>

                <h3 className="text-lg font-bold text-white tracking-tight mb-1.5">
                  {concept.name}
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  {concept.description}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80">
                <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Prerequisites:
                </span>
                {concept.prerequisites && concept.prerequisites.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {concept.prerequisites.map((p) => (
                      <span
                        key={p}
                        className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700/60"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-[11px] text-emerald-400/80 italic font-medium">
                    None (Root Syllabus Concept)
                  </span>
                )}
              </div>
            </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
