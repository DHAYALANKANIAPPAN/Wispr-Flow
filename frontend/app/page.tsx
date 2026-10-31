'use client';

import React, { useState, useEffect } from 'react';
import { api, User } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { AuthModal } from '@/components/AuthModal';
import { DecisionModal } from '@/components/DecisionModal';
import { ConceptsView } from '@/components/ConceptsView';
import { QuizView } from '@/components/QuizView';
import { StudentDashboard } from '@/components/StudentDashboard';
import { TeacherDashboard } from '@/components/TeacherDashboard';
import { ClaimsView } from '@/components/ClaimsView';
import { Shield, Sparkles, BookOpen, Brain, BarChart3, Users, HelpCircle, Terminal } from 'lucide-react';

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<string>('concepts');
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isDecisionOpen, setIsDecisionOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Check backend health and recover user session on initial mount
  useEffect(() => {
    const initApp = async () => {
      try {
        await api.checkHealth();
        setBackendOnline(true);
      } catch (e) {
        setBackendOnline(false);
      }

      if (api.getToken()) {
        try {
          const userData = await api.getMe();
          setUser(userData);
        } catch (e) {
          api.logout();
          setUser(null);
        }
      }
    };

    initApp();

    // Health check ping every 30 seconds
    const interval = setInterval(async () => {
      try {
        await api.checkHealth();
        setBackendOnline(true);
      } catch (e) {
        setBackendOnline(false);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setActiveTab('concepts');
  };

  const handleSwitchToTeacher = async () => {
    try {
      try {
        const res = await api.login({ email: 'turing@school.org', password: 'password123' });
        setUser(res.user);
        setActiveTab('teacher-dashboard');
      } catch (_) {
        const regRes = await api.register({
          name: 'Prof. Turing',
          email: 'turing@school.org',
          password: 'password123',
          role: 'teacher',
        });
        setUser(regRes.user);
        setActiveTab('teacher-dashboard');
      }
    } catch (err) {
      console.error('Failed to switch to teacher demo:', err);
    }
  };

  return (
    <main className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-emerald-500 selection:text-slate-950">
      {/* Top Navigation */}
      <Navbar
        user={user}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenAuth={() => setIsAuthOpen(true)}
        onLogout={handleLogout}
        backendOnline={backendOnline}
      />

      {/* Main Tab Views */}
      <div className="flex-1">
        {activeTab === 'concepts' && (
          <ConceptsView
            user={user}
            onOpenAuth={() => setIsAuthOpen(true)}
            onStartQuiz={() => setActiveTab('quiz')}
          />
        )}

        {activeTab === 'quiz' && (
          <QuizView
            user={user}
            onOpenAuth={() => setIsAuthOpen(true)}
            onViewDecisions={() => setIsDecisionOpen(true)}
          />
        )}

        {activeTab === 'student-dashboard' && (
          <StudentDashboard
            user={user}
            onOpenAuth={() => setIsAuthOpen(true)}
            onViewDecisions={() => setIsDecisionOpen(true)}
          />
        )}

        {activeTab === 'teacher-dashboard' && (
          <TeacherDashboard
            user={user}
            onOpenAuth={() => setIsAuthOpen(true)}
            onSwitchToTeacher={handleSwitchToTeacher}
          />
        )}

        {activeTab === 'claims' && <ClaimsView />}
      </div>

      {/* Decision Log Modal ("Why am I seeing this?") */}
      <DecisionModal
        isOpen={isDecisionOpen}
        onClose={() => setIsDecisionOpen(false)}
        user={user}
      />

      {/* Auth & Demo Profiles Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onSuccess={(u) => {
          setUser(u);
          if (u.role === 'teacher') {
            setActiveTab('teacher-dashboard');
          } else {
            setActiveTab('concepts');
          }
        }}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-8 px-4 sm:px-6 mt-auto text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-300">ADAPTIVE IQ</span>
            <span>&bull;</span>
            <span>CBSE Class 10 Physics: Electricity</span>
            <span>&bull;</span>
            <span className="font-mono text-[11px] text-emerald-400">Apache-2.0</span>
          </div>

          <div className="flex items-center space-x-4 text-[11px] text-slate-400">
            <span>FastAPI + NetworkX Backend</span>
            <span>&bull;</span>
            <span>Next.js + Recharts UI</span>
            <span>&bull;</span>
            <span>Wispr Flow Dictation</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
