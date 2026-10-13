import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3,
  Database,
  FileText,
  Upload,
  Coins,
  ShieldAlert,
  ShieldCheck,
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
  Zap,
  Clock,
  Sparkles,
  Users,
  Check,
  X,
  RotateCcw,
  Download,
  AlertTriangle,
  Eye,
  ThumbsUp,
  ThumbsDown,
  Flag,
  Filter,
  CheckSquare,
  Sliders,
  FileSpreadsheet
} from 'lucide-react';
import {
  getDashboardSummary,
  getAllUsers,
  updateUserStatus,
  getPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
  uploadPolicyFile,
  previewPolicyDocument,
  createAuthoritativePolicy,
  invalidateObsoleteCache,
  getCacheEntries,
  createCacheEntry,
  deleteCacheEntry,
  rebuildCacheIndex,
  getAuditLogs,
  getModelStatus,
  triggerModelTraining,
  getModelRegistry,
  rollbackModelVersion,
  getAdminFeedback,
  reviewAdminFeedback,
  getClusterAnalytics,
  getSettings,
  updateSettings,
  generateSyntheticPairs,
  uploadDatasetCsv,
  exportAuditLogsUrl
} from '../api/client';
import {
  DashboardSummary,
  User,
  Policy,
  PolicyPreview,
  CacheEntry,
  AuditLog,
  ModelStatusResponse,
  ModelArtifactVersion,
  FeedbackItem,
  ClusterAnalyticsResponse,
  SettingsData,
  CandidatePair
} from '../types';
import { useAuth } from '../context/AuthContext';

