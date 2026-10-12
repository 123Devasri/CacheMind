import React, { useEffect, useState } from 'react';
import { getClusterAnalytics } from '../api/client';
import { ClusterAnalyticsResponse } from '../types';
import {
  PieChart,
  Layers,
  Sparkles,
  Info,
  Tag
} from 'lucide-react';
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export const QueryClusters: React.FC = () => {
  const [data, setData] = useState<ClusterAnalyticsResponse | null>(null);
  const [kClusters, setKClusters] = useState(3);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadClusters();
  }, [kClusters]);

  const loadClusters = async () => {
    try {
      setLoading(true);
      const res = await getClusterAnalytics(kClusters);
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        Executing K-Means clustering and PCA dimensionality reduction...
      </div>
    );
  }

  const clusterColors = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899'];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Query Clustering & Topic Analytics</h2>
          <p className="text-xs text-slate-500 mt-1">
            Unsupervised K-Means clustering over dense Sentence Transformer embeddings with 2D PCA projection.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium">Cluster Count (k):</span>
          <select
            value={kClusters}
            onChange={(e) => setKClusters(Number(e.target.value))}
            className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-white focus:outline-none"
          >
            <option value={2}>k = 2</option>
            <option value={3}>k = 3</option>
            <option value={4}>k = 4</option>
            <option value={5}>k = 5</option>
          </select>
        </div>
      </div>

      {/* Analytics Notice */}
      <div className="p-3 bg-slate-100 border border-slate-200 rounded-lg text-xs text-slate-600 flex items-center gap-2">
        <Info className="h-4 w-4 text-slate-500 shrink-0" />
        <span>
          <strong>Important Architecture Rule:</strong> K-Means clustering is strictly an analytical monitoring tool for identifying recurring policy query patterns; it does NOT independently approve or validate cache hits.
        </span>
      </div>

      {/* 2D PCA Scatter Visualization */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900">2D PCA Embedding Projection</h3>
        <p className="text-xs text-slate-400 mt-0.5">Approximate 2-dimensional visualization of query clusters</p>

        <div className="h-72 mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 20, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis type="number" dataKey="x" name="PCA 1" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis type="number" dataKey="y" name="PCA 2" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <Tooltip
                cursor={{ strokeDasharray: '3 3' }}
                content={({ payload }) => {
                  if (payload && payload.length > 0) {
                    const pt = payload[0].payload;
                    return (
                      <div className="bg-slate-900 text-white p-2.5 rounded-lg text-[11px] shadow-lg max-w-xs">
                        <div className="font-semibold text-indigo-300">Cluster {pt.cluster_id + 1}</div>
                        <div className="mt-1">{pt.question}</div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              {data.clusters.map((c, idx) => {
                const clusterPoints = data.points.filter((p) => p.cluster_id === c.cluster_id);
                return (
                  <Scatter
                    key={c.cluster_id}
                    name={c.name}
                    data={clusterPoints}
                    fill={clusterColors[idx % clusterColors.length]}
                  />
                );
              })}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cluster Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {data.clusters.map((c, idx) => (
          <div key={c.cluster_id} className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                  style={{ backgroundColor: clusterColors[idx % clusterColors.length] }}
                >
                  Cluster {c.cluster_id + 1}
                </span>
                <span className="text-xs text-slate-500 font-medium">{c.size} Queries</span>
              </div>

              <h4 className="text-xs font-bold text-slate-900 mt-3">{c.name}</h4>

              <div className="mt-3 flex flex-wrap gap-1">
                {c.keywords.map((kw, i) => (
                  <span key={i} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                    #{kw}
                  </span>
                ))}
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Sample Inquiries:
                </span>
                {c.representative_questions.map((q, i) => (
                  <p key={i} className="text-[11px] text-slate-700 italic line-clamp-1">
                    "{q}"
                  </p>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
