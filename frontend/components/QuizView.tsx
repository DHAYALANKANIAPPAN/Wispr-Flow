'use client';

import React, { useState, useEffect, useRef } from 'react';
import { api, NextQuestionResponse, SubmitAttemptResponse, User } from '@/lib/api';
import {
  Mic,
  MicOff,
  Send,
  AlertCircle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Sparkles,
  RefreshCw,
  Zap,
  TrendingUp,
  TrendingDown,
  Info,
  Clock,
  ArrowRight,
} from 'lucide-react';

interface QuizViewProps {
  user: User | null;
  onOpenAuth: () => void;
  onViewDecisions: () => void;
}

export const QuizView: React.FC<QuizViewProps> = ({ user, onOpenAuth, onViewDecisions }) => {
  const [currentQuestion, setCurrentQuestion] = useState<NextQuestionResponse | null>(null);
  const [loadingQuestion, setLoadingQuestion] = useState(true);
  const [questionError, setQuestionError] = useState<string | null>(null);

  // Form states
  const [studentAnswer, setStudentAnswer] = useState('');
  const [explanation, setExplanation] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Response state from POST /attempts
  const [lastAttemptResult, setLastAttemptResult] = useState<SubmitAttemptResponse | null>(null);

  // Voice dictation state (Wispr Flow / Web Speech API simulation)
  const [isDictating, setIsDictating] = useState(false);
  const recognitionRef = useRef<any>(null);

  // Textarea reference: NEVER clears on blur
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load next question from adaptive engine
  const fetchNextQuestion = async () => {
    setLoadingQuestion(true);
    setQuestionError(null);
    setSubmitError(null);
    try {
      const data = await api.getNextQuestion();
      setCurrentQuestion(data);
      // Reset inputs for new question
      setStudentAnswer('');
      setExplanation('');
    } catch (err: any) {
      setQuestionError(err.message || 'Failed to select next adaptive question.');
    } finally {
      setLoadingQuestion(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchNextQuestion();
    } else {
      setLoadingQuestion(false);
    }
  }, [user]);

  // Speech Recognition setup (Voice input fallback / Wispr Flow dictation)
  const toggleDictation = () => {
    if (isDictating) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsDictating(false);
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert(
        'Speech Recognition is not natively supported in this browser. You can type directly or use the Wispr Flow desktop app to dictate into this field.'
      );
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsDictating(true);
      };

      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setExplanation((prev) => {
          const base = prev.trim() ? prev + ' ' : '';
          return base + transcript;
        });
      };

      recognition.onerror = (e: any) => {
        console.warn('Speech recognition error:', e.error);
        setIsDictating(false);
      };

      recognition.onend = () => {
        setIsDictating(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      setIsDictating(false);
    }
  };

  // Submit answer through 9-step atomic backend pipeline
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentQuestion || !currentQuestion.question_id) return;

    if (!studentAnswer.trim()) {
      setSubmitError('Please enter an answer to submit.');
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const result = await api.submitAttempt({
        question_id: currentQuestion.question_id,
        student_answer: studentAnswer,
        explanation: explanation,
      });

      setLastAttemptResult(result);

      // Scroll to result
      window.scrollTo({ top: 400, behavior: 'smooth' });
    } catch (err: any) {
      setSubmitError(err.message || 'Answer submission failed in backend pipeline.');
    } finally {
      setSubmitting(false);
    }
  };

  // Quick Preset Insert for Live Demo
  const insertDemoSpeech = (type: 'trap' | 'sound') => {
    if (type === 'trap') {
      setStudentAnswer('correct');
      setExplanation(
        'Um, so basically current increases because you know resistance is higher and more resistance pushes more current through.'
      );
    } else {
      setStudentAnswer('20');
      setExplanation(
        'According to Ohm\'s law V equals I times R. Multiplying current 2 A by resistance 10 Ohm yields 20 Volts.'
      );
    }
  };

  if (!user) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4 text-center text-slate-100">
        <div className="inline-flex p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-6">
          <Zap className="h-10 w-10" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight mb-2">Adaptive Quiz Session</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
          Please sign in to begin receiving questions tailored by the adaptive engine with explainable reason traces.
        </p>
        <button
          onClick={onOpenAuth}
          className="px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-sm transition-all shadow-md shadow-emerald-500/20"
        >
          Sign In to Practice
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 text-slate-100">
      {/* Explainable Adaptive Reason Banner */}
      {currentQuestion && currentQuestion.reason && (
        <div className="mb-6 p-4 rounded-2xl bg-slate-900 border border-emerald-500/30 shadow-lg flex items-start justify-between gap-4">
          <div className="flex items-start space-x-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 shrink-0 mt-0.5">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                  Adaptive Reason Trace
                </span>
                <span className="text-xs font-mono text-slate-400">
                  Rule: <strong className="text-slate-200">{currentQuestion.reason.rule}</strong>
                </span>
                <span className="text-xs font-mono text-slate-400">
                  Target Concept: <strong className="text-emerald-400">{currentQuestion.reason.concept}</strong>
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1">{currentQuestion.reason.detail}</p>
            </div>
          </div>

          <button
            onClick={onViewDecisions}
            className="shrink-0 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-xs font-medium text-slate-300 border border-slate-700 transition-colors flex items-center space-x-1"
          >
            <HelpCircle className="h-3.5 w-3.5 text-emerald-400" />
            <span>Audit Trail</span>
          </button>
        </div>
      )}

      {/* Loading State */}
      {loadingQuestion && (
        <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 animate-pulse space-y-4">
          <div className="h-4 bg-slate-800 rounded w-1/4" />
          <div className="h-8 bg-slate-800 rounded w-3/4" />
          <div className="h-24 bg-slate-800 rounded w-full" />
        </div>
      )}

      {/* Error State */}
      {questionError && (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-slate-200 mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
            <span className="text-xs text-rose-300">{questionError}</span>
          </div>
          <button
            onClick={fetchNextQuestion}
            className="px-3.5 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-xs font-semibold text-rose-300 border border-rose-500/30"
          >
            Retry
          </button>
        </div>
      )}

      {/* Active Question Card */}
      {!loadingQuestion && currentQuestion && currentQuestion.question && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl relative mb-8">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-4 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-1 rounded-md text-[11px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                Difficulty: {currentQuestion.question.difficulty} / 3
              </span>
              <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wider bg-slate-800 text-cyan-400 border border-slate-700">
                {currentQuestion.question.question_type}
              </span>
              <span className="text-xs font-mono text-slate-500">ID: {currentQuestion.question.id}</span>
            </div>

            <button
              onClick={fetchNextQuestion}
              className="text-xs text-slate-400 hover:text-white flex items-center space-x-1"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Skip / Next</span>
            </button>
          </div>

          <h2 className="text-lg sm:text-xl font-semibold text-white leading-relaxed mb-6">
            {currentQuestion.question.text}
          </h2>

          {/* Answer Submission Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Your Answer ({currentQuestion.question.answer_type === 'numeric' ? 'Numeric Value' : 'Text Answer'})
              </label>
              <input
                type="text"
                required
                value={studentAnswer}
                onChange={(e) => setStudentAnswer(e.target.value)}
                placeholder={
                  currentQuestion.question.answer_type === 'numeric'
                    ? 'e.g. 20 (or 20 V)'
                    : 'e.g. yes / no / incorrect'
                }
                className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono text-sm"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Explain your reasoning (Dictate with Wispr Flow or Type)
                </label>
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] font-mono text-slate-500">
                    {explanation.trim() ? explanation.trim().split(/\s+/).length : 0} words
                  </span>
                  {/* Preset Buttons for Live Judges Demonstration */}
                  <div className="flex items-center space-x-1 text-[11px]">
                    <span className="text-slate-500 text-[10px]">Demo fill:</span>
                    <button
                      type="button"
                      onClick={() => insertDemoSpeech('trap')}
                      className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-amber-400 border border-slate-700"
                    >
                      Bhavna (Trap)
                    </button>
                    <button
                      type="button"
                      onClick={() => insertDemoSpeech('sound')}
                      className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700"
                    >
                      Arun (Sound)
                    </button>
                  </div>
                </div>
              </div>

              {/* Multi-line explanation textarea: keeps line breaks and NEVER clears on blur */}
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  rows={4}
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder="Dictate your thoughts naturally using Wispr Flow, or type here... (e.g. 'I used Ohm's law V = IR because...')"
                  className="w-full bg-slate-800/90 border border-slate-700 rounded-xl p-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 leading-relaxed resize-y font-sans"
                />

                {/* Voice Dictation Button (Wispr Flow Speech Recognition) */}
                <button
                  type="button"
                  onClick={toggleDictation}
                  className={`absolute right-3 bottom-3 p-2 rounded-xl text-xs font-medium flex items-center space-x-1.5 transition-all shadow-md ${
                    isDictating
                      ? 'bg-rose-500 text-white animate-pulse'
                      : 'bg-slate-700/80 hover:bg-slate-650 text-slate-200 border border-slate-600'
                  }`}
                  title={isDictating ? 'Stop Recording' : 'Dictate with Wispr Flow / Mic'}
                >
                  {isDictating ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4 text-emerald-400" />}
                  <span className="hidden sm:inline">
                    {isDictating ? 'Listening...' : 'Dictate'}
                  </span>
                </button>
              </div>

              <p className="text-[11px] text-slate-500 mt-1">
                Audio is never recorded. Text is cleaned by <code className="text-slate-400">normalize_explanation()</code> to remove verbal fillers without mutating physics terms.
              </p>
            </div>

            {submitError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                <span>{submitError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !studentAnswer.trim()}
              className="w-full py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-slate-950 font-bold text-sm transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center space-x-2"
            >
              {submitting ? (
                <span className="inline-block animate-spin h-4 w-4 border-2 border-slate-950 border-t-transparent rounded-full" />
              ) : (
                <>
                  <span>Submit Answer & Update Learner Model</span>
                  <Send className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* Submitted Attempt Feedback & Learner Model Trace Card */}
      {lastAttemptResult && (
        <div className="bg-slate-900 border border-slate-750 rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6 animate-in fade-in duration-300 mb-8">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div className="flex items-center space-x-3">
              {lastAttemptResult.correct ? (
                <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
              ) : (
                <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
                  <XCircle className="h-6 w-6" />
                </div>
              )}
              <div>
                <h3 className="text-lg font-bold text-white">
                  {lastAttemptResult.correct ? 'Correct Deterministic Answer' : 'Incorrect Answer'}
                </h3>
                <p className="text-xs text-slate-400">
                  Correctness checked strictly against answer key (LLM never decides marks).
                </p>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[11px] font-mono text-slate-400 block">Evidence Score</span>
              <span className="text-lg font-bold text-emerald-400 font-mono">
                {lastAttemptResult.evidence.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Reasoning & Misconception Analysis */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-850 border border-slate-800">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Reasoning Classification
              </span>
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-semibold uppercase bg-slate-800 text-slate-200 border border-slate-700">
                <span>Level:</span>
                <strong className={lastAttemptResult.reasoning === 'sound' ? 'text-emerald-400' : 'text-amber-400'}>
                  {lastAttemptResult.reasoning}
                </strong>
              </span>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                LLM Status: {lastAttemptResult.llm_status}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-850 border border-slate-800">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Detected Misconception
              </span>
              {lastAttemptResult.misconception_id ? (
                <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  {lastAttemptResult.misconception_id}
                </span>
              ) : (
                <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                  NONE (No controlled trap detected)
                </span>
              )}
            </div>
          </div>

          {/* Student-facing Feedback */}
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-750">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              Feedback & Diagnostic Guidance
            </span>
            <p className="text-xs text-slate-200 leading-relaxed">
              {lastAttemptResult.feedback}
            </p>
          </div>

          {/* Concept Mastery Delta Updates */}
          {lastAttemptResult.concept_mastery_updates && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                Learner Model Updates (update_mastery)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(lastAttemptResult.concept_mastery_updates).map(([cid, update]) => (
                  <div key={cid} className="p-3 rounded-xl bg-slate-850 border border-slate-800 flex items-center justify-between">
                    <div>
                      <span className="text-xs font-mono text-slate-300 block">{cid}</span>
                      <span className="text-[11px] text-slate-500">
                        {(update.mastery_before * 100).toFixed(1)}% &rarr; {(update.mastery_after * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center space-x-1 font-mono text-xs font-bold">
                      {update.change >= 0 ? (
                        <span className="text-emerald-400 flex items-center">
                          <TrendingUp className="h-3.5 w-3.5 mr-0.5" />
                          +{(update.change * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-rose-400 flex items-center">
                          <TrendingDown className="h-3.5 w-3.5 mr-0.5" />
                          {(update.change * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action button to proceed */}
          <div className="pt-2 flex justify-end">
            <button
              onClick={() => {
                setLastAttemptResult(null);
                fetchNextQuestion();
              }}
              className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs transition-colors flex items-center space-x-2"
            >
              <span>Next Adaptive Question</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
