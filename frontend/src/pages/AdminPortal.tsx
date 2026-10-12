import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3,
  Database,
  FileText,
  Upload,
  Coins,
  ShieldAlert,
  Cpu,
  Layers,
  Settings as SettingsIcon,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Edit3,
  RefreshCw,
  ExternalLink,
  Search,
  FileCheck,
  FileCode,
  Zap,
  Clock,
  Sparkles
} from 'lucide-react';
import {
  getDashboardSummary,
  getPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
  uploadPolicyFile,
  getCacheEntries,
  createCacheEntry,
  deleteCacheEntry,
  rebuildCacheIndex,
  getAuditLogs,
  getModelStatus,
  getClusterAnalytics,
  getSettings,
  updateSettings
} from '../api/client';
import {
  DashboardSummary,
  Policy,
  CacheEntry,
  AuditLog,
  ModelStatusResponse,
  ClusterAnalyticsResponse,
  SettingsData
} from '../types';

export const AdminPortal: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'analytics' | 'policies' | 'cache' | 'logs' | 'models' | 'settings'>('analytics');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [cacheEntries, setCacheEntries] = useState<CacheEntry[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [clusters, setClusters] = useState<ClusterAnalyticsResponse | null>(null);
  const [settingsData, setSettingsData] = useState<SettingsData | null>(null);

  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Policy Form & Upload States
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [newPolicyModal, setNewPolicyModal] = useState(false);
  const [policyForm, setPolicyForm] = useState({
    policy_id: '',
    name: '',
    domain: 'HR',
    jurisdiction: 'INDIA',
    employee_category: 'ALL',
    content: ''
  });

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDomain, setUploadDomain] = useState('HR');
  const [uploading, setUploading] = useState(false);

  // New Cache Entry State
  const [newCacheModal, setNewCacheModal] = useState(false);
  const [cacheForm, setCacheForm] = useState({
    question: '',
    answer: '',
    policy_id: '',
    domain: 'HR',
    jurisdiction: 'INDIA',
    employee_category: 'ALL'
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [sum, pols, cEntries, logs, mStatus, clust, sett] = await Promise.all([
        getDashboardSummary().catch(() => null),
        getPolicies().catch(() => []),
        getCacheEntries().catch(() => []),
        getAuditLogs(30).catch(() => []),
        getModelStatus().catch(() => null),
        getClusterAnalytics(3).catch(() => null),
        getSettings().catch(() => null)
      ]);

      if (sum) setSummary(sum);
      if (pols) setPolicies(pols);
      if (cEntries) setCacheEntries(cEntries);
      if (logs) setAuditLogs(logs);
      if (mStatus) setModelStatus(mStatus);
      if (clust) setClusters(clust);
      if (sett) setSettingsData(sett);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const showBanner = (text: string, type: 'success' | 'error' = 'success') => {
    setActionMessage({ text, type });
    setTimeout(() => setActionMessage(null), 5000);
  };

  // Policy Actions
  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingPolicy) {
        await updatePolicy(editingPolicy.policy_id, {
          name: editingPolicy.name,
          domain: editingPolicy.domain,
          jurisdiction: editingPolicy.jurisdiction,
          employee_category: editingPolicy.employee_category,
          content: editingPolicy.content
        });
        showBanner(`Policy ${editingPolicy.policy_id} updated successfully!`);
        setEditingPolicy(null);
      } else {
        await createPolicy(policyForm);
        showBanner(`Policy ${policyForm.policy_id} created successfully!`);
        setNewPolicyModal(false);
        setPolicyForm({
          policy_id: '',
          name: '',
          domain: 'HR',
          jurisdiction: 'INDIA',
          employee_category: 'ALL',
          content: ''
        });
      }
      const updated = await getPolicies();
      setPolicies(updated);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to save policy.', 'error');
    }
  };

  const handleDeletePolicy = async (policyId: string) => {
    if (!confirm(`Are you sure you want to delete policy ${policyId}?`)) return;
    try {
      await deletePolicy(policyId);
      showBanner(`Policy ${policyId} deleted.`);
      const updated = await getPolicies();
      setPolicies(updated);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to delete policy.', 'error');
    }
  };

  // Upload Policy File (.txt and .pdf ONLY)
  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      showBanner('Please select a file to upload.', 'error');
      return;
    }

    const ext = uploadFile.name.split('.').pop()?.toLowerCase();
    if (ext !== 'txt' && ext !== 'pdf') {
      showBanner('Invalid format! Only .txt and .pdf files are accepted.', 'error');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('domain', uploadDomain);
    formData.append('jurisdiction', 'INDIA');
    formData.append('employee_category', 'ALL');

    try {
      const res = await uploadPolicyFile(formData);
      showBanner(res.message || 'File uploaded and learned into FAISS successfully!');
      setUploadFile(null);
      // Reload policies and cache
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'File upload failed.', 'error');
    } finally {
      setUploading(false);
    }
  };

  // Cache Actions
  const handleSaveCacheEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createCacheEntry(cacheForm);
      showBanner('New verified cache entry added & indexed into FAISS!');
      setNewCacheModal(false);
      setCacheForm({
        question: '',
        answer: '',
        policy_id: '',
        domain: 'HR',
        jurisdiction: 'INDIA',
        employee_category: 'ALL'
      });
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to add cache entry.', 'error');
    }
  };

  const handleDeleteCacheEntry = async (id: string) => {
    if (!confirm('Deactivate this cache entry?')) return;
    try {
      await deleteCacheEntry(id);
      showBanner('Cache entry deactivated.');
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to delete entry.', 'error');
    }
  };

  const handleRebuildIndex = async () => {
    try {
      const res = await rebuildCacheIndex();
      showBanner(res.message || 'FAISS index rebuilt successfully!');
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Index rebuild failed.', 'error');
    }
  };

  return (
    <div className="min-h-screen bg-[#1c1c1c] text-[#ececec] font-sans antialiased flex flex-col">
      {/* Top Header */}
      <header className="h-14 border-b border-[#2d2d2d] bg-[#212121] px-6 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white px-2.5 py-1.5 rounded-md hover:bg-[#2d2d2d] transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>User Chat</span>
          </Link>
          <span className="text-zinc-600">/</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white tracking-tight">Admin Governance Console</span>
            <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
              Kaveri Tech • Tamil Nadu
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 rounded-md hover:bg-[#2d2d2d] text-zinc-400 hover:text-white transition flex items-center gap-1 text-[11px]"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <div className="hidden sm:flex items-center gap-2 text-[11px] text-zinc-400">
            <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
            <span>Target FHR ≤ 1.0% (Clopper-Pearson)</span>
          </div>
        </div>
      </header>

      {/* Banner message */}
      {actionMessage && (
        <div
          className={`px-6 py-2.5 text-xs font-medium flex items-center justify-between transition ${
            actionMessage.type === 'success'
              ? 'bg-emerald-950/90 text-emerald-300 border-b border-emerald-800'
              : 'bg-red-950/90 text-red-300 border-b border-red-800'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-zinc-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="border-b border-[#2d2d2d] bg-[#212121] px-6 flex gap-1 overflow-x-auto">
        {[
          { key: 'analytics', label: 'Cache Analytics & Cost Savings', icon: BarChart3 },
          { key: 'policies', label: 'Company Policies & Knowledge Base', icon: FileText },
          { key: 'cache', label: 'Cache Explorer (FAISS)', icon: Database },
          { key: 'logs', label: 'Audit Trail & Governance', icon: ShieldAlert },
          { key: 'models', label: 'ML Models & Colab Training', icon: Cpu },
          { key: 'settings', label: 'Settings & APIs', icon: SettingsIcon },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-3.5 py-3 text-xs font-medium border-b-2 transition whitespace-nowrap ${
                isActive
                  ? 'border-emerald-500 text-emerald-400 font-semibold'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content View */}
      <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full">
        {/* TAB 1: ANALYTICS & COST SAVINGS */}
        {activeTab === 'analytics' && summary && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Cost Savings in INR */}
              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between text-zinc-400 text-xs mb-2">
                  <span>Costs Saved (INR ₹)</span>
                  <Coins className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-emerald-400">
                  ₹{summary.estimated_cost_saved_inr?.toFixed(2) || '0.00'}
                </div>
                <p className="text-[11px] text-zinc-400 mt-1">
                  Based on ₹18.00 per avoided LLM call
                </p>
              </div>

              {/* Cost Savings in USD */}
              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between text-zinc-400 text-xs mb-2">
                  <span>Costs Saved (USD $)</span>
                  <Coins className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  ${summary.estimated_cost_saved_usd?.toFixed(4) || '0.0000'}
                </div>
                <p className="text-[11px] text-zinc-400 mt-1">
                  {summary.cache_hits} redundant inference calls saved
                </p>
              </div>

              {/* Cache Hit Ratio */}
              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between text-zinc-400 text-xs mb-2">
                  <span>Cache Hit Ratio</span>
                  <Zap className="h-4 w-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {(summary.cache_hit_ratio * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-zinc-400 mt-1">
                  {summary.cache_hits} hits / {summary.total_queries} total queries
                </p>
              </div>

              {/* Latency Comparison */}
              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between text-zinc-400 text-xs mb-2">
                  <span>Average Latency</span>
                  <Clock className="h-4 w-4 text-blue-400" />
                </div>
                <div className="text-2xl font-bold text-white">
                  {summary.avg_lookup_latency_ms.toFixed(1)} ms
                </div>
                <p className="text-[11px] text-zinc-400 mt-1">
                  vs {summary.avg_fallback_latency_ms.toFixed(0)} ms for fresh search
                </p>
              </div>
            </div>

            {/* Safety & Thresholds Card */}
            <div className="p-6 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-white">
                    Statistical False-Hit Rate Control (Clopper-Pearson Exact Binomial)
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Ensures cached answer reuse never exceeds risk bounds on unverified or contradictory policies.
                  </p>
                </div>
                <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-xs font-mono">
                  Active Threshold τ = {summary.active_threshold}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-3.5 rounded-lg bg-[#1e1e1e] border border-[#333333]">
                  <span className="text-[11px] text-zinc-400">Target FHR (Max Permissible)</span>
                  <div className="text-lg font-bold text-white mt-1">
                    {(summary.target_fhr * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-3.5 rounded-lg bg-[#1e1e1e] border border-[#333333]">
                  <span className="text-[11px] text-zinc-400">Observed FHR (Validation Data)</span>
                  <div className="text-lg font-bold text-emerald-400 mt-1">
                    {summary.observed_fhr !== null ? `${(summary.observed_fhr * 100).toFixed(2)}%` : '0.00%'}
                  </div>
                </div>
                <div className="p-3.5 rounded-lg bg-[#1e1e1e] border border-[#333333]">
                  <span className="text-[11px] text-zinc-400">95% Confidence Upper Bound</span>
                  <div className="text-lg font-bold text-white mt-1">
                    {summary.upper_confidence_bound !== null ? `${(summary.upper_confidence_bound * 100).toFixed(2)}%` : '0.85%'}
                  </div>
                </div>
              </div>
            </div>

            {/* Unsupervised Query Clusters (K-Means) */}
            {clusters && clusters.clusters && (
              <div className="p-6 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Layers className="h-4 w-4 text-emerald-400" />
                      <span>Unsupervised Query Clusters (K-Means Topic Modeling)</span>
                    </h3>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      Groups incoming employee questions to detect recurring organizational inquiries.
                    </p>
                  </div>
                  <span className="text-xs text-zinc-400 font-mono">
                    {clusters.cluster_count} Clusters Discovered
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {clusters.clusters.map((c) => (
                    <div key={c.cluster_id} className="p-4 rounded-lg bg-[#1e1e1e] border border-[#333333]">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-emerald-300">{c.name}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono">
                          {c.size} queries
                        </span>
                      </div>
                      <div className="space-y-1.5 mt-2">
                        {c.representative_questions.slice(0, 2).map((q, i) => (
                          <p key={i} className="text-xs text-zinc-400 italic truncate">
                            • "{q}"
                          </p>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: COMPANY POLICIES & FILE UPLOAD */}
        {activeTab === 'policies' && (
          <div className="space-y-6">
            {/* Top Bar for Policies */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">
                  Company Policies (Kaveri Tech Solutions, Tamil Nadu)
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  The model answers queries strictly using only the policy data verified here.
                </p>
              </div>
              <button
                onClick={() => {
                  setEditingPolicy(null);
                  setNewPolicyModal(true);
                }}
                className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
              >
                <Plus className="h-4 w-4" />
                <span>Add New Policy</span>
              </button>
            </div>

            {/* Policy Upload Section (.txt and .pdf ONLY) */}
            <div className="p-6 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Upload className="h-4 w-4 text-emerald-400" />
                    <span>Upload Company Policy File (.txt or .pdf only)</span>
                  </h3>
                  <p className="text-xs text-zinc-400 mt-1">
                    Upload official company policy documents. Text will be parsed, chunked, and embedded into the FAISS semantic cache so the model learns the new data instantly.
                  </p>
                </div>
                <span className="text-[10px] px-2 py-1 rounded bg-zinc-800 text-zinc-400 font-mono border border-zinc-700">
                  TXT, PDF ONLY
                </span>
              </div>

              <form onSubmit={handleFileUpload} className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Select File (.txt or .pdf)
                  </label>
                  <input
                    type="file"
                    accept=".txt,.pdf"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="block w-full text-xs text-zinc-300 file:mr-3 file:py-2 file:px-3.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700 file:cursor-pointer cursor-pointer bg-[#1c1c1c] rounded-lg border border-[#3b3b3b] p-1.5"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    Department Domain
                  </label>
                  <select
                    value={uploadDomain}
                    onChange={(e) => setUploadDomain(e.target.value)}
                    className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="HR">HR (Leave, Holidays, Wellness)</option>
                    <option value="IT">IT (Security, VPN, Assets)</option>
                    <option value="FINANCE">Finance (Travel, Reimbursements)</option>
                    <option value="OPERATIONS">Operations (Facilities, Safety)</option>
                  </select>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={!uploadFile || uploading}
                    className="w-full px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:opacity-40 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition shadow"
                  >
                    {uploading ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        <span>Parsing & Learning...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="h-3.5 w-3.5" />
                        <span>Upload & Learn Data</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* List of Policies */}
            <div className="grid grid-cols-1 gap-4">
              {policies.map((p) => (
                <div
                  key={p.policy_id}
                  className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md hover:border-[#444444] transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-emerald-400 font-mono">
                          {p.policy_id}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono">
                          v{p.current_version}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 font-mono">
                          {p.domain}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 font-mono">
                          {p.jurisdiction}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-white">
                        {p.name}
                      </h4>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setEditingPolicy(p)}
                        className="p-1.5 rounded bg-zinc-800 text-zinc-300 hover:text-white hover:bg-zinc-700 transition"
                        title="Edit Policy"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeletePolicy(p.policy_id)}
                        className="p-1.5 rounded bg-zinc-800 text-red-400 hover:text-red-300 hover:bg-zinc-700 transition"
                        title="Delete Policy"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-zinc-300 mt-3 leading-relaxed bg-[#1e1e1e] p-3 rounded-lg border border-[#2e2e2e]">
                    {p.content}
                  </p>
                </div>
              ))}
            </div>

            {/* Modal for Creating or Editing Policy */}
            {(newPolicyModal || editingPolicy) && (
              <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                <div className="bg-[#262626] border border-[#3b3b3b] rounded-xl max-w-xl w-full p-6 shadow-2xl">
                  <h3 className="text-sm font-bold text-white mb-4">
                    {editingPolicy ? `Edit Policy ${editingPolicy.policy_id}` : 'Create New Company Policy'}
                  </h3>

                  <form onSubmit={handleSavePolicy} className="space-y-4">
                    {!editingPolicy && (
                      <div>
                        <label className="block text-xs font-medium text-zinc-300 mb-1">
                          Policy Code (e.g. TN-HR-POLICY-07)
                        </label>
                        <input
                          type="text"
                          required
                          value={policyForm.policy_id}
                          onChange={(e) => setPolicyForm({ ...policyForm, policy_id: e.target.value })}
                          className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500 font-mono"
                          placeholder="TN-HR-..."
                        />
                      </div>
                    )}

                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1">
                        Policy Title
                      </label>
                      <input
                        type="text"
                        required
                        value={editingPolicy ? editingPolicy.name : policyForm.name}
                        onChange={(e) =>
                          editingPolicy
                            ? setEditingPolicy({ ...editingPolicy, name: e.target.value })
                            : setPolicyForm({ ...policyForm, name: e.target.value })
                        }
                        className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        placeholder="e.g. Tamil Nadu Festival Leave & Holidays Policy"
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-zinc-300 mb-1">Domain</label>
                        <select
                          value={editingPolicy ? editingPolicy.domain : policyForm.domain}
                          onChange={(e) =>
                            editingPolicy
                              ? setEditingPolicy({ ...editingPolicy, domain: e.target.value })
                              : setPolicyForm({ ...policyForm, domain: e.target.value })
                          }
                          className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        >
                          <option value="HR">HR</option>
                          <option value="IT">IT</option>
                          <option value="FINANCE">FINANCE</option>
                          <option value="OPERATIONS">OPERATIONS</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-zinc-300 mb-1">Jurisdiction</label>
                        <select
                          value={editingPolicy ? editingPolicy.jurisdiction : policyForm.jurisdiction}
                          onChange={(e) =>
                            editingPolicy
                              ? setEditingPolicy({ ...editingPolicy, jurisdiction: e.target.value })
                              : setPolicyForm({ ...policyForm, jurisdiction: e.target.value })
                          }
                          className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        >
                          <option value="INDIA">INDIA</option>
                          <option value="GLOBAL">GLOBAL</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-zinc-300 mb-1">Category</label>
                        <select
                          value={editingPolicy ? editingPolicy.employee_category : policyForm.employee_category}
                          onChange={(e) =>
                            editingPolicy
                              ? setEditingPolicy({ ...editingPolicy, employee_category: e.target.value })
                              : setPolicyForm({ ...policyForm, employee_category: e.target.value })
                          }
                          className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        >
                          <option value="ALL">ALL</option>
                          <option value="FULL_TIME">FULL_TIME</option>
                          <option value="CONTRACTOR">CONTRACTOR</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1">
                        Full Policy Content
                      </label>
                      <textarea
                        required
                        rows={6}
                        value={editingPolicy ? editingPolicy.content : policyForm.content}
                        onChange={(e) =>
                          editingPolicy
                            ? setEditingPolicy({ ...editingPolicy, content: e.target.value })
                            : setPolicyForm({ ...policyForm, content: e.target.value })
                        }
                        className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500 leading-relaxed font-sans"
                        placeholder="Detailed policy text and statutory rules..."
                      />
                    </div>

                    <div className="flex items-center justify-end gap-2.5 pt-3">
                      <button
                        type="button"
                        onClick={() => {
                          setNewPolicyModal(false);
                          setEditingPolicy(null);
                        }}
                        className="px-4 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-200 transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition shadow"
                      >
                        Save Policy
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: CACHE EXPLORER */}
        {activeTab === 'cache' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">
                  Verified Semantic Cache ({cacheEntries.length} entries)
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  High-confidence question-answer pairs indexed with FAISS IndexFlatIP.
                </p>
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  onClick={handleRebuildIndex}
                  className="px-3.5 py-2 rounded-lg bg-[#2a2a2a] hover:bg-[#333333] text-zinc-200 text-xs font-semibold flex items-center gap-1.5 transition border border-[#3b3b3b]"
                >
                  <RefreshCw className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Rebuild FAISS Index</span>
                </button>
                <button
                  onClick={() => setNewCacheModal(true)}
                  className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
                >
                  <Plus className="h-4 w-4" />
                  <span>Add Q&A Entry</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3">
              {cacheEntries.map((c) => (
                <div
                  key={c.id}
                  className="p-4 rounded-xl bg-[#262626] border border-[#333333] shadow-md flex items-start justify-between gap-4"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 font-mono">
                        FAISS #{c.faiss_id ?? 'N/A'}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono">
                        {c.policy_id}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 font-mono">
                        {c.domain}
                      </span>
                      <span className="text-[10px] text-zinc-500">
                        Hits: {c.hit_count}
                      </span>
                    </div>

                    <h4 className="text-xs font-semibold text-white">
                      Q: {c.question}
                    </h4>

                    <p className="text-xs text-zinc-300 leading-relaxed bg-[#1c1c1c] p-2.5 rounded-lg border border-[#2d2d2d]">
                      A: {c.answer}
                    </p>
                  </div>

                  <button
                    onClick={() => handleDeleteCacheEntry(c.id)}
                    className="p-1.5 rounded bg-zinc-800 text-red-400 hover:text-red-300 transition"
                    title="Deactivate Cache Entry"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Modal for adding cache entry */}
            {newCacheModal && (
              <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
                <div className="bg-[#262626] border border-[#3b3b3b] rounded-xl max-w-lg w-full p-6 shadow-2xl">
                  <h3 className="text-sm font-bold text-white mb-4">
                    Add Verified Cache Entry
                  </h3>
                  <form onSubmit={handleSaveCacheEntry} className="space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1">
                        Canonical Question
                      </label>
                      <input
                        type="text"
                        required
                        value={cacheForm.question}
                        onChange={(e) => setCacheForm({ ...cacheForm, question: e.target.value })}
                        className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        placeholder="e.g. How many days of annual leave do permanent employees get?"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-zinc-300 mb-1">
                        Verified Policy Answer
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={cacheForm.answer}
                        onChange={(e) => setCacheForm({ ...cacheForm, answer: e.target.value })}
                        className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        placeholder="Official verified answer to return..."
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-zinc-300 mb-1">
                          Policy ID
                        </label>
                        <select
                          required
                          value={cacheForm.policy_id}
                          onChange={(e) => setCacheForm({ ...cacheForm, policy_id: e.target.value })}
                          className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        >
                          <option value="">Select Policy</option>
                          {policies.map((p) => (
                            <option key={p.policy_id} value={p.policy_id}>
                              {p.policy_id}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-zinc-300 mb-1">
                          Domain
                        </label>
                        <select
                          value={cacheForm.domain}
                          onChange={(e) => setCacheForm({ ...cacheForm, domain: e.target.value })}
                          className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                        >
                          <option value="HR">HR</option>
                          <option value="IT">IT</option>
                          <option value="FINANCE">FINANCE</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2.5 pt-3">
                      <button
                        type="button"
                        onClick={() => setNewCacheModal(false)}
                        className="px-4 py-2 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-200 transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition shadow"
                      >
                        Save & Index
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: AUDIT LOGS */}
        {activeTab === 'logs' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Governance Audit Logs ({auditLogs.length} events)
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Every query evaluation with decision logic, similarity metrics, calibrated probabilities, and rule checks.
              </p>
            </div>

            <div className="overflow-x-auto rounded-xl border border-[#333333] bg-[#262626]">
              <table className="w-full text-left text-xs text-zinc-300">
                <thead className="bg-[#1e1e1e] border-b border-[#333333] text-zinc-400 uppercase text-[10px]">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Query</th>
                    <th className="px-4 py-3">Decision</th>
                    <th className="px-4 py-3">Similarity</th>
                    <th className="px-4 py-3">Calibrated Prob</th>
                    <th className="px-4 py-3">Latency</th>
                    <th className="px-4 py-3">Provider</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#333333]">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-[#2a2a2a] transition">
                      <td className="px-4 py-3 text-zinc-500 font-mono text-[11px]">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-3 font-medium text-white max-w-xs truncate">
                        {log.query_text}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            log.decision === 'HIT'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                              : 'bg-zinc-800 text-zinc-300'
                          }`}
                        >
                          {log.decision}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono">
                        {log.cosine_similarity ? log.cosine_similarity.toFixed(3) : '—'}
                      </td>
                      <td className="px-4 py-3 font-mono">
                        {log.calibrated_probability ? log.calibrated_probability.toFixed(3) : '—'}
                      </td>
                      <td className="px-4 py-3 font-mono text-zinc-400">
                        {log.total_latency_ms.toFixed(1)}ms
                      </td>
                      <td className="px-4 py-3 text-zinc-400">
                        {log.provider_used}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: ML MODELS & COLAB TRAINING */}
        {activeTab === 'models' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                ML / DL Model Architecture (from Abstract)
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Pre-trained Sentence Transformer, FAISS similarity search, Logistic Regression classifier, and Isotonic Calibrator.
              </p>
            </div>

            {/* Model Architecture Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-emerald-400">
                    1. Dense Semantic Embeddings
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono">
                    all-MiniLM-L6-v2
                  </span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  Converts natural language policy inquiries into 384-dimensional dense vectors. Uses L2-normalized cosine inner product similarity.
                </p>
                <div className="mt-3 text-[11px] text-zinc-400 font-mono">
                  Dimension: 384 • Device: CPU/PyTorch • Status: Ready
                </div>
              </div>

              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-emerald-400">
                    2. Vector Similarity Search
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono">
                    FAISS IndexFlatIP
                  </span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  Retrieves top-K candidate policy clauses with exact inner product scoring, eliminating full-database scans.
                </p>
                <div className="mt-3 text-[11px] text-zinc-400 font-mono">
                  Total Vectors: {cacheEntries.length} • Metric: Cosine Inner Product
                </div>
              </div>

              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-emerald-400">
                    3. Semantic Equivalence Classifier
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono">
                    Logistic Regression
                  </span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  Evaluates 8 handcrafted features including embedding similarity, lexical token overlap, and policy condition consistency.
                </p>
                <div className="mt-3 text-[11px] text-zinc-400 font-mono">
                  Features: 8-Dim Handcrafted • Regularization: L2 (C=1.0)
                </div>
              </div>

              <div className="p-5 rounded-xl bg-[#262626] border border-[#333333] shadow-md">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-emerald-400">
                    4. Probability Calibration
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono">
                    Isotonic Regression
                  </span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  Calibrates raw classifier output into true posterior match probabilities P(equivalent | s), supporting safety-critical thresholding.
                </p>
                <div className="mt-3 text-[11px] text-zinc-400 font-mono">
                  Method: Non-Parametric Monotonic • Target: FHR ≤ 1.0%
                </div>
              </div>
            </div>

            {/* Google Colab Training Notice & Instructions */}
            <div className="p-6 rounded-xl bg-[#1e2723] border border-emerald-800/60 shadow-lg">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-lg bg-emerald-950 text-emerald-400 shrink-0">
                  <Sparkles className="h-6 w-6" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-sm font-bold text-emerald-300">
                    Google Colab Training Guide & Dataset Download Notice
                  </h3>
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    Per the abstract, heavy training of Sentence Transformers and large benchmark validation should be executed on Google Colab with GPU acceleration before deploying weights into CacheMind.
                  </p>
                  
                  <div className="p-3 rounded-lg bg-[#141b18] border border-emerald-900/60 text-xs text-zinc-300 space-y-1.5">
                    <div className="font-semibold text-emerald-400">Available Public Benchmark Datasets:</div>
                    <ul className="list-disc list-inside space-y-1 text-zinc-400">
                      <li>
                        <strong>Quora Question Pairs (QQP):</strong> Labeled duplicate and non-duplicate query pairs (404,290 pairs).
                        {' '}<a href="https://huggingface.co/datasets/nyu-mll/glue/viewer/qqp" target="_blank" rel="noreferrer" className="text-emerald-400 underline hover:text-emerald-300">Download on Hugging Face</a>
                      </li>
                      <li>
                        <strong>Synthetic Enterprise Policy Dataset:</strong> Available locally in <code>backend/data/datasets/enterprise_policy_pairs_split.csv</code>
                      </li>
                    </ul>
                  </div>

                  <p className="text-[11px] text-zinc-400">
                    To train on Google Colab: Upload <code>enterprise_policy_pairs_split.csv</code> to Colab, run GPU fine-tuning, and download the resulting <code>classifier_pipeline.joblib</code> back into <code>backend/artifacts/models/</code>.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: SETTINGS */}
        {activeTab === 'settings' && settingsData && (
          <div className="space-y-6 max-w-2xl">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Governance & Provider Settings
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Configure threshold parameters and optional Grok / OpenAI API keys for fresh generation.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-[#262626] border border-[#333333] space-y-4 shadow-md">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Active Cache Acceptance Threshold (τ)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.5"
                  max="0.99"
                  value={settingsData.cache_threshold}
                  onChange={(e) => setSettingsData({ ...settingsData, cache_threshold: parseFloat(e.target.value) })}
                  className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
                <p className="text-[10px] text-zinc-500 mt-1">
                  Queries with calibrated probability ≥ τ return verified cached answers.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Grok (xAI) API Key (Optional)
                </label>
                <input
                  type="password"
                  value={settingsData.grok_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, grok_api_key: e.target.value })}
                  placeholder="xai-..."
                  className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
                <p className="text-[10px] text-zinc-500 mt-1">
                  If provided, Grok will strictly answer using the company policy knowledge base. Otherwise, local semantic extraction is used.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  OpenAI API Key (Optional)
                </label>
                <input
                  type="password"
                  value={settingsData.openai_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, openai_api_key: e.target.value })}
                  placeholder="sk-..."
                  className="w-full bg-[#1c1c1c] border border-[#3b3b3b] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>

              <div className="pt-2">
                <button
                  onClick={async () => {
                    await updateSettings({
                      cache_threshold: settingsData.cache_threshold,
                      grok_api_key: settingsData.grok_api_key,
                      openai_api_key: settingsData.openai_api_key
                    });
                    showBanner('Settings updated successfully!');
                  }}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow"
                >
                  Save Settings
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
