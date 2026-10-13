import axios from 'axios';
import {
  DashboardSummary,
  QueryResponse,
  QueryCheckResponse,
  CacheEntry,
  Policy,
  PolicyPreview,
  ModelStatusResponse,
  ModelArtifactVersion,
  EvaluationResultsResponse,
  ClusterAnalyticsResponse,
  AuditLog,
  UserHistoryItem,
  UserAnalytics,
  FeedbackItem,
  FavoriteItem,
  Conversation,
  CandidatePair,
  SettingsData,
  User,
  AuthResponse
} from '../types';

export const api = axios.create({
  baseURL: '/api'
});

// Attach Authorization header if token exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cachemind_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ==========================================
// AUTHENTICATION APIS
// ==========================================
export const loginUser = async (credentials: { username: string; password: string }): Promise<AuthResponse> => {
  const res = await api.post('/auth/login', credentials);
  if (res.data.access_token) {
    localStorage.setItem('cachemind_token', res.data.access_token);
    localStorage.setItem('cachemind_user', JSON.stringify(res.data.user));
  }
  return res.data;
};

export const registerUser = async (data: {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  department?: string;
}): Promise<AuthResponse> => {
  const res = await api.post('/auth/register', data);
  if (res.data.access_token) {
    localStorage.setItem('cachemind_token', res.data.access_token);
    localStorage.setItem('cachemind_user', JSON.stringify(res.data.user));
  }
  return res.data;
};

export const getCurrentUser = async (): Promise<User> => {
  const res = await api.get('/auth/me');
  return res.data;
};

export const logoutUser = () => {
  localStorage.removeItem('cachemind_token');
  localStorage.removeItem('cachemind_user');
};

// ==========================================
// USER WORKSPACE APIS
// ==========================================
export const submitUserQuery = async (
  query: string,
  domain?: string,
  conversation_id?: string
): Promise<QueryResponse> => {
  const res = await api.post('/user/query', { query, domain, conversation_id });
  return res.data;
};

export const getUserHistory = async (limit: number = 50): Promise<UserHistoryItem[]> => {
  const res = await api.get('/user/history', { params: { limit } });
  return res.data;
};

export const searchUserHistory = async (q: string): Promise<UserHistoryItem[]> => {
  const res = await api.get('/user/history/search', { params: { q } });
  return res.data;
};

export const deleteUserHistory = async (logId?: string): Promise<{ message: string }> => {
  const res = await api.delete('/user/history', { params: logId ? { log_id: logId } : {} });
  return res.data;
};

export const getUserAnalytics = async (): Promise<UserAnalytics> => {
  const res = await api.get('/user/analytics');
  return res.data;
};

export const submitUserFeedback = async (data: {
  log_id?: string;
  query_text: string;
  answer_text: string;
  rating: 'helpful' | 'not_helpful';
  comment?: string;
  is_reported_incorrect?: boolean;
  report_reason?: string;
}): Promise<FeedbackItem> => {
  const res = await api.post('/user/feedback', data);
  return res.data;
};

export const getUserFavorites = async (): Promise<FavoriteItem[]> => {
  const res = await api.get('/user/favorites');
  return res.data;
};

export const addUserFavorite = async (data: {
  query_text: string;
  answer: string;
  policy_id?: string | null;
  policy_version?: string | null;
  is_cached?: boolean;
}): Promise<FavoriteItem> => {
  const res = await api.post('/user/favorites', data);
  return res.data;
};

export const removeUserFavorite = async (favId: string): Promise<{ message: string }> => {
  const res = await api.delete(`/user/favorites/${favId}`);
  return res.data;
};

export const getUserConversations = async (): Promise<Conversation[]> => {
  const res = await api.get('/user/conversations');
  return res.data;
};

export const createUserConversation = async (title?: string): Promise<Conversation> => {
  const res = await api.post('/user/conversations', { title });
  return res.data;
};

export const deleteUserConversation = async (convId: string): Promise<{ message: string }> => {
  const res = await api.delete(`/user/conversations/${convId}`);
  return res.data;
};

export const getSuggestedQuestions = async (): Promise<{ id: string; question: string; domain: string; policy_id: string }[]> => {
  const res = await api.get('/user/suggested-questions');
  return res.data;
};

// ==========================================
// ADMINISTRATOR APIS
// ==========================================
export const getAllUsers = async (): Promise<User[]> => {
  const res = await api.get('/admin/users');
  return res.data;
};

export const updateUserStatus = async (
  userId: string,
  update: { is_active?: boolean; role?: string; department?: string }
): Promise<User> => {
  const res = await api.patch(`/admin/users/${userId}/status`, update);
  return res.data;
};

