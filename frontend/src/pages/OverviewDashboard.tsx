import React, { useEffect, useState } from 'react';
import { getDashboardSummary } from '../api/client';
import { DashboardSummary } from '../types';
import {
  TrendingUp,
  Zap,
  DollarSign,
  ShieldCheck,
  Clock,
  Layers,
  ArrowUpRight,
  AlertTriangle
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export const OverviewDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSummary();
  }, []);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const res = await getDashboardSummary();
      setData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        Loading real-time enterprise metrics...
      </div>
    );
  }

  const chartData = [
    { name: 'Cache Hits', count: data.cache_hits, fill: '#4f46e5' },
    { name: 'Fallback Misses', count: data.cache_misses, fill: '#94a3b8' }
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Enterprise Overview Dashboard</h2>
        <p className="text-xs text-slate-500 mt-1">
          Production performance, inference cost reduction, and statistical safety metrics.
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Cache Hit Ratio</span>
            <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-900">
              {(data.cache_hit_ratio * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {data.cache_hits} hits / {data.total_queries} queries
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Avg Lookup Latency</span>
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-900">
              {data.avg_lookup_latency_ms.toFixed(1)} ms
            </div>
            <div className="text-[11px] text-emerald-600 font-medium mt-1">
              vs {data.avg_fallback_latency_ms.toFixed(1)} ms fallback
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Inference Cost Saved</span>
            <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-900">
              ${data.estimated_cost_saved_usd.toFixed(3)}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {data.estimated_calls_avoided} LLM calls avoided
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">False-Hit Rate (FHR)</span>
            <div className="p-2 rounded-lg bg-purple-50 text-purple-600">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-900">
              {data.observed_fhr !== null ? `${(data.observed_fhr * 100).toFixed(1)}%` : 'Not evaluated'}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              {data.upper_confidence_bound !== null
                ? `UCB: ${(data.upper_confidence_bound * 100).toFixed(1)}% (95% CI)`
                : 'Target: 1.0%'}
            </div>
          </div>
        </div>
      </div>

      {/* Main Visuals & Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="md:col-span-2 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
          <h3 className="text-sm font-semibold text-slate-900">Cache Hits vs Fallback Queries</h3>
          <p className="text-xs text-slate-400 mt-0.5">Real distribution of served requests from database records</p>
          <div className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: '#f8fafc' }}
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Model Stack Status */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">ML Pipeline & Governance Status</h3>
            <p className="text-xs text-slate-400 mt-0.5">Component initialization health</p>

            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100">
                <span className="text-slate-600 font-medium">Sentence Transformer</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                  {data.model_status.embedding_transformer || 'READY'}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100">
                <span className="text-slate-600 font-medium">FAISS Vector Index</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                  {data.model_status.faiss_index || 'READY'}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100">
                <span className="text-slate-600 font-medium">Logistic Regression</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                  {data.model_status.equivalence_classifier || 'FITTED'}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs py-2 border-b border-slate-100">
                <span className="text-slate-600 font-medium">Isotonic Calibrator</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                  {data.model_status.probability_calibrator || 'CALIBRATED'}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs py-2">
                <span className="text-slate-600 font-medium">Active Safe Threshold</span>
                <span className="font-mono text-slate-900 font-bold">{data.active_threshold}</span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-500 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
            <span>
              Deterministic policy-condition checks are enforced before threshold matching to prevent category or jurisdiction reuse violations.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
