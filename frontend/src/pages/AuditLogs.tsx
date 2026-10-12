import React, { useEffect, useState } from 'react';
import { getAuditLogs } from '../api/client';
import { AuditLog } from '../types';
import {
  FileText,
  Filter,
  CheckCircle2,
  XCircle,
  Download,
  Clock,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';

export const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [decisionFilter, setDecisionFilter] = useState('');

  useEffect(() => {
    loadLogs();
  }, [decisionFilter]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const res = await getAuditLogs(50, decisionFilter || undefined);
      setLogs(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = () => {
    const headers = ['Timestamp', 'Query', 'Decision', 'Provider', 'Latency(ms)', 'Probability', 'Threshold', 'Rejection Reasons'];
    const rows = logs.map((l) => [
      l.created_at,
      `"${l.query_text.replace(/"/g, '""')}"`,
      l.decision,
      l.provider_used,
      l.total_latency_ms,
      l.calibrated_probability ?? '',
      l.applied_threshold ?? '',
      `"${l.rejection_reasons.join('; ')}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `cache_audit_logs_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Audit & Security Decision Logs</h2>
          <p className="text-xs text-slate-500 mt-1">
            Complete provenance trace for every cached response and fallback inference.
          </p>
        </div>

        <button
          onClick={exportCSV}
          disabled={logs.length === 0}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 shadow-2xs transition cursor-pointer"
        >
          <Download className="h-3.5 w-3.5" />
          <span>Export Audit Log (CSV)</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:outline-none"
          >
            <option value="">All Decisions</option>
            <option value="HIT">Cache Hits Only</option>
            <option value="CACHE_MISS">Cache Misses / Fallbacks</option>
          </select>
        </div>

        <span className="text-xs text-slate-400 font-medium">Showing {logs.length} most recent queries</span>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Query</th>
              <th className="py-3 px-4">Decision</th>
              <th className="py-3 px-4">Safety & Match</th>
              <th className="py-3 px-4">Latency</th>
              <th className="py-3 px-4">Candidate / Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-slate-50/60 transition">
                <td className="py-3.5 px-4 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                  {new Date(log.created_at).toLocaleTimeString()}
                </td>
                <td className="py-3.5 px-4 max-w-xs">
                  <p className="font-semibold text-slate-900 line-clamp-2">{log.query_text}</p>
                </td>
                <td className="py-3.5 px-4 whitespace-nowrap">
                  {log.decision === 'HIT' ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="h-3 w-3" />
                      HIT
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                      <XCircle className="h-3 w-3" />
                      MISS
                    </span>
                  )}
                </td>
                <td className="py-3.5 px-4">
                  <div className="space-y-0.5 text-[11px] font-mono">
                    <div>P(cal): <span className="font-bold text-slate-900">{log.calibrated_probability?.toFixed(3) ?? 'N/A'}</span></div>
                    <div>&tau;: <span className="text-slate-500">{log.applied_threshold?.toFixed(2) ?? 'N/A'}</span></div>
                  </div>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-700 whitespace-nowrap">
                  {log.total_latency_ms.toFixed(1)} ms
                </td>
                <td className="py-3.5 px-4 max-w-sm text-slate-600 text-[11px]">
                  {log.decision === 'HIT' ? (
                    <span className="text-slate-700 italic">Matched: "{log.candidate_question}"</span>
                  ) : (
                    <span className="text-amber-800">{log.rejection_reasons.join(', ') || 'Fallback triggered'}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