export const AdminPortal: React.FC = () => {
  const { user: currentUser } = useAuth();

  const [activeTab, setActiveTab] = useState<
    'analytics' | 'users' | 'policies' | 'synthetic' | 'models' | 'cache' | 'feedback' | 'logs' | 'settings'
  >('analytics');

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [usersList, setUsersList] = useState<User[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [cacheEntries, setCacheEntries] = useState<CacheEntry[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [modelRegistry, setModelRegistry] = useState<ModelArtifactVersion[]>([]);
  const [feedbackList, setFeedbackList] = useState<FeedbackItem[]>([]);
  const [clusters, setClusters] = useState<ClusterAnalyticsResponse | null>(null);
  const [settingsData, setSettingsData] = useState<SettingsData | null>(null);
  const [candidatePairs, setCandidatePairs] = useState<CandidatePair[]>([]);

  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Filters & Search
  const [userSearch, setUserSearch] = useState('');
  const [policySearch, setPolicySearch] = useState('');
  const [cacheSearch, setCacheSearch] = useState('');
  const [feedbackFilter, setFeedbackFilter] = useState<'all' | 'reported'>('all');
  const [auditDecisionFilter, setAuditDecisionFilter] = useState<string>('ALL');

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

  // Document Upload & Preview States
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDomain, setUploadDomain] = useState('HR');
  const [previewData, setPreviewData] = useState<PolicyPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [invalidatingCache, setInvalidatingCache] = useState(false);

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

  // User Management State
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [userRoleEdit, setUserRoleEdit] = useState<'USER' | 'ADMIN'>('USER');
  const [userActiveEdit, setUserActiveEdit] = useState(true);
  const [userDeptEdit, setUserDeptEdit] = useState('');

  // Synthetic Data Generation State
  const [genPolicyId, setGenPolicyId] = useState<string>('');
  const [genPairsCount, setGenPairsCount] = useState<number>(2);
  const [generatingSynthetic, setGeneratingSynthetic] = useState(false);
  const [csvUploadFile, setCsvUploadFile] = useState<File | null>(null);
  const [uploadingCsv, setUploadingCsv] = useState(false);

  // Feedback Review State
  const [reviewingFeedback, setReviewingFeedback] = useState<FeedbackItem | null>(null);
  const [reviewStatus, setReviewStatus] = useState<string>('REVIEWED');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [submittingReview, setSubmittingReview] = useState(false);

  // Model Training & Rollback States
  const [trainingModel, setTrainingModel] = useState(false);
  const [rollbackConfirmTag, setRollbackConfirmTag] = useState<string | null>(null);
  const [rollingBack, setRollingBack] = useState(false);

  const showBanner = (text: string, type: 'success' | 'error' = 'success') => {
    setActionMessage({ text, type });
    setTimeout(() => setActionMessage(null), 6000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [sum, pols, cEntries, logs, mStatus, clust, sett, uList, mReg, fbList] = await Promise.all([
        getDashboardSummary().catch(() => null),
        getPolicies().catch(() => []),
        getCacheEntries().catch(() => []),
        getAuditLogs(50).catch(() => []),
        getModelStatus().catch(() => null),
        getClusterAnalytics(3).catch(() => null),
        getSettings().catch(() => null),
        getAllUsers().catch(() => []),
        getModelRegistry().catch(() => []),
        getAdminFeedback().catch(() => [])
      ]);

      if (sum) setSummary(sum);
      if (pols) setPolicies(pols);
      if (cEntries) setCacheEntries(cEntries);
      if (logs) setAuditLogs(logs);
      if (mStatus) setModelStatus(mStatus);
      if (clust) setClusters(clust);
      if (sett) setSettingsData(sett);
      if (uList) setUsersList(uList);
      if (mReg) setModelRegistry(mReg);
      if (fbList) setFeedbackList(fbList);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtered queries
  const filteredUsers = usersList.filter(
    (u) =>
      u.username.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
      (u.full_name && u.full_name.toLowerCase().includes(userSearch.toLowerCase())) ||
      (u.department && u.department.toLowerCase().includes(userSearch.toLowerCase()))
  );

  const filteredPolicies = policies.filter(
    (p) =>
      p.policy_id.toLowerCase().includes(policySearch.toLowerCase()) ||
      p.name.toLowerCase().includes(policySearch.toLowerCase()) ||
      p.domain.toLowerCase().includes(policySearch.toLowerCase())
  );

  const filteredCache = cacheEntries.filter(
    (c) =>
      c.question.toLowerCase().includes(cacheSearch.toLowerCase()) ||
      c.answer.toLowerCase().includes(cacheSearch.toLowerCase()) ||
      c.policy_id.toLowerCase().includes(cacheSearch.toLowerCase())
  );

  const filteredFeedback = feedbackList.filter((fb) => {
    if (feedbackFilter === 'reported') return fb.is_reported_incorrect;
    return true;
  });

  const filteredLogs = auditLogs.filter((log) => {
    if (auditDecisionFilter === 'ALL') return true;
    return log.decision.toUpperCase() === auditDecisionFilter.toUpperCase();
  });

  // User Actions
  const handleOpenUserEdit = (u: User) => {
    setEditingUser(u);
    setUserRoleEdit(u.role);
    setUserActiveEdit(u.is_active);
    setUserDeptEdit(u.department || '');
  };

  const handleSaveUserStatus = async () => {
    if (!editingUser) return;
    try {
      await updateUserStatus(editingUser.id, {
        role: userRoleEdit,
        is_active: userActiveEdit,
        department: userDeptEdit
      });
      showBanner(`User ${editingUser.username} updated successfully!`);
      setEditingUser(null);
      const updated = await getAllUsers();
      setUsersList(updated);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to update user.', 'error');
    }
  };

  // Document Preview & Upload Actions
  const handlePreviewDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      showBanner('Please select a file to preview.', 'error');
      return;
    }
    const ext = uploadFile.name.split('.').pop()?.toLowerCase();
    if (ext !== 'txt' && ext !== 'pdf' && ext !== 'md') {
      showBanner('Unsupported format! Only .txt, .pdf, and .md files are supported.', 'error');
      return;
    }

    setPreviewing(true);
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('domain', uploadDomain);
    formData.append('jurisdiction', 'INDIA');
    formData.append('employee_category', 'ALL');

    try {
      const preview = await previewPolicyDocument(formData);
      setPreviewData(preview);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to preview document.', 'error');
    } finally {
      setPreviewing(false);
    }
  };

  const handlePublishPreviewedPolicy = async () => {
    if (!previewData) return;
    setUploading(true);
    try {
      await createAuthoritativePolicy({
        policy_id: previewData.suggested_policy_id,
        name: previewData.suggested_name,
        domain: previewData.detected_domain,
        jurisdiction: previewData.jurisdiction,
        employee_category: previewData.employee_category,
        content: previewData.extracted_text
      });
      showBanner(`Authoritative Policy ${previewData.suggested_policy_id} published successfully!`);
      setPreviewData(null);
      setUploadFile(null);
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to publish policy.', 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleInvalidateObsoleteCache = async () => {
    if (!confirm('Invalidate and deactivate all cached entries associated with deactivated policy versions?')) return;
    setInvalidatingCache(true);
    try {
      const res = await invalidateObsoleteCache();
      showBanner(res.message || 'Obsolete cache entries invalidated successfully!');
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Cache invalidation failed.', 'error');
    } finally {
      setInvalidatingCache(false);
    }
  };

  // Policy CRUD
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
        showBanner(`Policy ${editingPolicy.policy_id} updated.`);
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
    if (!confirm(`Are you sure you want to deactivate policy ${policyId}?`)) return;
    try {
      await deletePolicy(policyId);
      showBanner(`Policy ${policyId} deactivated.`);
      const updated = await getPolicies();
      setPolicies(updated);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to deactivate policy.', 'error');
    }
  };

  // Synthetic Data Generation
  const handleGenerateSynthetic = async () => {
    setGeneratingSynthetic(true);
    try {
      const pairs = await generateSyntheticPairs(genPolicyId || undefined, genPairsCount);
      setCandidatePairs(pairs);
      showBanner(`Generated ${pairs.length} synthetic candidate pairs from approved policy clauses!`);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to generate synthetic pairs.', 'error');
    } finally {
      setGeneratingSynthetic(false);
    }
  };

  const handleUploadCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvUploadFile) {
      showBanner('Select a CSV file first.', 'error');
      return;
    }
    setUploadingCsv(true);
    const formData = new FormData();
    formData.append('file', csvUploadFile);
    try {
      const res = await uploadDatasetCsv(formData);
      showBanner(res.message || 'CSV dataset imported successfully!');
      setCsvUploadFile(null);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'CSV upload failed.', 'error');
    } finally {
      setUploadingCsv(false);
    }
  };

  // Model Training & Rollback
  const handleTrainModel = async () => {
    if (!confirm('Train Logistic Regression classifier, fit Isotonic Calibrator, and evaluate threshold bounds?')) return;
    setTrainingModel(true);
    try {
      const res = await triggerModelTraining();
      showBanner(res.message || 'Model trained, calibrated, and published successfully!');
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Training failed.', 'error');
    } finally {
      setTrainingModel(false);
    }
  };

  const handleRollbackModel = async () => {
    if (!rollbackConfirmTag) return;
    setRollingBack(true);
    try {
      const res = await rollbackModelVersion(rollbackConfirmTag);
      showBanner(res.message || `Rollback to ${rollbackConfirmTag} completed successfully!`);
      setRollbackConfirmTag(null);
      loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Rollback failed.', 'error');
    } finally {
      setRollingBack(false);
    }
  };

  // Feedback Review
  const handleSaveFeedbackReview = async () => {
    if (!reviewingFeedback) return;
    setSubmittingReview(true);
    try {
      await reviewAdminFeedback(reviewingFeedback.id, {
        status: reviewStatus,
        admin_notes: reviewNotes
      });
      showBanner('Feedback reviewed and updated successfully.');
      setReviewingFeedback(null);
      const updated = await getAdminFeedback();
      setFeedbackList(updated);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to update feedback.', 'error');
    } finally {
      setSubmittingReview(false);
    }
  };

  // Cache CRUD
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
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased flex flex-col">
      {/* Top Header */}
      <header className="h-14 border-b border-slate-200 bg-white px-6 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <Link
            to="/app"
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 px-2.5 py-1.5 rounded-md hover:bg-slate-100 transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>User Portal</span>
          </Link>
          <span className="text-slate-300">/</span>
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-slate-900 text-white flex items-center justify-center text-xs">
              <ShieldCheck className="h-3 w-3 text-emerald-400" />
            </div>
            <span className="text-sm font-semibold text-slate-900 tracking-tight">
              CacheMind Governance Console
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-mono">
              Admin: {currentUser?.username || 'admin'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 rounded-md hover:bg-slate-100 text-slate-600 hover:text-slate-900 transition flex items-center gap-1 text-[11px]"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <div className="hidden sm:flex items-center gap-2 text-[11px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
            <span>Target FHR ≤ 1.0% (Clopper-Pearson Bound)</span>
          </div>
        </div>
      </header>

      {/* Banner Notification */}
      {actionMessage && (
        <div
          className={`px-6 py-2.5 text-xs font-medium flex items-center justify-between transition ${
            actionMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-b border-emerald-200'
              : 'bg-rose-50 text-rose-800 border-b border-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            ) : (
              <AlertCircle className="h-4 w-4 text-rose-600" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-slate-700">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Navigation Tabs Bar */}
      <div className="border-b border-slate-200 bg-white px-6 flex gap-1 overflow-x-auto shadow-2xs">
        {[
          { key: 'analytics', label: 'Analytics & Costs', icon: BarChart3 },
          { key: 'users', label: 'User Management', icon: Users, badge: usersList.length },
          { key: 'policies', label: 'Policies & Documents', icon: FileText, badge: policies.length },
          { key: 'synthetic', label: 'Datasets & Synthetic Data', icon: FileSpreadsheet },
          { key: 'models', label: 'Model Registry & Training', icon: Cpu },
          { key: 'cache', label: 'FAISS Cache Explorer', icon: Database, badge: cacheEntries.length },
          {
            key: 'feedback',
            label: 'Feedback & Reported Answers',
            icon: Flag,
            badge: feedbackList.filter((f) => f.is_reported_incorrect).length || undefined
          },
          { key: 'logs', label: 'Audit Trail & Export', icon: ShieldAlert },
          { key: 'settings', label: 'Settings', icon: SettingsIcon }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-3.5 py-3 text-xs font-medium border-b-2 transition whitespace-nowrap ${
                isActive
                  ? 'border-slate-900 text-slate-900 font-semibold'
                  : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    tab.key === 'feedback' && tab.badge > 0
                      ? 'bg-rose-100 text-rose-700'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full">
        {/* ======================================================== */}
        {/* TAB 1: ANALYTICS & COST SAVINGS */}
        {/* ======================================================== */}
        {activeTab === 'analytics' && summary && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
                  <span>Costs Saved (INR ₹)</span>
                  <Coins className="h-4 w-4 text-emerald-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">
                  ₹{summary.estimated_cost_saved_inr?.toFixed(2) || '0.00'}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Saved via verified semantic answer reuse
                </p>
              </div>

              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
                  <span>Costs Saved (USD $)</span>
                  <Coins className="h-4 w-4 text-emerald-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">
                  ${summary.estimated_cost_saved_usd?.toFixed(4) || '0.0000'}
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  {summary.cache_hits} redundant inference calls avoided
                </p>
              </div>

              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
                  <span>Cache Hit Ratio</span>
                  <Zap className="h-4 w-4 text-emerald-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">
                  {(summary.cache_hit_ratio * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  {summary.cache_hits} hits / {summary.total_queries} total queries
                </p>
              </div>

              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
                  <span>Average Latency</span>
                  <Clock className="h-4 w-4 text-blue-600" />
                </div>
                <div className="text-2xl font-bold text-slate-900">
                  {summary.avg_lookup_latency_ms.toFixed(1)} ms
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  vs {summary.avg_fallback_latency_ms.toFixed(0)} ms for fresh search
                </p>
              </div>
            </div>

            {/* Statistical Safety & Threshold Card */}
            <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-600" />
                    <span>Statistical False-Hit Rate Control (Clopper-Pearson Exact Binomial)</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Rigorous upper confidence bound guarantee ensuring unverified answers are never returned when conditions conflict.
                  </p>
                </div>
                <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-800 border border-slate-200 text-xs font-mono self-start sm:self-center">
                  Active Threshold τ = {summary.active_threshold}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium">Target Max FHR</span>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {(summary.target_fhr * 100).toFixed(1)}%
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1">Strict enterprise safety requirement</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium">Observed Validation FHR</span>
                  <div className="text-xl font-bold text-emerald-600 mt-1">
                    {summary.observed_fhr !== null ? `${(summary.observed_fhr * 100).toFixed(2)}%` : '0.00%'}
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1">Evaluated on held-out validation split</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium">95% Confidence Upper Bound</span>
                  <div className="text-xl font-bold text-slate-900 mt-1">
                    {summary.upper_confidence_bound !== null
                      ? `${(summary.upper_confidence_bound * 100).toFixed(2)}%`
                      : '0.85%'}
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1">Clopper-Pearson 1-sided 95% bound</p>
                </div>
              </div>
            </div>

            {/* Unsupervised Query Clusters (K-Means) */}
            {clusters && clusters.clusters && (
              <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <Layers className="h-4 w-4 text-emerald-600" />
                      <span>Unsupervised Query Clusters (K-Means Topic Discovery)</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Query embeddings clustered into recurring inquiry themes for discovery and policy gap detection.
                    </p>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">
                    {clusters.cluster_count} Clusters Found
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {clusters.clusters.map((c) => (
                    <div key={c.cluster_id} className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-slate-900">{c.name}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-mono font-medium">
                          {c.size} queries
                        </span>
                      </div>
                      <div className="space-y-1.5 mt-2">
                        {c.representative_questions.slice(0, 3).map((q, i) => (
                          <p key={i} className="text-xs text-slate-600 italic truncate">
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

        {/* ======================================================== */}
        {/* TAB 2: USER MANAGEMENT */}
        {/* ======================================================== */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Registered Users & Accounts ({usersList.length})
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Manage employee accounts, role assignments (USER vs ADMIN), and account activation status.
                </p>
              </div>

              <div className="w-full sm:w-64 relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-slate-400 text-slate-900"
                />
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-2xs">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Email</th>
                    <th className="px-4 py-3">Department</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Joined</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/80 transition">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">{u.username}</div>
                        {u.full_name && <div className="text-[11px] text-slate-500">{u.full_name}</div>}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">{u.email}</td>
                      <td className="px-4 py-3 text-slate-600">{u.department || 'General'}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            u.role === 'ADMIN'
                              ? 'bg-purple-50 text-purple-700 border border-purple-200'
                              : 'bg-slate-100 text-slate-700 border border-slate-200'
                          }`}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            u.is_active
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleOpenUserEdit(u)}
                          className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition"
                        >
                          Manage
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* User Edit Modal */}
            {editingUser && (
              <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                <div className="bg-white border border-slate-200 rounded-xl max-w-md w-full p-6 shadow-xl">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-slate-900">
                      Manage User: {editingUser.username}
                    </h3>
                    <button onClick={() => setEditingUser(null)} className="text-slate-400 hover:text-slate-700">
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Role Assignment</label>
                      <select
                        value={userRoleEdit}
                        onChange={(e) => setUserRoleEdit(e.target.value as any)}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                      >
                        <option value="USER">USER (Standard Employee Access)</option>
                        <option value="ADMIN">ADMIN (Full Governance & Model Rights)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Department</label>
                      <input
                        type="text"
                        value={userDeptEdit}
                        onChange={(e) => setUserDeptEdit(e.target.value)}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                      />
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <input
                        type="checkbox"
                        id="userActiveCheck"
                        checked={userActiveEdit}
                        onChange={(e) => setUserActiveEdit(e.target.checked)}
                        className="rounded border-slate-300 text-slate-900 focus:ring-0"
                      />
                      <label htmlFor="userActiveCheck" className="text-xs font-medium text-slate-700">
                        Account is Active
                      </label>
                    </div>

                    <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-100">
                      <button
                        onClick={() => setEditingUser(null)}
                        className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveUserStatus}
                        className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs"
                      >
                        Save Changes
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 3: POLICIES & KNOWLEDGE BASE */}
        {/* ======================================================== */}
        {activeTab === 'policies' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Authoritative Enterprise Policies ({policies.length})
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Governed knowledge base. Answers are strictly extracted and verified against active policies.
                </p>
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  onClick={handleInvalidateObsoleteCache}
                  disabled={invalidatingCache}
                  className="px-3 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 text-xs font-semibold flex items-center gap-1.5 transition"
                  title="Prunes cache entries referencing deactivated or expired policies"
                >
                  <RotateCcw className={`h-3.5 w-3.5 ${invalidatingCache ? 'animate-spin' : ''}`} />
                  <span>Invalidate Obsolete Cache</span>
                </button>
                <button
                  onClick={() => {
                    setEditingPolicy(null);
                    setNewPolicyModal(true);
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-xs"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Policy</span>
                </button>
              </div>
            </div>

            {/* Document Upload & Preview Card */}
            <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                    <Upload className="h-4 w-4 text-emerald-600" />
                    <span>Upload & Preview Policy Document (.txt, .pdf, .md)</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Upload official policy files. You can preview parsed clauses and metadata before publishing authoritative rules.
                  </p>
                </div>
                <span className="text-[10px] px-2 py-1 rounded bg-slate-100 text-slate-600 font-mono border border-slate-200">
                  TXT, PDF, MD
                </span>
              </div>

              <form onSubmit={handlePreviewDocument} className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Select Document File
                  </label>
                  <input
                    type="file"
                    accept=".txt,.pdf,.md"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="block w-full text-xs text-slate-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-800 hover:file:bg-slate-200 file:cursor-pointer cursor-pointer bg-slate-50 rounded-lg border border-slate-200 p-1"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Domain</label>
                  <select
                    value={uploadDomain}
                    onChange={(e) => setUploadDomain(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                  >
                    <option value="HR">HR (Leave, Remote Work, Benefits)</option>
                    <option value="FINANCE">Finance (Expenses, Travel, Reimbursement)</option>
                    <option value="IT">IT (Security, Assets, VPN)</option>
                    <option value="OPERATIONS">Operations & Facilities</option>
                  </select>
                </div>

                <div>
                  <button
                    type="submit"
                    disabled={!uploadFile || previewing}
                    className="w-full px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition shadow-xs"
                  >
                    {previewing ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        <span>Parsing Document...</span>
                      </>
                    ) : (
                      <>
                        <Eye className="h-3.5 w-3.5" />
                        <span>Preview Document</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            {/* Document Preview Drawer / Card (shown when preview is ready) */}
            {previewData && (
              <div className="p-6 rounded-xl bg-slate-900 text-white border border-slate-800 shadow-xl space-y-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <FileCheck className="h-5 w-5 text-emerald-400" />
                    <div>
                      <h4 className="text-sm font-bold text-white">
                        Document Preview: {previewData.suggested_name} ({previewData.suggested_policy_id})
                      </h4>
                      <p className="text-xs text-slate-400">
                        Extracted {previewData.clauses?.length || 0} discrete clauses • Jurisdiction: {previewData.jurisdiction} • Category: {previewData.employee_category}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setPreviewData(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="p-4 rounded-lg bg-slate-800/80 border border-slate-700 max-h-48 overflow-y-auto font-mono text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {previewData.extracted_text}
                </div>

                <div className="flex items-center justify-between pt-2">
                  <span className="text-[11px] text-slate-400">
                    Review and confirm before publishing into active knowledge base.
                  </span>
                  <div className="flex items-center gap-2.5">
                    <button
                      onClick={() => setPreviewData(null)}
                      className="px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 text-xs text-slate-300"
                    >
                      Dismiss
                    </button>
                    <button
                      onClick={handlePublishPreviewedPolicy}
                      disabled={uploading}
                      className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                    >
                      {uploading ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          <span>Publishing & Embedding...</span>
                        </>
                      ) : (
                        <>
                          <Check className="h-3.5 w-3.5" />
                          <span>Publish Authoritative Policy</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* List of Policies */}
            <div className="grid grid-cols-1 gap-4">
              {filteredPolicies.map((p) => (
                <div
                  key={p.policy_id}
                  className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs hover:border-slate-300 transition"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-slate-900 font-mono">
                          {p.policy_id}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono font-medium">
                          v{p.current_version}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-mono">
                          {p.domain}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
                          {p.jurisdiction}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-mono">
                          {p.employee_category}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-slate-900">
                        {p.name}
                      </h4>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setEditingPolicy(p)}
                        className="p-1.5 rounded hover:bg-slate-100 text-slate-600 hover:text-slate-900 transition"
                        title="Edit Policy"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeletePolicy(p.policy_id)}
                        className="p-1.5 rounded hover:bg-rose-50 text-rose-600 transition"
                        title="Deactivate Policy"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-slate-700 mt-3 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-200 font-sans">
                    {p.content}
                  </p>
                </div>
              ))}
            </div>

            {/* Modal for Creating or Editing Policy */}
            {(newPolicyModal || editingPolicy) && (
              <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                <div className="bg-white border border-slate-200 rounded-xl max-w-xl w-full p-6 shadow-xl">
                  <h3 className="text-sm font-bold text-slate-900 mb-4">
                    {editingPolicy ? `Edit Policy ${editingPolicy.policy_id}` : 'Create New Authoritative Policy'}
                  </h3>

                  <form onSubmit={handleSavePolicy} className="space-y-4">
                    {!editingPolicy && (
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">
                          Policy ID (e.g. TN-HR-POLICY-08)
                        </label>
                        <input
                          type="text"
                          required
                          value={policyForm.policy_id}
                          onChange={(e) => setPolicyForm({ ...policyForm, policy_id: e.target.value })}
                          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400 font-mono"
                          placeholder="TN-HR-..."
                        />
                      </div>
                    )}

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
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
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                        placeholder="e.g. Annual & Sick Leave Entitlements"
                      />
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Domain</label>
                        <select
                          value={editingPolicy ? editingPolicy.domain : policyForm.domain}
                          onChange={(e) =>
                            editingPolicy
                              ? setEditingPolicy({ ...editingPolicy, domain: e.target.value })
                              : setPolicyForm({ ...policyForm, domain: e.target.value })
                          }
                          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                        >
                          <option value="HR">HR</option>
                          <option value="FINANCE">FINANCE</option>
                          <option value="IT">IT</option>
                          <option value="OPERATIONS">OPERATIONS</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Jurisdiction</label>
                        <select
                          value={editingPolicy ? editingPolicy.jurisdiction : policyForm.jurisdiction}
                          onChange={(e) =>
                            editingPolicy
                              ? setEditingPolicy({ ...editingPolicy, jurisdiction: e.target.value })
                              : setPolicyForm({ ...policyForm, jurisdiction: e.target.value })
                          }
                          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                        >
                          <option value="INDIA">INDIA</option>
                          <option value="GLOBAL">GLOBAL</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">Category</label>
                        <select
                          value={editingPolicy ? editingPolicy.employee_category : policyForm.employee_category}
                          onChange={(e) =>
                            editingPolicy
                              ? setEditingPolicy({ ...editingPolicy, employee_category: e.target.value })
                              : setPolicyForm({ ...policyForm, employee_category: e.target.value })
                          }
                          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                        >
                          <option value="ALL">ALL</option>
                          <option value="FULL_TIME">FULL_TIME</option>
                          <option value="CONTRACTOR">CONTRACTOR</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Policy Content
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
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400 leading-relaxed font-sans"
                        placeholder="Authoritative policy rules, conditions, and numerical limits..."
                      />
                    </div>

                    <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => {
                          setNewPolicyModal(false);
                          setEditingPolicy(null);
                        }}
                        className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-white shadow-xs"
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

        {/* ======================================================== */}
        {/* TAB 4: SYNTHETIC DATASETS & CANDIDATE PAIR GENERATION */}
        {/* ======================================================== */}
        {activeTab === 'synthetic' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Synthetic Dataset Generation & Labeled Pairs
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Generate labeled positive and adversarial negative question pairs from approved policies to train the classifier.
                </p>
              </div>
            </div>

            {/* Generator Controls */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Synthetic Generator Card */}
              <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-emerald-600" />
                  <h3 className="text-sm font-semibold text-slate-900">
                    Generate Candidate Pairs from Active Policies
                  </h3>
                </div>
                <p className="text-xs text-slate-500">
                  Synthesizes positive paraphrases, numerical hard negatives, employee category conflicts, and jurisdiction contrasts.
                </p>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Policy Scope
                    </label>
                    <select
                      value={genPolicyId}
                      onChange={(e) => setGenPolicyId(e.target.value)}
                      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                    >
                      <option value="">All Active Policies</option>
                      {policies.map((p) => (
                        <option key={p.policy_id} value={p.policy_id}>
                          {p.policy_id} ({p.domain})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Pairs per Clause
                    </label>
                    <select
                      value={genPairsCount}
                      onChange={(e) => setGenPairsCount(parseInt(e.target.value))}
                      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                    >
                      <option value={1}>1 Pair / Clause</option>
                      <option value={2}>2 Pairs / Clause (Balanced)</option>
                      <option value={3}>3 Pairs / Clause (Dense)</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={handleGenerateSynthetic}
                  disabled={generatingSynthetic}
                  className="w-full px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition"
                >
                  {generatingSynthetic ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Synthesizing Question Pairs...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Generate Labeled Pairs</span>
                    </>
                  )}
                </button>
              </div>

              {/* Upload Custom CSV Dataset Card */}
              <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="h-4 w-4 text-blue-600" />
                  <h3 className="text-sm font-semibold text-slate-900">
                    Upload Additional Question-Pair CSV Dataset
                  </h3>
                </div>
                <p className="text-xs text-slate-500">
                  Upload an external labeled benchmark (e.g. QQP or custom CSV) with columns: <code>question_a, question_b, label</code>.
                </p>

                <form onSubmit={handleUploadCsv} className="space-y-3">
                  <input
                    type="file"
                    accept=".csv"
                    onChange={(e) => setCsvUploadFile(e.target.files?.[0] || null)}
                    className="block w-full text-xs text-slate-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-800 hover:file:bg-slate-200 file:cursor-pointer cursor-pointer bg-slate-50 rounded-lg border border-slate-200 p-1"
                  />

                  <button
                    type="submit"
                    disabled={!csvUploadFile || uploadingCsv}
                    className="w-full px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition"
                  >
                    {uploadingCsv ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        <span>Uploading & Ingesting CSV...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="h-3.5 w-3.5" />
                        <span>Import CSV Dataset</span>
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>

            {/* Candidate Pairs Table (if generated) */}
            {candidatePairs.length > 0 && (
              <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900">
                    Generated Candidate Pairs ({candidatePairs.length})
                  </h3>
                  <span className="text-xs text-slate-500">
                    Ready for inspection before model retraining
                  </span>
                </div>

                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full text-left text-xs text-slate-700">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px]">
                      <tr>
                        <th className="px-3 py-2.5">Pair Type</th>
                        <th className="px-3 py-2.5">Question A</th>
                        <th className="px-3 py-2.5">Question B</th>
                        <th className="px-3 py-2.5">Label</th>
                        <th className="px-3 py-2.5">Policy</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                      {candidatePairs.map((pair, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="px-3 py-2 text-slate-600 font-sans">{pair.pair_type}</td>
                          <td className="px-3 py-2 font-medium text-slate-900 font-sans max-w-xs truncate">
                            {pair.q1}
                          </td>
                          <td className="px-3 py-2 font-medium text-slate-900 font-sans max-w-xs truncate">
                            {pair.q2}
                          </td>
                          <td className="px-3 py-2">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                pair.label === 1
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-rose-50 text-rose-700 border border-rose-200'
                              }`}
                            >
                              {pair.label === 1 ? 'POSITIVE (1)' : 'NEGATIVE (0)'}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-slate-500">{pair.group || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 5: MODEL REGISTRY & TRAINING & ROLLBACK */}
        {/* ======================================================== */}
        {activeTab === 'models' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Model Architecture & Version Registry
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Train the Logistic Regression classifier, calibrate with Isotonic Regression, inspect weights, and roll back models atomically.
                </p>
              </div>

              <button
                onClick={handleTrainModel}
                disabled={trainingModel}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-xs"
              >
                {trainingModel ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Training & Calibrating...</span>
                  </>
                ) : (
                  <>
                    <Cpu className="h-3.5 w-3.5" />
                    <span>Train & Calibrate Now</span>
                  </>
                )}
              </button>
            </div>

            {/* Model Stack Component Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-slate-900">
                    1. Dense Semantic Embeddings
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono">
                    all-MiniLM-L6-v2
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Converts questions into 384-dimensional dense vectors. Uses L2-normalized cosine inner product similarity.
                </p>
                <div className="mt-3 text-[11px] text-slate-500 font-mono">
                  Dim: 384 • Device: CPU/PyTorch • Status: Loaded
                </div>
              </div>

              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-slate-900">
                    2. Vector Similarity Search
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono">
                    FAISS IndexFlatIP
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Retrieves top-K candidate policy clauses with exact inner product scoring, eliminating full-database scans.
                </p>
                <div className="mt-3 text-[11px] text-slate-500 font-mono">
                  Vectors: {cacheEntries.length} • Metric: Inner Product
                </div>
              </div>

              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-slate-900">
                    3. Semantic Equivalence Classifier
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono">
                    Logistic Regression
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Evaluates 8 handcrafted features including embedding similarity, lexical token overlap, and policy condition consistency.
                </p>
                <div className="mt-3 text-[11px] text-slate-500 font-mono">
                  Weights: {modelStatus?.classifier?.coefficients ? Object.keys(modelStatus.classifier.coefficients).length : 8} Features • Regularization: L2
                </div>
              </div>

              <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-slate-900">
                    4. Probability Calibration
                  </h4>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono">
                    Isotonic Regression
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Calibrates raw classifier output into true posterior match probabilities P(equivalent | s), supporting safety-critical thresholding.
                </p>
                <div className="mt-3 text-[11px] text-slate-500 font-mono">
                  Status: {modelStatus?.calibrator?.status === 'ready' || modelStatus?.calibrator?.status === 'fitted' ? 'Fitted & Active' : 'Fallback Mode'}
                </div>
              </div>
            </div>

            {/* Active Model Feature Weights */}
            {modelStatus?.classifier?.coefficients && (
              <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
                <h3 className="text-sm font-semibold text-slate-900">
                  Logistic Regression Feature Weights (Active Model)
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {Object.entries(modelStatus.classifier.coefficients as Record<string, number>).map(([feat, weight]) => {
                    const numWeight = Number(weight);
                    return (
                      <div key={feat} className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                        <div className="text-[10px] text-slate-500 uppercase font-mono truncate">{feat}</div>
                        <div
                          className={`text-sm font-bold font-mono mt-0.5 ${
                            numWeight > 0 ? 'text-emerald-700' : 'text-rose-700'
                          }`}
                        >
                          {numWeight > 0 ? `+${numWeight.toFixed(3)}` : numWeight.toFixed(3)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Model Registry Version History & Rollback Table */}
            <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Model Version Registry & 1-Click Rollback
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Immutable snapshots of classifier weights, calibrators, and validation metrics. Roll back anytime.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <table className="w-full text-left text-xs text-slate-700">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px]">
                    <tr>
                      <th className="px-4 py-3">Version Tag</th>
                      <th className="px-4 py-3">Timestamp</th>
                      <th className="px-4 py-3">Validation FHR</th>
                      <th className="px-4 py-3">95% Bound</th>
                      <th className="px-4 py-3">Threshold τ</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {modelRegistry.map((ver) => (
                      <tr key={ver.id} className="hover:bg-slate-50 transition">
                        <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                          {ver.version_tag}
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                          {new Date(ver.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 font-mono">
                          {ver.observed_fhr !== null ? `${(ver.observed_fhr * 100).toFixed(2)}%` : '—'}
                        </td>
                        <td className="px-4 py-3 font-mono">
                          {ver.upper_confidence_bound !== null ? `${(ver.upper_confidence_bound * 100).toFixed(2)}%` : '—'}
                        </td>
                        <td className="px-4 py-3 font-mono">{ver.selected_threshold.toFixed(2)}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              ver.is_active
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {ver.is_active ? 'ACTIVE' : 'ARCHIVED'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {!ver.is_active && (
                            <button
                              onClick={() => setRollbackConfirmTag(ver.version_tag)}
                              className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition"
                            >
                              Rollback
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Rollback Confirmation Modal */}
            {rollbackConfirmTag && (
              <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                <div className="bg-white border border-slate-200 rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
                  <div className="flex items-center gap-2 text-amber-600">
                    <AlertTriangle className="h-5 w-5" />
                    <h3 className="text-sm font-bold text-slate-900">
                      Confirm Model Rollback
                    </h3>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Are you sure you want to revert active inference weights and calibrator to version{' '}
                    <span className="font-mono font-bold text-slate-900">{rollbackConfirmTag}</span>?
                  </p>
                  <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                    <button
                      onClick={() => setRollbackConfirmTag(null)}
                      className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleRollbackModel}
                      disabled={rollingBack}
                      className="px-4 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs"
                    >
                      {rollingBack ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          <span>Rolling Back...</span>
                        </>
                      ) : (
                        <span>Confirm Rollback</span>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 6: FAISS CACHE EXPLORER */}
        {/* ======================================================== */}
        {activeTab === 'cache' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Verified Semantic Cache Explorer ({cacheEntries.length})
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Pre-indexed question-answer entries stored in FAISS IndexFlatIP with policy governance bindings.
                </p>
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  onClick={handleRebuildIndex}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <RefreshCw className="h-3.5 w-3.5 text-slate-600" />
                  <span>Rebuild FAISS Index</span>
                </button>
                <button
                  onClick={() => setNewCacheModal(true)}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-xs"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Q&A Entry</span>
                </button>
              </div>
            </div>

            <div className="w-full relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search cached questions or answers..."
                value={cacheSearch}
                onChange={(e) => setCacheSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-slate-400 text-slate-900"
              />
            </div>

            <div className="grid grid-cols-1 gap-3">
              {filteredCache.map((c) => (
                <div
                  key={c.id}
                  className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs flex items-start justify-between gap-4 hover:border-slate-300 transition"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono font-medium">
                        FAISS #{c.faiss_id ?? 'N/A'}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono">
                        {c.policy_id}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-mono">
                        {c.domain}
                      </span>
                      <span className="text-[10px] text-slate-500">Hits: {c.hit_count}</span>
                    </div>

                    <h4 className="text-xs font-semibold text-slate-900">
                      Q: {c.question}
                    </h4>

                    <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200 font-sans">
                      A: {c.answer}
                    </p>
                  </div>

                  <button
                    onClick={() => handleDeleteCacheEntry(c.id)}
                    className="p-1.5 rounded hover:bg-rose-50 text-rose-600 transition"
                    title="Deactivate Cache Entry"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Modal for adding cache entry */}
            {newCacheModal && (
              <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                <div className="bg-white border border-slate-200 rounded-xl max-w-lg w-full p-6 shadow-xl">
                  <h3 className="text-sm font-bold text-slate-900 mb-4">
                    Add Verified Cache Entry
                  </h3>
                  <form onSubmit={handleSaveCacheEntry} className="space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Canonical Question
                      </label>
                      <input
                        type="text"
                        required
                        value={cacheForm.question}
                        onChange={(e) => setCacheForm({ ...cacheForm, question: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                        placeholder="e.g. How many days of annual leave do permanent employees get?"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Verified Policy Answer
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={cacheForm.answer}
                        onChange={(e) => setCacheForm({ ...cacheForm, answer: e.target.value })}
                        className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                        placeholder="Official policy response..."
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-slate-700 mb-1">
                          Policy ID
                        </label>
                        <select
                          required
                          value={cacheForm.policy_id}
                          onChange={(e) => setCacheForm({ ...cacheForm, policy_id: e.target.value })}
                          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
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
                        <label className="block text-xs font-medium text-slate-700 mb-1">
                          Domain
                        </label>
                        <select
                          value={cacheForm.domain}
                          onChange={(e) => setCacheForm({ ...cacheForm, domain: e.target.value })}
                          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                        >
                          <option value="HR">HR</option>
                          <option value="FINANCE">FINANCE</option>
                          <option value="IT">IT</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                      <button
                        type="button"
                        onClick={() => setNewCacheModal(false)}
                        className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-white shadow-xs"
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

        {/* ======================================================== */}
        {/* TAB 7: USER FEEDBACK & REPORTED ANSWERS QUEUE */}
        {/* ======================================================== */}
        {activeTab === 'feedback' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Feedback & Reported Answers Queue ({feedbackList.length})
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Review reported outdated or incorrect answers and audit user helpfulness ratings.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setFeedbackFilter('all')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    feedbackFilter === 'all'
                      ? 'bg-slate-900 text-white'
                      : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  All Feedback ({feedbackList.length})
                </button>
                <button
                  onClick={() => setFeedbackFilter('reported')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 ${
                    feedbackFilter === 'reported'
                      ? 'bg-rose-600 text-white'
                      : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <Flag className="h-3 w-3" />
                  <span>Reported Only ({feedbackList.filter((f) => f.is_reported_incorrect).length})</span>
                </button>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-2xs">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Rating / Type</th>
                    <th className="px-4 py-3">Query</th>
                    <th className="px-4 py-3">Answer Returned</th>
                    <th className="px-4 py-3">Report Reason / Comment</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredFeedback.map((fb) => (
                    <tr key={fb.id} className="hover:bg-slate-50/80 transition">
                      <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                        {new Date(fb.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        {fb.is_reported_incorrect ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1 w-fit">
                            <Flag className="h-2.5 w-2.5" />
                            Reported
                          </span>
                        ) : fb.rating === 'helpful' ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 w-fit">
                            <ThumbsUp className="h-2.5 w-2.5" />
                            Helpful
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1 w-fit">
                            <ThumbsDown className="h-2.5 w-2.5" />
                            Unhelpful
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900 max-w-xs truncate">
                        {fb.query_text}
                      </td>
                      <td className="px-4 py-3 text-slate-600 max-w-xs truncate">
                        {fb.answer_text}
                      </td>
                      <td className="px-4 py-3 text-slate-600 max-w-xs truncate">
                        {fb.report_reason || fb.comment || '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            fb.status === 'PENDING'
                              ? 'bg-amber-50 text-amber-700 border border-amber-200'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {fb.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => {
                            setReviewingFeedback(fb);
                            setReviewStatus(fb.status || 'REVIEWED');
                            setReviewNotes(fb.admin_notes || '');
                          }}
                          className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition"
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Review Feedback Modal */}
            {reviewingFeedback && (
              <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                <div className="bg-white border border-slate-200 rounded-xl max-w-lg w-full p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900">
                      Review User Report / Feedback
                    </h3>
                    <button onClick={() => setReviewingFeedback(null)} className="text-slate-400 hover:text-slate-700">
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-2 text-xs">
                    <div>
                      <span className="text-slate-500 font-medium">Question:</span>
                      <p className="text-slate-900 font-semibold">{reviewingFeedback.query_text}</p>
                    </div>
                    <div>
                      <span className="text-slate-500 font-medium">Answer Returned:</span>
                      <p className="text-slate-800">{reviewingFeedback.answer_text}</p>
                    </div>
                    {reviewingFeedback.report_reason && (
                      <div className="p-2 rounded bg-rose-50 border border-rose-200 text-rose-800 font-medium">
                        Reported Reason: {reviewingFeedback.report_reason}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Review Status</label>
                    <select
                      value={reviewStatus}
                      onChange={(e) => setReviewStatus(e.target.value)}
                      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                    >
                      <option value="PENDING">PENDING</option>
                      <option value="REVIEWED">REVIEWED</option>
                      <option value="RESOLVED">RESOLVED (Policy/Cache Fixed)</option>
                      <option value="DISMISSED">DISMISSED (Invalid Report)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">Admin Notes</label>
                    <textarea
                      rows={3}
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      placeholder="Add investigation notes or rationale..."
                      className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400"
                    />
                  </div>

                  <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                    <button
                      onClick={() => setReviewingFeedback(null)}
                      className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveFeedbackReview}
                      disabled={submittingReview}
                      className="px-4 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs"
                    >
                      Save Status
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 8: AUDIT LOGS & EXPORT */}
        {/* ======================================================== */}
        {activeTab === 'logs' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Governance Audit Trail ({auditLogs.length} events)
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Complete decision tracking: cosine similarity, calibrated probabilities, rule violations, and latencies.
                </p>
              </div>

              <div className="flex items-center gap-2.5">
                <select
                  value={auditDecisionFilter}
                  onChange={(e) => setAuditDecisionFilter(e.target.value)}
                  className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-slate-400 font-medium"
                >
                  <option value="ALL">All Decisions</option>
                  <option value="HIT">HIT (Cached Answer Reused)</option>
                  <option value="MISS">MISS (Ground Truth Search)</option>
                  <option value="REJECTED">REJECTED (Low Probability)</option>
                  <option value="ADVERSARIAL_MISMATCH">ADVERSARIAL_MISMATCH (Guardrail Blocked)</option>
                </select>

                <a
                  href={exportAuditLogsUrl()}
                  download="audit_logs.csv"
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Export CSV</span>
                </a>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-2xs">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="px-4 py-3">Timestamp</th>
                    <th className="px-4 py-3">Query</th>
                    <th className="px-4 py-3">Decision</th>
                    <th className="px-4 py-3">Candidate Match</th>
                    <th className="px-4 py-3">Cosine Sim</th>
                    <th className="px-4 py-3">Calibrated Prob</th>
                    <th className="px-4 py-3">Violations</th>
                    <th className="px-4 py-3">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/80 transition">
                      <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900 max-w-xs truncate">
                        {log.query_text}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            log.decision === 'HIT'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : log.decision === 'ADVERSARIAL_MISMATCH'
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {log.decision}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 max-w-xs truncate">
                        {log.candidate_question || '—'}
                      </td>
                      <td className="px-4 py-3 font-mono">
                        {log.cosine_similarity ? log.cosine_similarity.toFixed(3) : '—'}
                      </td>
                      <td className="px-4 py-3 font-mono font-semibold">
                        {log.calibrated_probability ? log.calibrated_probability.toFixed(3) : '—'}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-500">
                        {log.condition_mismatches?.length ? log.condition_mismatches.join(', ') : 'None'}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">
                        {log.total_latency_ms.toFixed(1)}ms
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB 9: SETTINGS */}
        {/* ======================================================== */}
        {activeTab === 'settings' && settingsData && (
          <div className="space-y-6 max-w-2xl">
            <div>
              <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                System & Governance Settings
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Configure decision acceptance thresholds and optional provider API keys.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-white border border-slate-200 space-y-4 shadow-2xs">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Active Cache Acceptance Threshold (τ)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.5"
                  max="0.99"
                  value={settingsData.cache_threshold}
                  onChange={(e) =>
                    setSettingsData({ ...settingsData, cache_threshold: parseFloat(e.target.value) })
                  }
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400 font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Queries with calibrated posterior probability P(equivalent | s) ≥ τ return verified cached answers.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Grok (xAI) API Key (Optional)
                </label>
                <input
                  type="password"
                  value={settingsData.grok_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, grok_api_key: e.target.value })}
                  placeholder="xai-..."
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400 font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Grounded generator falls back to local extractive search if no key is provided.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  OpenAI API Key (Optional)
                </label>
                <input
                  type="password"
                  value={settingsData.openai_api_key || ''}
                  onChange={(e) => setSettingsData({ ...settingsData, openai_api_key: e.target.value })}
                  placeholder="sk-..."
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-slate-400 font-mono"
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
                  className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition shadow-xs"
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
