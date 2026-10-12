import axios from 'axios';
import {
  DashboardSummary,
  QueryResponse,
  CacheEntry,
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
