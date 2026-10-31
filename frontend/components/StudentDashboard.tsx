'use client';

import React, { useEffect, useState } from 'react';
import { api, StudentMasterySummary, DecisionLogRecord, User } from '@/lib/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
} from 'recharts';
import {
  BarChart3,
  Calendar,
  AlertTriangle,
  Award,
  Sparkles,
  HelpCircle,
  RefreshCw,
  Clock,
  CheckCircle,
  Layers,
} from 'lucide-react';

interface StudentDashboardProps {
  user: User | null;
  onOpenAuth: () => void;
  onViewDecisions: () => void;
}

export const StudentDashboard: React.FC<StudentDashboardProps> = ({
  user,
  onOpenAuth,
  onViewDecisions,
}) => {
  const [summary, setSummary] = useState<StudentMasterySummary | null>(null);
  const [decisions, setDecisions] = useState<DecisionLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [mSummary, dLogs] = await Promise.all([
        api.getStudentMastery(user.id),
        api.getStudentDecisions(user.id, 10),
      ]);
      setSummary(mSummary);
      setDecisions(dLogs);
    } catch (err: any) {
      setError(err.message || 'Failed to load learner model from database.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchDashboardData();
    } else {
      setLoading(false);
    }
  }, [user]);

  if (!user) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center text-slate-100">
        <div className="inline-flex p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-6">
          <BarChart3 className="h-10 w-10" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight mb-2">Learner Model & Mastery View</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
          Sign in to inspect your personalized knowledge states, spaced review calendar, and explainable recommendation traces.
        </p>
        <button
          onClick={onOpenAuth}
          className="px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-sm transition-all"
        >
          Sign In
        </button>
      </div>
    );
  }

  // Prepare chart data from concept_mastery
  const chartData = summary
    ? Object.entries(summary.concept_mastery).map(([cid, data]) => ({
        id: cid,
        name: data.name,
        percentage: data.percentage,
        mastery: data.mastery,
        attempts: data.attempts_count,
      }))
    : [];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 text-slate-100">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Per-Student Learner Model
            </span>
            <span className="text-xs text-slate-400">Student: {user.name}</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Knowledge Mastery & Explainable Decisions
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time Bayesian-style exponential mastery updates strictly stored in SQLite / PostgreSQL tables.
          </p>
        </div>

        <button
          onClick={fetchDashboardData}
          disabled={loading}
          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors self-start sm:self-center"
          title="Refresh Learner Model"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
            ))}
          </div>
          <div className="h-72 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-slate-200 mb-8 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
            <span className="text-xs text-rose-300">{error}</span>
          </div>
          <button
            onClick={fetchDashboardData}
            className="px-3.5 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-xs font-semibold text-rose-300 border border-rose-500/30"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && summary && (
        <div className="space-y-8">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Total Attempts
              </span>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-white font-mono">{summary.total_attempts}</span>
                <span className="text-xs text-slate-500">recorded</span>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Accuracy Rate
              </span>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-emerald-400 font-mono">
                  {summary.accuracy_percentage.toFixed(1)}%
                </span>
                <span className="text-xs text-slate-500">deterministic</span>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Weakest Concept
              </span>
              <span className="text-sm font-bold text-rose-400 block truncate">
                {summary.weakest_concept || 'None (Assessing)'}
              </span>
              <span className="text-[10px] text-slate-500">Target for revision</span>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Strongest Concept
              </span>
              <span className="text-sm font-bold text-cyan-400 block truncate">
                {summary.strongest_concept || 'None (Assessing)'}
              </span>
              <span className="text-[10px] text-slate-500">Solid foundation</span>
            </div>
          </div>

          {/* Recharts Mastery Chart per Concept */}
          <div className="p-6 sm:p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-white tracking-tight">
                  Concept Mastery Breakdown
                </h3>
                <p className="text-xs text-slate-400">
                  Target threshold for prerequisite unlock is <strong className="text-slate-200">60.0%</strong>.
                </p>
              </div>

              <div className="flex items-center space-x-3 text-[11px]">
                <span className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                  <span className="text-slate-400">&ge; 70% Strong</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                  <span className="text-slate-400">40-69% Moderate</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
                  <span className="text-slate-400">&lt; 40% Weak</span>
                </span>
              </div>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="name"
                    stroke="#64748b"
                    fontSize={11}
                    angle={-20}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} unit="%" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      fontSize: '12px',
                      color: '#f8fafc',
                    }}
                    formatter={(val: any) => [`${val}%`, 'Mastery']}
                  />
                  <Bar dataKey="percentage" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry, index) => {
                      const color =
                        entry.percentage >= 70
                          ? '#10b981'
                          : entry.percentage >= 40
                          ? '#f59e0b'
                          : '#ef4444';
                      return <Cell key={`cell-${index}`} fill={color} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Spaced Revision Schedule & Misconceptions Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Upcoming Spaced Revisions */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
              <h3 className="text-base font-bold text-white tracking-tight flex items-center space-x-2 mb-4">
                <Calendar className="h-4 w-4 text-emerald-400" />
                <span>Spaced Revision Calendar</span>
              </h3>

              {summary.upcoming_revisions && summary.upcoming_revisions.length > 0 ? (
                <div className="space-y-3">
                  {summary.upcoming_revisions.map((rev, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-850 border border-slate-800 flex items-center justify-between"
                    >
                      <div>
                        <span className="font-semibold text-sm text-slate-200 block">
                          {rev.concept_name}
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Rule: {rev.rule}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-semibold text-emerald-400 block">
                          {new Date(rev.due_date).toLocaleDateString()}
                        </span>
                        <span className="text-[10px] text-slate-500">Scheduled Date</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic py-4">
                  No pending spaced revisions scheduled yet.
                </p>
              )}
            </div>

            {/* Misconceptions Encountered */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
              <h3 className="text-base font-bold text-white tracking-tight flex items-center space-x-2 mb-4">
                <AlertTriangle className="h-4 w-4 text-rose-400" />
                <span>Misconceptions Tracked</span>
              </h3>

              {summary.misconceptions_encountered && summary.misconceptions_encountered.length > 0 ? (
                <div className="space-y-3">
                  {summary.misconceptions_encountered.map((m, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-slate-850 border border-slate-800 flex items-center justify-between"
                    >
                      <span className="font-mono text-xs font-semibold text-rose-300">
                        {m.misconception_id}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">
                        {m.count} {m.count === 1 ? 'event' : 'events'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic py-4">
                  Zero misconceptions logged. Clear conceptual reasoning maintained.
                </p>
              )}
            </div>
          </div>

          {/* Explainable Decision Log Audit Trail ("Why am I seeing this?") */}
          <div className="p-6 sm:p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight flex items-center space-x-2">
                  <Sparkles className="h-4 w-4 text-emerald-400" />
                  <span>&quot;Why am I seeing this?&quot; Decision Log Trace</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Every question recommendation and spaced review has an immutable reason row in <code className="text-slate-300 font-mono">decision_log</code>.
                </p>
              </div>
            </div>

            {decisions.length > 0 ? (
              <div className="space-y-3">
                {decisions.map((d) => (
                  <div
                    key={d.id}
                    className="p-4 rounded-xl bg-slate-850 border border-slate-800/80 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                          {d.decision_type}
                        </span>
                        <span className="text-xs font-bold text-emerald-400">
                          {d.payload?.rule || 'system_rule'}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-500 font-mono">
                        {new Date(d.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed font-sans">
                      {d.payload?.detail || JSON.stringify(d.payload)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic py-4">
                No decision traces logged yet. Complete questions in the Adaptive Quiz to generate audit traces.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
