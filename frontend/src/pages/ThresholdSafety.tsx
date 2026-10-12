import React, { useEffect, useState } from 'react';
import { getEvaluationResults, activateThreshold } from '../api/client';
import { EvaluationResultsResponse } from '../types';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  TrendingDown,
  Info
} from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts';

export const ThresholdSafety: React.FC = () => {
  const [data, setData] = useState<EvaluationResultsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activating, setActivating] = useState(false);

  useEffect(() => {
    loadEval();
  }, []);

  const loadEval = async () => {
    try {
      setLoading(true);
      const res = await getEvaluationResults();
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async (tau: number) => {
    try {
      setActivating(true);
      await activateThreshold(tau);
      await loadEval();
    } catch (err) {
      console.error(err);
    } finally {
      setActivating(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        Loading statistical threshold evaluation data...
      </div>
    );
  }

  const chartData = (data.results || []).map((r) => ({
    threshold: r.threshold,
    observed_fhr: Number((r.observed_fhr * 100).toFixed(1)),
    upper_bound: Number((r.upper_confidence_bound * 100).toFixed(1)),
    hits: r.evaluated_hits
  }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Statistical Threshold & Safety Bounds</h2>
        <p className="text-xs text-slate-500 mt-1">
          Rigorous False-Hit Rate (FHR) selection using Clopper-Pearson exact binomial confidence bounds.
        </p>
      </div>

      {/* Primary Status Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Target FHR Objective</span>
            <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full">
              {(data.target_fhr * 100).toFixed(1)}% Max
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-3">
            {data.selected_threshold ? data.selected_threshold.toFixed(2) : 'None'}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Current active acceptance threshold &tau;
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Clopper-Pearson Confidence</span>
            <span className="text-xs font-semibold text-slate-700 font-mono">
              {(data.confidence_level * 100).toFixed(0)}% One-Sided
            </span>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-3">
            {data.upper_confidence_bound ? `${(data.upper_confidence_bound * 100).toFixed(1)}%` : '100%'}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Statistical Upper Confidence Bound (UCB)
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Evaluation Sample Size</span>
            <span className="text-xs font-semibold text-slate-700 font-mono">Validation Split</span>
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-3">
            {data.sample_size} Pairs
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            False hits observed: {data.false_hits}
          </p>
        </div>
      </div>

      {/* Safety Notice Regarding Academic Claims */}
      <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl flex items-start gap-3 text-xs text-amber-900">
        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold block">Academic Integrity Notice:</span>
          <span>
            Under small validation sample sizes (e.g. N &lt; 100), Clopper-Pearson bounds remain conservative.
            The system refuses to fabricate a 1% claim without empirical validation backing. Conservative fallback mode is safely activated.
          </span>
        </div>
      </div>

      {/* Curve Visualizer */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900">Threshold vs False-Hit Rate (FHR) & Confidence Bound</h3>
        <p className="text-xs text-slate-400 mt-0.5">
          Observed FHR (solid blue) compared with Clopper-Pearson Upper Bound (dashed amber)
        </p>

        <div className="h-72 mt-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="threshold" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} unit="%" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
              />
              <ReferenceLine y={1.0} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'Target 1.0%', fill: '#ef4444', fontSize: 10 }} />
              <Line type="monotone" dataKey="observed_fhr" name="Observed FHR (%)" stroke="#4f46e5" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="upper_bound" name="Upper Bound (%)" stroke="#f59e0b" strokeWidth={2} strokeDasharray="4 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
