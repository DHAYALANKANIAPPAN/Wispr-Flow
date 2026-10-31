'use client';

import React from 'react';
import { User } from '@/lib/api';
import { Sparkles, Shield, User as UserIcon, LogOut, Activity, BookOpen, Brain, BarChart3, Users, HelpCircle } from 'lucide-react';

interface NavbarProps {
  user: User | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenAuth: () => void;
  onLogout: () => void;
  backendOnline: boolean | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  activeTab,
  setActiveTab,
  onOpenAuth,
  onLogout,
  backendOnline,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-40 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Product Title */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('concepts')}>
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-emerald-400 bg-clip-text text-transparent">
                  ADAPTIVE IQ
                </span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  PS 02 CBSE
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Adaptive Exam-Prep Tutor with a Learner Model
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1">
            <button
              onClick={() => setActiveTab('concepts')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'concepts'
                  ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <BookOpen className="h-4 w-4" />
              <span>Syllabus & Graph</span>
            </button>

            <button
              onClick={() => setActiveTab('quiz')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'quiz'
                  ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <Brain className="h-4 w-4" />
              <span>Adaptive Quiz</span>
            </button>

            <button
              onClick={() => setActiveTab('student-dashboard')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'student-dashboard'
                  ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              <span>Learner Mastery</span>
            </button>

            <button
              onClick={() => setActiveTab('teacher-dashboard')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'teacher-dashboard'
                  ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <Users className="h-4 w-4" />
              <span>Teacher Analytics</span>
            </button>

            <button
              onClick={() => setActiveTab('claims')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'claims'
                  ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
              }`}
            >
              <HelpCircle className="h-4 w-4" />
              <span>Judges Claims</span>
            </button>
          </nav>

          {/* Right Status & User Panel */}
          <div className="flex items-center space-x-3">
            {/* Backend Health Status Pill */}
            <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs bg-slate-800/80 border border-slate-700/60">
              <span
                className={`h-2 w-2 rounded-full ${
                  backendOnline === true
                    ? 'bg-emerald-400 shadow-sm shadow-emerald-400'
                    : backendOnline === false
                    ? 'bg-rose-500 shadow-sm shadow-rose-500'
                    : 'bg-amber-400 animate-pulse'
                }`}
              />
              <span className="text-slate-400">
                {backendOnline === true ? 'Backend: Connected' : backendOnline === false ? 'Backend: Offline' : 'Connecting...'}
              </span>
            </div>

            {user ? (
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg text-sm">
                  {user.role === 'teacher' ? (
                    <Shield className="h-4 w-4 text-purple-400" />
                  ) : (
                    <UserIcon className="h-4 w-4 text-emerald-400" />
                  )}
                  <span className="font-medium text-slate-200">{user.name}</span>
                  <span className="text-[11px] font-semibold uppercase px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">
                    {user.role}
                  </span>
                </div>
                <button
                  onClick={onLogout}
                  title="Logout"
                  className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenAuth}
                className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-sm font-semibold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-colors shadow-md shadow-emerald-500/20"
              >
                <UserIcon className="h-4 w-4" />
                <span>Sign In / Demo</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
