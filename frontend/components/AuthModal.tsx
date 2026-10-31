'use client';

import React, { useState } from 'react';
import { api, User } from '@/lib/api';
import { X, Shield, User as UserIcon, Lock, Mail, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [role, setRole] = useState<'student' | 'teacher'>('student');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (mode === 'login') {
        const res = await api.login({ email, password });
        onSuccess(res.user);
        onClose();
      } else {
        const res = await api.register({ name, email, password, role });
        onSuccess(res.user);
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (
    presetName: string,
    presetEmail: string,
    presetRole: 'student' | 'teacher'
  ) => {
    setLoading(true);
    setError(null);
    try {
      try {
        const res = await api.login({ email: presetEmail, password: 'password123' });
        onSuccess(res.user);
        onClose();
      } catch (loginErr) {
        // Automatically register demo user if not yet in SQLite database
        const regRes = await api.register({
          name: presetName,
          email: presetEmail,
          password: 'password123',
          role: presetRole,
        });
        onSuccess(regRes.user);
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to authenticate preset demo profile.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative text-slate-100">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="mb-5">
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center space-x-2">
            <span>Adaptive IQ Sign In</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Access your CBSE Class 10 Physics learner model and explainable decision records.
          </p>
        </div>

        {/* Quick Demo Profiles (for Hackathon Judges & Pair Testing) */}
        <div className="mb-5 p-3 rounded-xl bg-slate-850 border border-slate-800">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Quick Demo Profiles (One-Click)
          </p>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => handleQuickLogin('Arun (Student A)', 'arun@school.org', 'student')}
              className="px-2 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-emerald-500/20 hover:text-emerald-400 border border-slate-700/60 transition-colors text-left"
            >
              <span className="block font-semibold">Student A</span>
              <span className="text-[10px] text-slate-400">Theory Strong</span>
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('Bhavna (Student B)', 'bhavna@school.org', 'student')}
              className="px-2 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-cyan-500/20 hover:text-cyan-400 border border-slate-700/60 transition-colors text-left"
            >
              <span className="block font-semibold">Student B</span>
              <span className="text-[10px] text-slate-400">Concept Trap</span>
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('Prof. Turing', 'turing@school.org', 'teacher')}
              className="px-2 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-purple-500/20 hover:text-purple-400 border border-slate-700/60 transition-colors text-left"
            >
              <span className="block font-semibold">Teacher</span>
              <span className="text-[10px] text-slate-400">Class View</span>
            </button>
          </div>
        </div>

        {/* Mode Toggle */}
        <div className="flex border-b border-slate-800 mb-4">
          <button
            onClick={() => { setMode('login'); setError(null); }}
            className={`flex-1 pb-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
              mode === 'login' ? 'border-b-2 border-emerald-500 text-emerald-400' : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setMode('register'); setError(null); }}
            className={`flex-1 pb-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
              mode === 'register' ? 'border-b-2 border-emerald-500 text-emerald-400' : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            New Account
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5">
          {mode === 'register' && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
              <div className="relative">
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Arun Kumar"
                  className="w-full bg-slate-800/90 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="h-4 w-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@school.org"
                className="w-full bg-slate-800/90 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="h-4 w-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-800/90 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          {mode === 'register' && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Role</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRole('student')}
                  className={`py-2 px-3 rounded-lg border text-xs font-medium flex items-center justify-center space-x-1.5 transition-colors ${
                    role === 'student'
                      ? 'bg-emerald-500/10 border-emerald-500 text-emerald-400'
                      : 'border-slate-700 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <UserIcon className="h-3.5 w-3.5" />
                  <span>Student</span>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('teacher')}
                  className={`py-2 px-3 rounded-lg border text-xs font-medium flex items-center justify-center space-x-1.5 transition-colors ${
                    role === 'teacher'
                      ? 'bg-purple-500/10 border-purple-500 text-purple-400'
                      : 'border-slate-700 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  <Shield className="h-3.5 w-3.5" />
                  <span>Teacher</span>
                </button>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-slate-950 font-semibold text-sm transition-colors flex items-center justify-center space-x-1.5 shadow-md shadow-emerald-500/20"
          >
            {loading ? (
              <span className="inline-block animate-spin h-4 w-4 border-2 border-slate-950 border-t-transparent rounded-full" />
            ) : (
              <>
                <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