export const previewPolicyDocument = async (formData: FormData): Promise<PolicyPreview> => {
  const res = await api.post('/admin/policies/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
};

export const createAuthoritativePolicy = async (policyData: Partial<Policy>): Promise<Policy> => {
  const res = await api.post('/admin/policies', policyData);
  return res.data;
};

export const updateAuthoritativePolicy = async (
  policyId: string,
  policyData: Partial<Policy>
): Promise<Policy> => {
  const res = await api.put(`/admin/policies/${policyId}`, policyData);
  return res.data;
};

export const deactivatePolicy = async (policyId: string): Promise<any> => {
  const res = await api.post(`/admin/policies/${policyId}/deactivate`);
  return res.data;
};

export const invalidateObsoleteCache = async (): Promise<any> => {
  const res = await api.post('/admin/policies/invalidate-cache');
  return res.data;
};

export const generateSyntheticPairs = async (
  policyId?: string,
  numPairs: number = 2
): Promise<CandidatePair[]> => {
  const res = await api.post('/admin/datasets/generate-synthetic', {
    policy_id: policyId,
    num_pairs_per_clause: numPairs
  });
  return res.data;
};

export const uploadDatasetCsv = async (formData: FormData): Promise<any> => {
  const res = await api.post('/admin/datasets/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
};

export const getModelRegistry = async (): Promise<ModelArtifactVersion[]> => {
  const res = await api.get('/admin/models/registry');
  return res.data;
};

export const rollbackModelVersion = async (targetVersionTag: string): Promise<any> => {
  const res = await api.post('/admin/models/rollback', {
    target_version_tag: targetVersionTag
  });
  return res.data;
};

export const getAdminFeedback = async (
  statusFilter?: string,
  reportedOnly: boolean = false
): Promise<FeedbackItem[]> => {
  const res = await api.get('/admin/feedback', {
    params: { status_filter: statusFilter, reported_only: reportedOnly }
  });
  return res.data;
};

export const reviewAdminFeedback = async (
  feedbackId: string,
  data: { status?: string; admin_notes?: string }
): Promise<FeedbackItem> => {
  const res = await api.patch(`/admin/feedback/${feedbackId}`, data);
  return res.data;
};

export const exportAuditLogsUrl = () => '/api/admin/audit-logs/export';

// ==========================================
// CORE / COMMON APIS
// ==========================================
export const getDashboardSummary = async (): Promise<DashboardSummary> => {
  const res = await api.get('/dashboard/summary');
  return res.data;
};

export const submitQuery = async (query: string, domain?: string): Promise<QueryResponse> => {
  const res = await api.post('/query', { query, domain });
  return res.data;
};

export const checkOrOptimizeQuery = async (query: string, domain?: string): Promise<QueryCheckResponse> => {
  const res = await api.post('/query/check-or-optimize', { query, domain });
  return res.data;
};

export const getPolicies = async (): Promise<Policy[]> => {
  const res = await api.get('/policies');
  return res.data;
};

export const createPolicy = async (policyData: Partial<Policy>): Promise<Policy> => {
  const res = await api.post('/policies', policyData);
  return res.data;
};

export const updatePolicy = async (policyId: string, policyData: Partial<Policy>): Promise<Policy> => {
  const res = await api.put(`/policies/${policyId}`, policyData);
  return res.data;
};

export const deletePolicy = async (policyId: string): Promise<any> => {
  const res = await api.delete(`/policies/${policyId}`);
  return res.data;
};

export const uploadPolicyFile = async (formData: FormData): Promise<any> => {
  const res = await api.post('/policies/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
};

export const getCacheEntries = async (domain?: string, verifiedOnly: boolean = false): Promise<CacheEntry[]> => {
  const res = await api.get('/cache', {
    params: { domain, verified_only: verifiedOnly }
  });
  return res.data;
};

export const createCacheEntry = async (entry: any): Promise<CacheEntry> => {
  const res = await api.post('/cache', entry);
  return res.data;
};

export const updateCacheEntry = async (entryId: string, update: Partial<CacheEntry>): Promise<CacheEntry> => {
  const res = await api.patch(`/cache/${entryId}`, update);
  return res.data;
};

export const deleteCacheEntry = async (id: string): Promise<any> => {
  const res = await api.delete(`/cache/${id}`);
  return res.data;
};

export const rebuildCacheIndex = async (): Promise<any> => {
  const res = await api.post('/cache/rebuild-index');
  return res.data;
};

export const getModelStatus = async (): Promise<ModelStatusResponse> => {
  const res = await api.get('/models/status');
  return res.data;
};

export const triggerModelTraining = async (): Promise<any> => {
  const res = await api.post('/models/train');
  return res.data;
};

export const getEvaluationResults = async (): Promise<EvaluationResultsResponse> => {
  const res = await api.get('/evaluation/results');
  return res.data;
};

export const activateThreshold = async (threshold: number): Promise<any> => {
  const res = await api.post(`/evaluation/activate-threshold?threshold=${threshold}`);
  return res.data;
};

export const getClusterAnalytics = async (n_clusters: number = 3): Promise<ClusterAnalyticsResponse> => {
  const res = await api.get('/analytics/clusters', {
    params: { n_clusters }
  });
  return res.data;
};

export const getAuditLogs = async (limit: number = 50, decision?: string): Promise<AuditLog[]> => {
  const res = await api.get('/audit-logs', {
    params: { limit, decision }
  });
  return res.data;
};

export const getSettings = async (): Promise<SettingsData> => {
  const res = await api.get('/settings');
  return res.data;
};

export const updateSettings = async (settings: Partial<SettingsData>): Promise<any> => {
  const res = await api.patch('/settings', settings);
  return res.data;
};

export const listDatasets = async (): Promise<any[]> => {
  const res = await api.get('/datasets');
  return res.data;
};
