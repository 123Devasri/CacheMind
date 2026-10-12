import axios from 'axios';
import {
  DashboardSummary,
  QueryResponse,
  QueryCheckResponse,
  CacheEntry,
  Policy,
  ModelStatusResponse,
  EvaluationResultsResponse,
  ClusterAnalyticsResponse,
  AuditLog,
  SettingsData
} from '../types';

const api = axios.create({
  baseURL: '/api'
});

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

// Policies CRUD & Upload
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
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return res.data;
};

// Cache entries
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

export const deleteCacheEntry = async (id: string): Promise<any> => {
  const res = await api.delete(`/cache/${id}`);
  return res.data;
};

export const rebuildCacheIndex = async (): Promise<any> => {
  const res = await api.post('/cache/rebuild-index');
  return res.data;
};

// ML Models
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
