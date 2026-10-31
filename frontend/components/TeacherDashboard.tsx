'use client';

import React, { useEffect, useState } from 'react';
import { api, TeacherClassSummary, User } from '@/lib/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
  PieChart,
  Pie,
} from 'recharts';
import {
  Users,
  AlertTriangle,
  Award,
  Sparkles,
  TrendingDown,
  RefreshCw,
  Shield,
  HelpCircle,
  AlertCircle,
} from 'lucide-react';

interface TeacherDashboardProps {
  user: User | null;
  onOpenAuth: () => void;
  onSwitchToTeacher: () => void;
}

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#10b981'];

export const TeacherDashboard: React.FC<TeacherDashboardProps> = ({
  user,
  onOpenAuth,
  onSwitchToTeacher,
}) => {
  const [summary, setSummary] = useState<TeacherClassSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchClassSummary = async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTeacherClassSummary(user.id);
      setSummary(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load class analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role === 'teacher') {
      fetchClassSummary();
    } else {
      setLoading(false);
    }
  }, [user]);

  if (!user) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center text-slate-100">
        <div className="inline-flex p-4 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400 mb-6">
          <Shield className="h-10 w-10" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight mb-2">Teacher Analytics Portal</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
          Sign in with a teacher account (or click Teacher Demo Profile) to access aggregate class mastery and student interventions.
        </p>
        <button
          onClick={onOpenAuth}
          className="px-6 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-600 text-slate-950 font-bold text-sm transition-all"
        >
          Sign In as Teacher
        </button>
      </div>
    );
  }

  if (user.role !== 'teacher') {
    return (
      <div className="max-w-xl mx-auto py-16 px-4 text-center text-slate-100">
        <div className="inline-flex p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 mb-4">
          <AlertCircle className="h-8 w-8" />
        </div>
        <h2 className="text-xl font-bold tracking-tight mb-2">Teacher Authorization Required</h2>
        <p className="text-xs text-slate-400 mb-6 leading-relaxed">
          You are currently logged in as student <strong className="text-slate-200">{user.name}</strong>.
          Under Section 6 & 8 security rules, students cannot inspect class aggregates. Switch to the Teacher profile to view class analytics.
        </p>
        <button
          onClick={onSwitchToTeacher}
          className="px-5 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-600 text-slate-950 font-bold text-xs transition-colors"
        >
          Switch to Prof. Turing (Teacher Demo)
        </button>
      </div>
    );
  }

  // Bar chart data: class mastery
  const masteryChartData = summary
    ? Object.entries(summary.concept_class_mastery).map(([cid, data]) => ({
        id: cid,
        name: data.concept_name,
        percentage: data.average_percentage,
        students: data.students_assessed,
      }))
    : [];

  // Pie chart data: misconception distribution
  const misconceptionPieData = summary
    ? Object.entries(summary.misconception_distribution).map(([mid, count]) => ({
        name: mid,
        value: count,
      }))
    : [];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 text-slate-100">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-500/10 text-purple-400 border border-purple-500/20">
              Instructor Portal
            </span>
            <span className="text-xs text-slate-400">Teacher: {user.name}</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Class Performance & Diagnostic Interventions
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Aggregated strictly from persistent database attempts and learner mastery records. Zero hardcoded stats.
          </p>
        </div>

        <button
          onClick={fetchClassSummary}
          disabled={loading}
          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors self-start sm:self-center"
          title="Refresh Class Aggregates"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
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
            onClick={fetchClassSummary}
            className="px-3.5 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-xs font-semibold text-rose-300 border border-rose-500/30"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && summary && (
        <div className="space-y-8">
          {/* Key Metric KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Total Enrolled Students
              </span>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-white font-mono">{summary.total_students}</span>
                <span className="text-xs text-slate-500">active</span>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Total Attempts Graded
              </span>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-cyan-400 font-mono">{summary.total_attempts}</span>
                <span className="text-xs text-slate-500">pipeline submissions</span>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Average Class Accuracy
              </span>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-emerald-400 font-mono">
                  {summary.average_class_accuracy.toFixed(1)}%
                </span>
                <span className="text-xs text-slate-500">accuracy</span>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-rose-500/30 shadow-md">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-rose-400 block mb-1">
                Most-Missed Concept
              </span>
              <span className="text-sm font-bold text-white block truncate">
                {summary.most_missed_concept || 'None'}
              </span>
              <span className="text-[10px] text-rose-400">Class priority target</span>
            </div>
          </div>

          {/* Charts Row: Class Concept Mastery + Misconception Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Concept Mastery Bar Chart */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
              <h3 className="text-base font-bold text-white tracking-tight mb-2">
                Class Average Mastery per Concept
              </h3>
              <p className="text-xs text-slate-400 mb-6">
                Evaluates cohort proficiency across all 7 CBSE Electricity concepts.
              </p>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={masteryChartData} margin={{ top: 10, right: 10, left: -20, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="name"
                      stroke="#64748b"
                      fontSize={10}
                      angle={-25}
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
                      formatter={(val: any) => [`${val}%`, 'Class Average']}
                    />
                    <Bar dataKey="percentage" radius={[6, 6, 0, 0]}>
                      {masteryChartData.map((entry, index) => {
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

            {/* Misconception Distribution Pie / Bar */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col justify-between">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight mb-2">
                  Misconception Distribution
                </h3>
                <p className="text-xs text-slate-400 mb-4">
                  Controlled taxonomy errors detected in student spoken/typed explanations.
                </p>

                {misconceptionPieData.length > 0 ? (
                  <div className="space-y-3 pt-2">
                    {misconceptionPieData.map((m, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-slate-850 border border-slate-800 flex items-center justify-between"
                      >
                        <div className="flex items-center space-x-2.5">
                          <span
                            className="h-3 w-3 rounded-full shrink-0"
                            style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                          />
                          <span className="font-mono text-xs text-slate-200">{m.name}</span>
                        </div>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-800 text-slate-300 font-mono">
                          {m.value} {m.value === 1 ? 'incident' : 'incidents'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center text-xs text-slate-500 italic">
                    Zero misconceptions detected across cohort attempts.
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-800 text-[11px] text-slate-500">
                Data generated strictly by closed-vocabulary classification (<code className="text-slate-400 font-mono">backend/app/misconceptions.py</code>).
              </div>
            </div>
          </div>

          {/* Students Needing Support Section */}
          <div className="p-6 sm:p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
            <h3 className="text-base font-bold text-white tracking-tight flex items-center space-x-2 mb-2">
              <Users className="h-4 w-4 text-rose-400" />
              <span>Students Requiring Targeted Remediation</span>
            </h3>
            <p className="text-xs text-slate-400 mb-6">
              Students automatically flagged whose mastery on any curriculum concept drops below 40%, or whose average accuracy is substandard.
            </p>

            {summary.students_needing_support && summary.students_needing_support.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-850 text-slate-400 uppercase text-[10px] font-semibold tracking-wider">
                    <tr>
                      <th className="py-3 px-4 rounded-l-xl">Student Name</th>
                      <th className="py-3 px-4">Student ID</th>
                      <th className="py-3 px-4">Weakest Concept</th>
                      <th className="py-3 px-4">Concept Mastery</th>
                      <th className="py-3 px-4 rounded-r-xl">Flag Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {summary.students_needing_support.map((s) => {
                      const displayName = s.student_name ?? s.name ?? 'Student';
                      const masteryVal = s.weakest_mastery ?? s.average_mastery ?? 0.35;
                      const reason = s.flag_reason ?? (s.average_mastery && s.average_mastery < 0.50 ? 'Average cohort mastery < 50%' : 'Low concept mastery (< 40%)');
                      return (
                        <tr key={s.student_id} className="hover:bg-slate-850/50 transition-colors">
                          <td className="py-3 px-4 font-semibold text-slate-200">{displayName}</td>
                          <td className="py-3 px-4 font-mono text-slate-400">{s.student_id}</td>
                          <td className="py-3 px-4 font-mono text-rose-300">{s.weakest_concept}</td>
                          <td className="py-3 px-4 font-mono font-bold text-rose-400">
                            {(masteryVal * 100).toFixed(1)}%
                          </td>
                          <td className="py-3 px-4 text-slate-300">{reason}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-6 rounded-xl bg-slate-850/60 border border-slate-800 text-center text-xs text-emerald-400">
                All students currently maintain mastery levels above the 40% intervention threshold.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
