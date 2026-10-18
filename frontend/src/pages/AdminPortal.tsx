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
  FileSpreadsheet,
  Leaf,
  HelpCircle,
  FileQuestion,
  MessageSquareQuote,
  Droplets,
  TrendingUp,
  Activity
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  AreaChart,
  Area,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend
} from 'recharts';
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
  exportAuditLogsUrl,
  resetCacheColdStart,
  selectActiveModel,
  getActiveModelInfo,
  getInsufficientDataQuestions,
  updateInsufficientDataQuestion,
  reEvaluateInsufficientDataQuestions,
  getSustainabilityMetrics
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
  CandidatePair,
  InsufficientDataQuestion,
  InsufficientDataQuestionListResponse,
  SustainabilityData
} from '../types';
import { useAuth } from '../context/AuthContext';

export const AdminPortal: React.FC = () => {
  const { user: currentUser } = useAuth();

  const [activeTab, setActiveTab] = useState<
    'analytics' | 'users' | 'policies' | 'insufficient' | 'cache'
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

  // Sustainability Data State
  const [sustainabilityData, setSustainabilityData] = useState<SustainabilityData | null>(null);
  const [sustainabilityChartMetric, setSustainabilityChartMetric] = useState<'hit_rate' | 'cost' | 'energy' | 'tokens'>('hit_rate');

  // Insufficient Data Questions (Policy Gaps) State
  const [insufficientData, setInsufficientData] = useState<InsufficientDataQuestionListResponse | null>(null);
  const [insufficientStatusFilter, setInsufficientStatusFilter] = useState<'ALL' | 'PENDING' | 'REVIEWED' | 'RESOLVED'>('ALL');
  const [insufficientSearch, setInsufficientSearch] = useState('');
  const [insufficientLoading, setInsufficientLoading] = useState(false);
  const [editingGapNotes, setEditingGapNotes] = useState<{ id: string; notes: string } | null>(null);
  const [reEvaluating, setReEvaluating] = useState(false);

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

  // Active Equivalence Classifier Selection State (Syllabus Models)
  const [activeModelInfo, setActiveModelInfo] = useState<any>(null);
  const [switchingModel, setSwitchingModel] = useState(false);

  // Cold Start Cache Reset State
  const [resettingCache, setResettingCache] = useState(false);
  const [showColdStartModal, setShowColdStartModal] = useState(false);

  const showBanner = (text: string, type: 'success' | 'error' = 'success') => {
    setActionMessage({ text, type });
    setTimeout(() => setActionMessage(null), 6000);
  };

  const handleSelectModel = async (modelName: string) => {
    setSwitchingModel(true);
    try {
      const res = await selectActiveModel(modelName);
      showBanner(res.message || `Switched active classifier to ${modelName.toUpperCase()}`, 'success');
      const updated = await getActiveModelInfo().catch(() => null);
      if (updated) setActiveModelInfo(updated);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to switch classifier model', 'error');
    } finally {
      setSwitchingModel(false);
    }
  };

  const handleColdStartReset = async () => {
    setResettingCache(true);
    try {
      const res = await resetCacheColdStart();
      showBanner(res.message || 'Cold start reset: Cache emptied and FAISS vectors reset to 0.', 'success');
      setShowColdStartModal(false);
      await loadData();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to execute cold start reset', 'error');
    } finally {
      setResettingCache(false);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [sum, pols, cEntries, logs, mStatus, clust, sett, uList, mReg, fbList, activeModelData, gapData, sustData] = await Promise.all([
        getDashboardSummary().catch(() => null),
        getPolicies().catch(() => []),
        getCacheEntries().catch(() => []),
        getAuditLogs(50).catch(() => []),
        getModelStatus().catch(() => null),
        getClusterAnalytics(3).catch(() => null),
        getSettings().catch(() => null),
        getAllUsers().catch(() => []),
        getModelRegistry().catch(() => []),
        getAdminFeedback().catch(() => []),
        getActiveModelInfo().catch(() => null),
        getInsufficientDataQuestions().catch(() => null),
        getSustainabilityMetrics().catch(() => null)
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
      if (activeModelData) setActiveModelInfo(activeModelData);
      if (gapData) setInsufficientData(gapData);
      if (sustData) setSustainabilityData(sustData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchInsufficientQuestions = async (statusOverride?: string, searchOverride?: string) => {
    setInsufficientLoading(true);
    try {
      const statusParam = (statusOverride !== undefined ? statusOverride : insufficientStatusFilter) === 'ALL'
        ? undefined
        : (statusOverride !== undefined ? statusOverride : insufficientStatusFilter);
      const searchParam = (searchOverride !== undefined ? searchOverride : insufficientSearch).trim() || undefined;
      const data = await getInsufficientDataQuestions({ status: statusParam, search: searchParam });
      setInsufficientData(data);
    } catch (err: any) {
      console.error("Error loading insufficient data questions:", err);
    } finally {
      setInsufficientLoading(false);
    }
  };

  const handleUpdateGapStatus = async (gapId: string, newStatus: 'PENDING' | 'REVIEWED' | 'RESOLVED') => {
    try {
      await updateInsufficientDataQuestion(gapId, { status: newStatus });
      showBanner(`Question marked as ${newStatus}.`, 'success');
      fetchInsufficientQuestions();
      const sum = await getDashboardSummary().catch(() => null);
      if (sum) setSummary(sum);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to update status', 'error');
    }
  };

  const handleSaveGapNotes = async (gapId: string, notes: string) => {
    try {
      await updateInsufficientDataQuestion(gapId, { admin_notes: notes });
      showBanner('Admin notes saved successfully.', 'success');
      setEditingGapNotes(null);
      fetchInsufficientQuestions();
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Failed to save notes', 'error');
    }
  };

  const handleBatchReEvaluateGaps = async () => {
    setReEvaluating(true);
    try {
      const res = await reEvaluateInsufficientDataQuestions();
      showBanner(res.message, 'success');
      await Promise.all([
        fetchInsufficientQuestions(),
        loadData()
      ]);
    } catch (err: any) {
      showBanner(err?.response?.data?.detail || 'Re-evaluation failed.', 'error');
    } finally {
      setReEvaluating(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (activeTab === 'insufficient') {
      fetchInsufficientQuestions();
    }
  }, [activeTab, insufficientStatusFilter]);

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
            <span>Enterprise Cache Engine: Active</span>
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
          { key: 'analytics', label: 'Analytics & Sustainability', icon: BarChart3 },
          { key: 'users', label: 'User Management', icon: Users, badge: usersList.length },
          { key: 'policies', label: 'Policies & Documents', icon: FileText, badge: policies.length },
          {
            key: 'insufficient',
            label: 'Insufficient Data Questions',
            icon: HelpCircle,
            badge: insufficientData?.pending_count ?? summary?.pending_insufficient_questions_count ?? 0,
            isWarning: (insufficientData?.pending_count ?? summary?.pending_insufficient_questions_count ?? 0) > 0
          },
          { key: 'cache', label: 'Cache Explorer', icon: Database, badge: cacheEntries.length }
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
                    tab.isWarning
                      ? 'bg-amber-100 text-amber-800 border border-amber-300 font-bold'
                      : tab.key === 'feedback' && tab.badge > 0
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
        {activeTab === 'analytics' && summary && (() => {
          const costWithoutCacheUSD = summary.total_queries * 0.030;
          const costWithoutCacheINR = costWithoutCacheUSD * 83.50;
          const costWithCacheUSD = (summary.cache_misses * 0.030) + (summary.cache_hits * 0.00005);
          const costWithCacheINR = costWithCacheUSD * 83.50;
          const netSavingsUSD = summary.estimated_cost_saved_usd ?? (costWithoutCacheUSD - costWithCacheUSD);
          const netSavingsINR = summary.estimated_cost_saved_inr ?? (netSavingsUSD * 83.50);
          const savingsPct = costWithoutCacheUSD > 0 ? (netSavingsUSD / costWithoutCacheUSD) * 100 : 0;

          return (
            <div className="space-y-6">
              {/* SECTION 1: CACHE HIT RATE & QUERY THROUGHPUT */}
              <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <Zap className="h-4 w-4 text-emerald-600" />
                      <span>1. Historical Cache Hit Rate & System Throughput</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Historical hit rate is computed strictly from immutable QueryAuditLog events for eligible policy questions. Deleting or invalidating cache entries never drops historical analytics.
                    </p>
                  </div>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold">
                    {(((summary.policy_cache_hit_rate ?? summary.cache_hit_ratio) || 0) * 100).toFixed(1)}% Historical Hit Rate
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[11px] text-slate-500 font-medium">Eligible Policy Inquiries</span>
                    <div className="text-2xl font-bold text-slate-900 mt-1">
                      {summary.eligible_policy_queries ?? summary.total_queries}
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">All employee policy questions</p>
                  </div>

                  <div className="p-4 rounded-lg bg-emerald-50/60 border border-emerald-200">
                    <span className="text-[11px] text-emerald-700 font-medium">Historical Cache Hits</span>
                    <div className="text-2xl font-bold text-emerald-800 mt-1">
                      {summary.total_historical_cache_hits ?? summary.cache_hits}
                    </div>
                    <p className="text-[10px] text-emerald-700 mt-1">
                      Avg latency: {summary.avg_lookup_latency_ms.toFixed(1)} ms (&lt;5ms)
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                    <span className="text-[11px] text-slate-500 font-medium">Active Cache Entries</span>
                    <div className="text-2xl font-bold text-slate-800 mt-1">
                      {summary.current_active_cache_entries ?? cacheEntries.filter(c => c.is_active).length}
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">
                      {summary.current_invalidated_cache_entries ?? cacheEntries.filter(c => !c.is_active).length} invalidated versions
                    </p>
                  </div>

                  <div className="p-4 rounded-lg bg-amber-50/60 border border-amber-200">
                    <span className="text-[11px] text-amber-800 font-medium">Policy Evidence Gaps</span>
                    <div className="text-2xl font-bold text-amber-900 mt-1">
                      {summary.insufficient_evidence_queries ?? 0}
                    </div>
                    <p className="text-[10px] text-amber-700 mt-1">
                      {summary.pending_insufficient_questions_count ?? 0} pending admin review
                    </p>
                  </div>
                </div>
              </div>

              {/* SECTION 2: COST WITH AND WITHOUT CACHE */}
              <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <Coins className="h-4 w-4 text-emerald-600" />
                      <span>2. Cost Comparison: With vs Without Semantic Cache</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Direct cost comparison between un-cached cloud inference and CacheMind governed caching.
                    </p>
                  </div>
                  {savingsPct > 0 && (
                    <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">
                      {savingsPct.toFixed(1)}% Cost Reduction
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div className="p-5 rounded-xl bg-rose-50/50 border border-rose-200">
                    <div className="flex items-center justify-between text-rose-800 text-xs font-semibold mb-1">
                      <span>Cost Without Cache</span>
                      <span className="text-[10px] uppercase font-mono">100% Model Inference</span>
                    </div>
                    <div className="text-2xl font-bold text-rose-900 mt-2">
                      ${costWithoutCacheUSD.toFixed(4)}
                    </div>
                    <div className="text-sm font-semibold text-rose-700 mt-0.5">
                      ₹{costWithoutCacheINR.toFixed(2)} INR
                    </div>
                    <p className="text-[11px] text-rose-600/90 mt-2">
                      If every inquiry ({summary.total_queries}) required a fresh model call at $0.030/query.
                    </p>
                  </div>

                  <div className="p-5 rounded-xl bg-blue-50/50 border border-blue-200">
                    <div className="flex items-center justify-between text-blue-800 text-xs font-semibold mb-1">
                      <span>Cost With CacheMind</span>
                      <span className="text-[10px] uppercase font-mono">Governed Cache Active</span>
                    </div>
                    <div className="text-2xl font-bold text-blue-900 mt-2">
                      ${costWithCacheUSD.toFixed(4)}
                    </div>
                    <div className="text-sm font-semibold text-blue-700 mt-0.5">
                      ₹{costWithCacheINR.toFixed(2)} INR
                    </div>
                    <p className="text-[11px] text-blue-600/90 mt-2">
                      Actual incurred cost: only {summary.cache_misses} misses called model; {summary.cache_hits} hits served from cache.
                    </p>
                  </div>

                  <div className="p-5 rounded-xl bg-emerald-50 border border-emerald-200">
                    <div className="flex items-center justify-between text-emerald-800 text-xs font-semibold mb-1">
                      <span>Net Enterprise Savings</span>
                      <span className="text-[10px] uppercase font-mono">Money Saved</span>
                    </div>
                    <div className="text-2xl font-bold text-emerald-900 mt-2">
                      ${netSavingsUSD.toFixed(4)}
                    </div>
                    <div className="text-sm font-semibold text-emerald-700 mt-0.5">
                      ₹{netSavingsINR.toFixed(2)} INR
                    </div>
                    <p className="text-[11px] text-emerald-700/90 mt-2">
                      Direct cash saved by avoiding {summary.cache_hits} redundant inference queries.
                    </p>
                  </div>
                </div>

                {/* Cloud Model Inference Token Footprint */}
                <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 text-[10px] uppercase font-medium">Model Calls Made</span>
                    <div className="font-bold text-slate-800 mt-0.5">{summary.grok_invocations ?? summary.cache_misses}</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 text-[10px] uppercase font-medium">Calls Avoided</span>
                    <div className="font-bold text-emerald-700 mt-0.5">{summary.cache_hits}</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 text-[10px] uppercase font-medium">Tokens Consumed</span>
                    <div className="font-bold text-slate-800 mt-0.5">{(summary.total_tokens_consumed ?? 0).toLocaleString()}</div>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 text-[10px] uppercase font-medium">Incurred Model Cost</span>
                    <div className="font-bold text-slate-800 mt-0.5">${(summary.actual_cost_usd ?? 0).toFixed(4)}</div>
                  </div>
                </div>
              </div>

              {/* SECTION 3: VISUAL SUSTAINABILITY & CACHE WARMING TRAJECTORY (CHARTS) */}
              {(() => {
                const progressionData = (sustainabilityData?.progression && sustainabilityData.progression.length > 0)
                  ? sustainabilityData.progression
                  : (() => {
                      const sorted = [...auditLogs].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
                      let cHits = 0;
                      let cMisses = 0;
                      return sorted.map((log, idx) => {
                        const isHit = log.decision === 'HIT' || log.decision === 'CACHE_HIT';
                        if (isHit) cHits++; else cMisses++;
                        return {
                          query_index: idx + 1,
                          query_text: log.query_text ? (log.query_text.length > 50 ? log.query_text.slice(0, 47) + '...' : log.query_text) : `Query #${idx + 1}`,
                          decision: log.decision,
                          is_hit: isHit,
                          cumulative_queries: idx + 1,
                          cumulative_hits: cHits,
                          cumulative_misses: cMisses,
                          hit_rate_pct: Number(((cHits / (idx + 1)) * 100).toFixed(1)),
                          cumulative_tokens_saved: cHits * 450,
                          cumulative_energy_wh_saved: Number((cHits * 0.47).toFixed(2)),
                          cumulative_co2_g_saved: Number((cHits * 2.50).toFixed(1)),
                          cumulative_cost_saved_usd: Number((cHits * 0.02995).toFixed(4)),
                          cumulative_cost_saved_inr: Number((cHits * 2.5008).toFixed(2)),
                          timestamp: log.created_at
                        };
                      });
                    })();

                const totalQ = summary.total_queries || progressionData.length || 1;
                const totalH = summary.total_historical_cache_hits ?? summary.cache_hits ?? progressionData[progressionData.length - 1]?.cumulative_hits ?? 0;
                const totalM = summary.cache_misses || Math.max(0, totalQ - totalH);
                const currentHitRatePct = totalQ > 0 ? ((totalH / totalQ) * 100).toFixed(1) : '0.0';

                const comparativeData = [
                  {
                    metric: 'Financial Cost ($)',
                    baseline: Number((totalQ * 0.0300).toFixed(2)),
                    withCache: Number(((totalM * 0.0300) + (totalH * 0.00005)).toFixed(2)),
                    saved: Number((totalH * 0.02995).toFixed(2)),
                    unit: '$',
                    reductionPct: totalQ > 0 ? ((totalH / totalQ) * 100).toFixed(1) : '0'
                  },
                  {
                    metric: 'Inference Calls',
                    baseline: totalQ,
                    withCache: totalM,
                    saved: totalH,
                    unit: 'calls',
                    reductionPct: totalQ > 0 ? ((totalH / totalQ) * 100).toFixed(1) : '0'
                  },
                  {
                    metric: 'GPU Power (Wh)',
                    baseline: Number((totalQ * 0.47).toFixed(1)),
                    withCache: Number((totalM * 0.47).toFixed(1)),
                    saved: Number((totalH * 0.47).toFixed(1)),
                    unit: 'Wh',
                    reductionPct: totalQ > 0 ? ((totalH / totalQ) * 100).toFixed(1) : '0'
                  },
                  {
                    metric: 'Carbon (g CO₂e)',
                    baseline: Number((totalQ * 2.50).toFixed(1)),
                    withCache: Number((totalM * 2.50).toFixed(1)),
                    saved: Number((totalH * 2.50).toFixed(1)),
                    unit: 'g',
                    reductionPct: totalQ > 0 ? ((totalH / totalQ) * 100).toFixed(1) : '0'
                  },
                  {
                    metric: 'Wait Latency (s)',
                    baseline: Number((totalQ * 3.2).toFixed(1)),
                    withCache: Number(((totalM * 3.2) + (totalH * 0.002)).toFixed(1)),
                    saved: Number((totalH * 3.198).toFixed(1)),
                    unit: 'sec',
                    reductionPct: totalQ > 0 ? ((totalH / totalQ) * 100).toFixed(1) : '0'
                  }
                ];

                return (
                  <>
                    <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-6">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                            <Leaf className="h-4 w-4 text-emerald-600" />
                            <span>3. Visual Sustainability: Progressive Cache Warming Trajectory</span>
                          </h3>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Demonstrates how CacheMind progressively warms up across all {totalQ} queries: as total inquiries increase, cache hits rise from 0 to {totalH}, driving hit rate from 0% up to {currentHitRatePct}%.
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold flex items-center gap-1.5">
                            <TrendingUp className="h-3.5 w-3.5" />
                            <span>{currentHitRatePct}% Current Hit Rate</span>
                          </span>
                        </div>
                      </div>

                      {/* View Metric Tabs */}
                      <div className="flex items-center justify-between flex-wrap gap-2 pt-1 border-b border-slate-100 pb-3">
                        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
                          <button
                            type="button"
                            onClick={() => setSustainabilityChartMetric('hit_rate')}
                            className={`px-3 py-1 rounded-md text-xs font-medium transition cursor-pointer ${
                              sustainabilityChartMetric === 'hit_rate'
                                ? 'bg-white text-emerald-800 shadow-xs font-semibold'
                                : 'text-slate-600 hover:text-slate-900'
                            }`}
                          >
                            Hit Rate & Query Trajectory
                          </button>
                          <button
                            type="button"
                            onClick={() => setSustainabilityChartMetric('cost')}
                            className={`px-3 py-1 rounded-md text-xs font-medium transition cursor-pointer ${
                              sustainabilityChartMetric === 'cost'
                                ? 'bg-white text-emerald-800 shadow-xs font-semibold'
                                : 'text-slate-600 hover:text-slate-900'
                            }`}
                          >
                            Financial Cost Saved ($ / ₹)
                          </button>
                          <button
                            type="button"
                            onClick={() => setSustainabilityChartMetric('energy')}
                            className={`px-3 py-1 rounded-md text-xs font-medium transition cursor-pointer ${
                              sustainabilityChartMetric === 'energy'
                                ? 'bg-white text-emerald-800 shadow-xs font-semibold'
                                : 'text-slate-600 hover:text-slate-900'
                            }`}
                          >
                            GPU Energy Saved (Wh)
                          </button>
                          <button
                            type="button"
                            onClick={() => setSustainabilityChartMetric('tokens')}
                            className={`px-3 py-1 rounded-md text-xs font-medium transition cursor-pointer ${
                              sustainabilityChartMetric === 'tokens'
                                ? 'bg-white text-emerald-800 shadow-xs font-semibold'
                                : 'text-slate-600 hover:text-slate-900'
                            }`}
                          >
                            Avoided Tokens & Carbon
                          </button>
                        </div>

                        <span className="text-[11px] text-slate-400 font-mono">
                          Dataset: {progressionData.length} Real Recorded Queries
                        </span>
                      </div>

                      {/* Main Interactive Progression Chart */}
                      <div className="h-80 w-full pt-2">
                        {progressionData.length === 0 ? (
                          <div className="h-full flex items-center justify-center text-xs text-slate-400">
                            No query traffic recorded yet to render progression.
                          </div>
                        ) : (
                          <ResponsiveContainer width="100%" height="100%">
                            {sustainabilityChartMetric === 'hit_rate' ? (
                              <ComposedChart data={progressionData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                <defs>
                                  <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.25} />
                                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.02} />
                                  </linearGradient>
                                  <linearGradient id="colorHits" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                <XAxis
                                  dataKey="query_index"
                                  tickFormatter={(v) => `Q#${v}`}
                                  tick={{ fontSize: 11, fill: '#64748b' }}
                                  stroke="#cbd5e1"
                                />
                                <YAxis
                                  yAxisId="left"
                                  tick={{ fontSize: 11, fill: '#64748b' }}
                                  stroke="#cbd5e1"
                                  label={{ value: 'Query Count', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#94a3b8' } }}
                                />
                                <YAxis
                                  yAxisId="right"
                                  orientation="right"
                                  domain={[0, 100]}
                                  tickFormatter={(v) => `${v}%`}
                                  tick={{ fontSize: 11, fill: '#059669' }}
                                  stroke="#10b981"
                                  label={{ value: 'Hit Rate %', angle: 90, position: 'insideRight', style: { fontSize: 10, fill: '#059669' } }}
                                />
                                <RechartsTooltip
                                  content={({ active, payload }) => {
                                    if (active && payload && payload.length) {
                                      const pt: any = payload[0].payload;
                                      return (
                                        <div className="bg-slate-900 text-white p-3 rounded-xl border border-slate-700 shadow-xl text-xs space-y-1.5 max-w-xs">
                                          <div className="flex items-center justify-between border-b border-slate-800 pb-1 font-semibold text-slate-200">
                                            <span>Query #{pt.query_index}</span>
                                            <span
                                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                                pt.is_hit
                                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                                  : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                              }`}
                                            >
                                              {pt.is_hit ? 'CACHE HIT' : 'CACHE MISS'}
                                            </span>
                                          </div>
                                          <p className="text-[11px] text-slate-300 italic line-clamp-2">
                                            "{pt.query_text}"
                                          </p>
                                          <div className="pt-1 text-[11px] space-y-0.5 border-t border-slate-800">
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Progression:</span>
                                              <span className="font-mono text-emerald-400 font-semibold">{pt.cumulative_hits} hits / {pt.cumulative_queries} queries</span>
                                            </div>
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Cumulative Hit Rate:</span>
                                              <span className="font-mono text-emerald-400 font-bold">{pt.hit_rate_pct.toFixed(1)}%</span>
                                            </div>
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Net Cost Saved:</span>
                                              <span className="font-mono text-emerald-400 font-bold">
                                                ${Number(pt.cumulative_cost_saved_usd ?? (pt.cumulative_hits * 0.02995)).toFixed(4)} (~₹{Number(pt.cumulative_cost_saved_inr ?? (pt.cumulative_hits * 2.5008)).toFixed(2)})
                                              </span>
                                            </div>
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Avoided GPU Energy:</span>
                                              <span className="font-mono text-blue-300">{pt.cumulative_energy_wh_saved.toFixed(2)} Wh</span>
                                            </div>
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">CO₂e Avoided:</span>
                                              <span className="font-mono text-teal-300">{pt.cumulative_co2_g_saved.toFixed(1)} g</span>
                                            </div>
                                          </div>
                                        </div>
                                      );
                                    }
                                    return null;
                                  }}
                                />
                                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                                <Area
                                  yAxisId="left"
                                  type="monotone"
                                  dataKey="cumulative_queries"
                                  stroke="#64748b"
                                  fill="url(#colorQueries)"
                                  name="Total Inquiries Received"
                                />
                                <Area
                                  yAxisId="left"
                                  type="monotone"
                                  dataKey="cumulative_hits"
                                  stroke="#10b981"
                                  fill="url(#colorHits)"
                                  strokeWidth={2}
                                  name="Cumulative Cache Hits"
                                />
                                <Line
                                  yAxisId="right"
                                  type="monotone"
                                  dataKey="hit_rate_pct"
                                  stroke="#059669"
                                  strokeWidth={2.5}
                                  dot={{ r: 3, fill: '#059669' }}
                                  activeDot={{ r: 6 }}
                                  name="Cumulative Hit Rate (%)"
                                />
                              </ComposedChart>
                            ) : sustainabilityChartMetric === 'cost' ? (
                              <ComposedChart data={progressionData} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
                                <defs>
                                  <linearGradient id="colorCostUSD" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.05} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                <XAxis
                                  dataKey="query_index"
                                  tickFormatter={(v) => `Q#${v}`}
                                  tick={{ fontSize: 11, fill: '#64748b' }}
                                  stroke="#cbd5e1"
                                />
                                <YAxis
                                  yAxisId="left"
                                  tick={{ fontSize: 11, fill: '#059669' }}
                                  stroke="#10b981"
                                  tickFormatter={(v) => `$${Number(v).toFixed(2)}`}
                                  label={{ value: 'Cost Saved (USD $)', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#059669' } }}
                                />
                                <YAxis
                                  yAxisId="right"
                                  orientation="right"
                                  tick={{ fontSize: 11, fill: '#0d9488' }}
                                  stroke="#14b8a6"
                                  tickFormatter={(v) => `₹${Number(v).toFixed(0)}`}
                                  label={{ value: 'Cost Saved (INR ₹)', angle: 90, position: 'insideRight', style: { fontSize: 10, fill: '#0d9488' } }}
                                />
                                <RechartsTooltip
                                  content={({ active, payload }) => {
                                    if (active && payload && payload.length) {
                                      const pt: any = payload[0].payload;
                                      const costUsd = pt.cumulative_cost_saved_usd ?? (pt.cumulative_hits * 0.02995);
                                      const costInr = pt.cumulative_cost_saved_inr ?? (pt.cumulative_hits * 2.5008);
                                      return (
                                        <div className="bg-slate-900 text-white p-3 rounded-xl border border-slate-700 shadow-xl text-xs space-y-1.5 max-w-xs">
                                          <div className="flex items-center justify-between border-b border-slate-800 pb-1 font-semibold text-slate-200">
                                            <span>Query #{pt.query_index}</span>
                                            <span
                                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                                pt.is_hit
                                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                                  : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                              }`}
                                            >
                                              {pt.is_hit ? 'CACHE HIT' : 'CACHE MISS'}
                                            </span>
                                          </div>
                                          <p className="text-[11px] text-slate-300 italic line-clamp-2">
                                            "{pt.query_text}"
                                          </p>
                                          <div className="pt-1 text-[11px] space-y-0.5 border-t border-slate-800">
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Cumulative Savings (USD):</span>
                                              <span className="font-mono text-emerald-400 font-bold">${Number(costUsd).toFixed(4)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Cumulative Savings (INR):</span>
                                              <span className="font-mono text-teal-300 font-bold">₹{Number(costInr).toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Cache Hits:</span>
                                              <span className="font-mono text-slate-200">{pt.cumulative_hits} of {pt.cumulative_queries} ({pt.hit_rate_pct.toFixed(1)}%)</span>
                                            </div>
                                            <div className="flex justify-between">
                                              <span className="text-slate-400">Avoided GPU Energy:</span>
                                              <span className="font-mono text-blue-300">{pt.cumulative_energy_wh_saved.toFixed(2)} Wh</span>
                                            </div>
                                          </div>
                                        </div>
                                      );
                                    }
                                    return null;
                                  }}
                                />
                                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                                <Area
                                  yAxisId="left"
                                  type="monotone"
                                  dataKey="cumulative_cost_saved_usd"
                                  stroke="#10b981"
                                  strokeWidth={2}
                                  fill="url(#colorCostUSD)"
                                  name="Cumulative Financial Savings (USD $)"
                                />
                                <Line
                                  yAxisId="right"
                                  type="monotone"
                                  dataKey="cumulative_cost_saved_inr"
                                  stroke="#14b8a6"
                                  strokeWidth={2}
                                  dot={false}
                                  name="Cumulative Financial Savings (INR ₹)"
                                />
                              </ComposedChart>
                            ) : sustainabilityChartMetric === 'energy' ? (
                              <AreaChart data={progressionData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                <defs>
                                  <linearGradient id="colorEnergy" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                <XAxis dataKey="query_index" tickFormatter={(v) => `Q#${v}`} tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" label={{ value: 'Watt-Hours (Wh)', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#3b82f6' } }} />
                                <RechartsTooltip
                                  formatter={(value: any) => [`${Number(value).toFixed(2)} Wh`, 'GPU Energy Avoided']}
                                  labelFormatter={(label) => `Query #${label}`}
                                />
                                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                                <Area type="monotone" dataKey="cumulative_energy_wh_saved" stroke="#3b82f6" strokeWidth={2} fill="url(#colorEnergy)" name="Avoided GPU Inference Power (Watt-Hours)" />
                              </AreaChart>
                            ) : (
                              <AreaChart data={progressionData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                <defs>
                                  <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.05} />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                <XAxis dataKey="query_index" tickFormatter={(v) => `Q#${v}`} tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" label={{ value: 'Tokens Avoided', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#f59e0b' } }} />
                                <RechartsTooltip
                                  formatter={(value: any) => [`${Number(value).toLocaleString()} tokens`, 'Avoided LLM Tokens']}
                                  labelFormatter={(label) => `Query #${label}`}
                                />
                                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                                <Area type="monotone" dataKey="cumulative_tokens_saved" stroke="#f59e0b" strokeWidth={2} fill="url(#colorTokens)" name="Avoided LLM Compute Tokens" />
                              </AreaChart>
                            )}
                          </ResponsiveContainer>
                        )}
                      </div>

                      {/* Cache Warming Milestones Progression Bar */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                        <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                          <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                            <span>Phase 1: Cold Start (Q1–Q8)</span>
                            <span className="font-mono text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded text-[10px] border border-amber-200">0.0% Hits</span>
                          </div>
                          <p className="text-[11px] text-slate-500 leading-relaxed">
                            Initial user queries populate unseeded policy vectors into FAISS. Grounded fallback is invoked while the knowledge base initializes.
                          </p>
                        </div>

                        <div className="p-3.5 rounded-lg bg-emerald-50/50 border border-emerald-200 space-y-1">
                          <div className="flex items-center justify-between text-xs font-semibold text-emerald-900">
                            <span>Phase 2: Warming Surge (Q9–Q20)</span>
                            <span className="font-mono text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded text-[10px] font-bold">11% → 33% Hits</span>
                          </div>
                          <p className="text-[11px] text-emerald-800/80 leading-relaxed">
                            Recurring employee questions on core policies (paternity leave, allowances, travel) trigger sub-2ms cache hits, accelerating hit rate.
                          </p>
                        </div>

                        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-300 space-y-1">
                          <div className="flex items-center justify-between text-xs font-semibold text-emerald-900">
                            <span>Phase 3: Steady-State (Q21–Q33)</span>
                            <span className="font-mono text-emerald-800 bg-emerald-200/60 px-1.5 py-0.5 rounded text-[10px] font-bold">~48.5% – 50% Hits</span>
                          </div>
                          <p className="text-[11px] text-emerald-900/90 leading-relaxed">
                            Cache saturation achieved. Approximately 1 in every 2 employee questions is absorbed instantaneously with zero external GPU inference.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* SECTION 4: RESOURCE CONSERVATION & GREEN AI BASELINE COMPARISON */}
                    <div className="p-6 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                            <Activity className="h-4 w-4 text-emerald-600" />
                            <span>4. Resource Conservation: Uncached LLM Baseline vs. Governed Cache</span>
                          </h3>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Comparison between traditional 100% cloud model inference and CacheMind's governed semantic caching architecture.
                          </p>
                        </div>
                        <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">
                          {((totalH / totalQ) * 100).toFixed(1)}% Datacenter Compute Conserved
                        </span>
                      </div>

                      {/* Side-by-Side Comparison Chart */}
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
                        <div className="h-64 w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={comparativeData} layout="vertical" margin={{ top: 10, right: 30, left: 40, bottom: 10 }}>
                              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                              <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                              <YAxis type="category" dataKey="metric" tick={{ fontSize: 11, fill: '#334155' }} stroke="#cbd5e1" width={120} />
                              <RechartsTooltip
                                formatter={(value: any, name: any, item: any) => {
                                  const isCost = item?.payload?.metric === 'Financial Cost ($)';
                                  return [isCost ? `$${Number(value).toFixed(2)}` : `${value}`, name];
                                }}
                              />
                              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                              <Bar dataKey="baseline" fill="#cbd5e1" name="Without Cache (100% LLM Calls)" radius={[0, 4, 4, 0]} />
                              <Bar dataKey="withCache" fill="#10b981" name="With CacheMind (Governed Cache)" radius={[0, 4, 4, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>

                        {/* Comparative Value Cards */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200">
                            <span className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider">Financial Cost Saved</span>
                            <div className="text-xl font-bold text-emerald-900 mt-1">
                              ${(totalH * 0.02995).toFixed(2)}
                            </div>
                            <p className="text-[10px] text-emerald-700 mt-0.5">
                              ~₹{(totalH * 2.5008).toFixed(0)} saved in external model API costs
                            </p>
                          </div>

                          <div className="p-3.5 rounded-lg bg-teal-50/70 border border-teal-200">
                            <span className="text-[10px] uppercase font-bold text-teal-700 tracking-wider">GPU Energy Saved</span>
                            <div className="text-xl font-bold text-teal-900 mt-1">
                              {(totalH * 0.47).toFixed(2)} Wh
                            </div>
                            <p className="text-[10px] text-teal-700/90 mt-0.5">
                              ~{(totalH * 1.69).toFixed(1)} kJ direct datacenter power conserved
                            </p>
                          </div>

                          <div className="p-3.5 rounded-lg bg-blue-50/70 border border-blue-200">
                            <span className="text-[10px] uppercase font-bold text-blue-700 tracking-wider">Carbon Avoided</span>
                            <div className="text-xl font-bold text-blue-900 mt-1">
                              {(totalH * 2.50).toFixed(1)} g CO₂e
                            </div>
                            <p className="text-[10px] text-blue-700/90 mt-0.5">
                              Eliminated cloud datacenter Scope 2 & 3 carbon footprint
                            </p>
                          </div>

                          <div className="p-3.5 rounded-lg bg-purple-50/70 border border-purple-200">
                            <span className="text-[10px] uppercase font-bold text-purple-700 tracking-wider">Latency Saved</span>
                            <div className="text-xl font-bold text-purple-900 mt-1">
                              {(totalH * 3.198).toFixed(1)}s
                            </div>
                            <p className="text-[10px] text-purple-700/90 mt-0.5">
                              Total employee productivity wait time eliminated
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          );
        })()}

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
        {/* TAB: INSUFFICIENT DATA QUESTIONS (POLICY EVIDENCE GAPS) */}
        {/* ======================================================== */}
        {activeTab === 'insufficient' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FileQuestion className="h-5 w-5 text-amber-600" />
                  <span>Insufficient Data Questions (Policy Evidence Gaps)</span>
                </h2>
                <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
                  Questions asked by users that could not be answered with high confidence using authorized policy documents.
                  Use this log to identify missing clauses, upload updated policies, and auto-resolve gaps.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleBatchReEvaluateGaps}
                  disabled={reEvaluating}
                  className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-50 transition shadow-2xs"
                  title="Re-evaluates all pending questions against newly uploaded or updated policies"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${reEvaluating ? 'animate-spin' : ''}`} />
                  <span>{reEvaluating ? 'Re-evaluating...' : 'Re-evaluate Against Policies'}</span>
                </button>
              </div>
            </div>

            {/* Filter & Search Bar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              {/* Status Tabs */}
              <div className="flex items-center bg-slate-100 p-1 rounded-lg text-xs font-medium">
                {[
                  { key: 'ALL', label: 'All', count: insufficientData?.total ?? 0 },
                  { key: 'PENDING', label: 'Pending', count: insufficientData?.pending_count ?? 0, highlight: (insufficientData?.pending_count ?? 0) > 0 },
                  { key: 'REVIEWED', label: 'Reviewed', count: insufficientData?.reviewed_count ?? 0 },
                  { key: 'RESOLVED', label: 'Resolved', count: insufficientData?.resolved_count ?? 0 }
                ].map((st) => (
                  <button
                    key={st.key}
                    onClick={() => {
                      setInsufficientStatusFilter(st.key as any);
                    }}
                    className={`px-3 py-1.5 rounded-md transition flex items-center gap-1.5 ${
                      insufficientStatusFilter === st.key
                        ? 'bg-white text-slate-900 font-bold shadow-2xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span>{st.label}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                      st.highlight ? 'bg-amber-100 text-amber-800 font-bold' : 'bg-slate-200 text-slate-700'
                    }`}>
                      {st.count}
                    </span>
                  </button>
                ))}
              </div>

              {/* Search */}
              <div className="relative min-w-[280px]">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search questions, reasons, scope..."
                  value={insufficientSearch}
                  onChange={(e) => setInsufficientSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      fetchInsufficientQuestions(undefined, e.currentTarget.value);
                    }
                  }}
                  className="w-full pl-9 pr-8 py-1.5 text-xs rounded-lg border border-slate-200 bg-white focus:outline-hidden focus:ring-1 focus:ring-slate-900"
                />
                {insufficientSearch && (
                  <button
                    onClick={() => {
                      setInsufficientSearch('');
                      fetchInsufficientQuestions(undefined, '');
                    }}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Questions Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
              {insufficientLoading ? (
                <div className="p-12 text-center text-xs text-slate-500">
                  <RefreshCw className="h-5 w-5 animate-spin mx-auto text-slate-400 mb-2" />
                  Loading insufficient data questions...
                </div>
              ) : !insufficientData || insufficientData.items.length === 0 ? (
                <div className="p-12 text-center text-xs text-slate-500 space-y-2">
                  <CheckCircle2 className="h-8 w-8 mx-auto text-emerald-500" />
                  <p className="font-semibold text-slate-800 text-sm">No Insufficient Data Questions Found</p>
                  <p className="text-slate-500 max-w-md mx-auto">
                    {insufficientSearch
                      ? 'No questions matched your search criteria.'
                      : 'All queries processed by CacheMind have sufficient policy evidence! Questions that cannot be answered will appear here automatically.'}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[10px]">
                        <th className="py-3 px-4">User Question & Scope</th>
                        <th className="py-3 px-4">Classification & Reason</th>
                        <th className="py-3 px-4">Confidence</th>
                        <th className="py-3 px-4">Frequency & Timing</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Admin Notes</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {insufficientData.items.map((gap) => (
                        <tr key={gap.id} className="hover:bg-slate-50/70 transition">
                          <td className="py-3.5 px-4 max-w-xs">
                            <div className="font-semibold text-slate-900 text-xs leading-snug">
                              {gap.query_text}
                            </div>
                            {gap.normalized_query && gap.normalized_query !== gap.query_text.toLowerCase() && (
                              <div className="text-[10px] text-slate-400 font-mono mt-0.5 truncate">
                                Normalized: {gap.normalized_query}
                              </div>
                            )}
                            <div className="flex items-center gap-1.5 mt-1.5">
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700">
                                Scope: {gap.policy_scope}
                              </span>
                              {gap.occurrence_count > 1 && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                                  {gap.occurrence_count}x Asked
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="py-3.5 px-4 max-w-xs">
                            <div>
                              {gap.retrieval_status === 'DOCUMENT_CONFLICT' ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-100 text-purple-800 border border-purple-200">
                                  Document Conflict
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                                  Insufficient Evidence
                                </span>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-600 mt-1 line-clamp-2" title={gap.reason || ''}>
                              {gap.reason || 'No supporting clause found in approved policy documents.'}
                            </p>
                          </td>

                          <td className="py-3.5 px-4 whitespace-nowrap">
                            <span className="font-mono text-slate-700 font-semibold">
                              {gap.confidence_score ? `${(gap.confidence_score * 100).toFixed(1)}%` : '0.0%'}
                            </span>
                            <span className="text-[10px] text-slate-400 block">evidence match</span>
                          </td>

                          <td className="py-3.5 px-4 whitespace-nowrap text-[11px] text-slate-600">
                            <div>
                              <span className="text-slate-400 text-[10px]">Last: </span>
                              {new Date(gap.last_asked_at).toLocaleDateString()} {new Date(gap.last_asked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </div>
                            {gap.occurrence_count > 1 && (
                              <div className="text-[10px] text-slate-400 mt-0.5">
                                First: {new Date(gap.first_asked_at).toLocaleDateString()}
                              </div>
                            )}
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                              User: {gap.user_id ? gap.user_id.slice(0, 8) : 'Anonymous'}
                            </div>
                          </td>

                          <td className="py-3.5 px-4 whitespace-nowrap">
                            {gap.status === 'PENDING' && (
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                                Pending Review
                              </span>
                            )}
                            {gap.status === 'REVIEWED' && (
                              <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                                Reviewed
                              </span>
                            )}
                            {gap.status === 'RESOLVED' && (
                              <div>
                                <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                                  Resolved
                                </span>
                                {gap.resolved_by_policy_id && (
                                  <div className="text-[10px] text-emerald-700 font-mono mt-1">
                                    By: {gap.resolved_by_policy_id}
                                  </div>
                                )}
                              </div>
                            )}
                          </td>

                          <td className="py-3.5 px-4 max-w-xs">
                            {editingGapNotes && editingGapNotes.id === gap.id ? (
                              <div className="space-y-1.5">
                                <input
                                  type="text"
                                  value={editingGapNotes.notes}
                                  onChange={(e) => setEditingGapNotes({ ...editingGapNotes, notes: e.target.value })}
                                  placeholder="Add admin note..."
                                  className="w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-slate-900 focus:outline-hidden"
                                />
                                <div className="flex items-center gap-1.5">
                                  <button
                                    onClick={() => handleSaveGapNotes(gap.id, editingGapNotes.notes)}
                                    className="px-2 py-0.5 text-[10px] bg-slate-900 text-white rounded font-medium hover:bg-slate-800"
                                  >
                                    Save
                                  </button>
                                  <button
                                    onClick={() => setEditingGapNotes(null)}
                                    className="px-2 py-0.5 text-[10px] text-slate-600 hover:text-slate-900"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div className="flex items-start justify-between gap-1 group">
                                <span className={`text-[11px] ${gap.admin_notes ? 'text-slate-700' : 'text-slate-400 italic'}`}>
                                  {gap.admin_notes || 'No notes added'}
                                </span>
                                <button
                                  onClick={() => setEditingGapNotes({ id: gap.id, notes: gap.admin_notes || '' })}
                                  className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-700 transition"
                                  title="Edit note"
                                >
                                  <Edit3 className="h-3 w-3" />
                                </button>
                              </div>
                            )}
                          </td>

                          <td className="py-3.5 px-4 whitespace-nowrap text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {gap.status === 'PENDING' && (
                                <>
                                  <button
                                    onClick={() => handleUpdateGapStatus(gap.id, 'REVIEWED')}
                                    className="px-2 py-1 text-[11px] font-medium bg-slate-100 text-slate-700 rounded hover:bg-slate-200 transition"
                                  >
                                    Mark Reviewed
                                  </button>
                                  <button
                                    onClick={() => handleUpdateGapStatus(gap.id, 'RESOLVED')}
                                    className="px-2 py-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded hover:bg-emerald-100 transition"
                                  >
                                    Resolve
                                  </button>
                                </>
                              )}
                              {gap.status === 'REVIEWED' && (
                                <>
                                  <button
                                    onClick={() => handleUpdateGapStatus(gap.id, 'RESOLVED')}
                                    className="px-2 py-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded hover:bg-emerald-100 transition"
                                  >
                                    Resolve
                                  </button>
                                  <button
                                    onClick={() => handleUpdateGapStatus(gap.id, 'PENDING')}
                                    className="px-2 py-1 text-[11px] text-slate-500 hover:text-slate-800 transition"
                                  >
                                    Re-open
                                  </button>
                                </>
                              )}
                              {gap.status === 'RESOLVED' && (
                                <button
                                  onClick={() => handleUpdateGapStatus(gap.id, 'PENDING')}
                                  className="px-2 py-1 text-[11px] text-slate-500 hover:text-slate-800 transition"
                                >
                                  Re-open
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB: VERIFIED SEMANTIC CACHE EXPLORER */}
        {/* ======================================================== */}
        {activeTab === 'cache' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Verified Semantic Cache Explorer ({cacheEntries.length})
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Verified question-and-answer records available for instant semantic reuse. Populated dynamically as questions are answered.
                </p>
              </div>

              <div className="flex items-center gap-2.5">
                <button
                  onClick={() => setShowColdStartModal(true)}
                  className="px-3.5 py-1.5 rounded-lg border border-rose-300 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold flex items-center gap-1.5 transition shadow-2xs"
                  title="Wipe cache entries to test cold start workflow"
                >
                  <RotateCcw className="h-3.5 w-3.5 text-rose-600" />
                  <span>Reset Cache (Cold Start)</span>
                </button>
                <button
                  onClick={handleRebuildIndex}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <RefreshCw className="h-3.5 w-3.5 text-slate-600" />
                  <span>Re-sync Cache Index</span>
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
                        Cache ID: {c.id.slice(0, 8)}
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

            {/* Modal for Cold Start Reset Confirmation */}
            {showColdStartModal && (
              <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                <div className="bg-white border border-slate-200 rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-full bg-rose-100 text-rose-600">
                      <AlertTriangle className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">
                        Initiate Cold-Start Reset?
                      </h3>
                      <p className="text-xs text-slate-500">
                        Empties the semantic cache (N=0) to test dynamic learning.
                      </p>
                    </div>
                  </div>

                  <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1.5">
                    <p className="font-semibold text-slate-800">
                      Cold-Start Learning Lifecycle:
                    </p>
                    <ul className="list-disc pl-4 space-y-1 text-slate-600">
                      <li>Deactivates all cached entries in SQLite.</li>
                      <li>Rebuilds the FAISS index with <span className="font-mono font-semibold text-slate-800">0 vectors</span>.</li>
                      <li>User questions initially produce a <span className="font-semibold text-rose-600">CACHE MISS</span> and are answered strictly from authoritative uploaded policy documents.</li>
                      <li>The grounded answer is automatically cached via dynamic write-on-miss!</li>
                      <li>Subsequent questions yield instant <span className="font-semibold text-emerald-600">CACHE HITS</span> (&lt; 5ms).</li>
                    </ul>
                  </div>

                  <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
                    <button
                      type="button"
                      disabled={resettingCache}
                      onClick={() => setShowColdStartModal(false)}
                      className="px-3.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs text-slate-700 font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={resettingCache}
                      onClick={handleColdStartReset}
                      className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white flex items-center gap-1.5 shadow-xs"
                    >
                      {resettingCache ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          <span>Resetting...</span>
                        </>
                      ) : (
                        <span>Confirm Cold-Start Reset</span>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};
