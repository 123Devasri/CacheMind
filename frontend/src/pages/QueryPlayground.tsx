import React, { useState } from 'react';
import { submitQuery } from '../api/client';
import { QueryResponse } from '../types';
import {
  Send,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Sliders,
  ChevronRight,
  Info
} from 'lucide-react';

export const QueryPlayground: React.FC = () => {
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);

  const sampleQueries = [
    { label: 'Safe Paraphrase (HR Leave)', text: 'How many annual vacation days do permanent employees receive?' },
    { label: 'Adversarial Mismatch (Contractor PTO)', text: 'How many days of annual leave do contractors get?' },
    { label: 'Jurisdiction Conflict (Travel Allowance)', text: 'What is the daily domestic travel per diem in India?' },
    { label: 'Numeric Limit Conflict (Remote Work)', text: 'Can full-time employees work from home 4 days a week?' }
  ];

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      const res = await submitQuery(query, domain ? domain : undefined);
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Interactive Query Playground</h2>
        <p className="text-xs text-slate-500 mt-1">
          Test semantic equivalence matching against company policies with deterministic governance safety checks.
        </p>
      </div>

      {/* Query Form */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-3">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Enterprise Question
              </label>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask about HR vacation, remote work limits, IT hardware, or travel per diem..."
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition min-h-[90px]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Policy Domain (Optional)
              </label>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="w-full px-3 py-2.5 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              >
                <option value="">Auto-Detect Domain</option>
                <option value="HR">HR Policies</option>
                <option value="IT">IT Security & Hardware</option>
                <option value="FINANCE">Finance & Travel Reimbursements</option>
              </select>

              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="w-full mt-3.5 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50 cursor-pointer"
              >
                <Send className="h-3.5 w-3.5" />
                <span>{loading ? 'Evaluating Pipeline...' : 'Process Query'}</span>
              </button>
            </div>
          </div>
        </form>

        {/* Quick Sample Queries */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center gap-2 flex-wrap">
          <span className="text-[11px] text-slate-400 font-medium">Quick Test Scenarios:</span>
          {sampleQueries.map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(item.text);
              }}
              className="text-[11px] bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 px-2.5 py-1 rounded-md transition cursor-pointer"
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Decision Results Container */}
      {result && (
        <div className="space-y-4">
          {/* Main Answer Header */}
          <div
            className={`p-6 rounded-xl border ${
              result.is_cached
                ? 'bg-emerald-50/40 border-emerald-200'
                : 'bg-amber-50/40 border-amber-200'
            }`}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-200/60">
              <div className="flex items-center gap-2">
                {result.is_cached ? (
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-600 text-white">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>CACHE HIT (Reused Verified Policy)</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-600 text-white">
                    <XCircle className="h-3.5 w-3.5" />
                    <span>CACHE MISS (Safe Fallback Inference)</span>
                  </div>
                )}
                <span className="text-xs text-slate-500 font-mono">
                  Provider: {result.provider_used}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-500 font-mono">
                <div className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  <span>Lookup: {result.lookup_latency_ms} ms</span>
                </div>
                <span>|</span>
                <span>Total: {result.total_latency_ms} ms</span>
              </div>
            </div>

            <div className="mt-4">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Delivered Response:
              </h4>
              <p className="mt-1 text-sm font-medium text-slate-900 leading-relaxed bg-white/80 p-3 rounded-lg border border-slate-200/60">
                {result.answer}
              </p>
            </div>

            {result.rejection_reasons.length > 0 && (
              <div className="mt-3.5 p-3 rounded-lg bg-amber-100/60 border border-amber-300 text-xs text-amber-900">
                <span className="font-semibold block mb-1">Rejection Reasons Logged:</span>
                <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                  {result.rejection_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Candidate Diagnostics Grid */}
          {result.candidate && (
            <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
              <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                <Sliders className="h-4 w-4 text-indigo-600" />
                <span>Candidate Match & Safety Breakdown</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left: Matched Question details */}
                <div className="space-y-3">
                  <div>
                    <span className="text-xs font-medium text-slate-400">Retrieved Candidate Question:</span>
                    <p className="text-xs font-semibold text-slate-800 mt-0.5">
                      "{result.candidate.question}"
                    </p>
                  </div>

                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-500 font-medium">Deterministic Safety Check:</span>
                    {result.candidate.policy_condition_passed ? (
                      <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-semibold border border-emerald-200">
                        PASSED (No Policy Conflicts)
                      </span>
                    ) : (
                      <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded font-semibold border border-rose-200">
                        FAILED (Policy Condition Conflict)
                      </span>
                    )}
                  </div>

                  {result.candidate.condition_mismatches.length > 0 && (
                    <div className="text-[11px] text-rose-700 bg-rose-50 p-2 rounded border border-rose-200">
                      {result.candidate.condition_mismatches.join(', ')}
                    </div>
                  )}
                </div>

                {/* Right: ML Scores & Probabilities */}
                <div className="space-y-3 bg-slate-50 p-4 rounded-lg border border-slate-200">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-600 font-medium">FAISS Cosine Similarity:</span>
                    <span className="font-mono font-bold text-slate-900">
                      {result.candidate.cosine_similarity.toFixed(4)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-600 font-medium">Logistic Regression Score:</span>
                    <span className="font-mono font-bold text-slate-900">
                      {result.candidate.classifier_score.toFixed(4)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-600 font-medium">Isotonic Calibrated Probability:</span>
                    <span className="font-mono font-bold text-indigo-600">
                      {result.candidate.calibrated_probability.toFixed(4)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs pt-2 border-t border-slate-200">
                    <span className="text-slate-600 font-medium">Applied Statistical Threshold:</span>
                    <span className="font-mono font-bold text-slate-900">
                      {result.active_threshold.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
