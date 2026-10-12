export interface CandidateInfo {
  cache_id: string;
  faiss_id: number;
  question: string;
  cosine_similarity: number;
  classifier_score: number;
  calibrated_probability: number;
  applied_threshold: number;
  policy_condition_passed: boolean;
  condition_mismatches: string[];
}

export interface QueryResponse {
  query: string;
  decision: string;
  is_cached: boolean;
  answer: string;
  provider_used: string;
  rejection_reasons: string[];
  candidate: CandidateInfo | null;
  active_threshold: number;
  lookup_latency_ms: number;
  total_latency_ms: number;
  log_id?: string;
}

export interface QueryCheckResponse {
  status: string; // "HIT" | "CACHE_MISS" | "NEEDS_CONFIRMATION"
  is_cached: boolean;
  needs_confirmation: boolean;
  original_query: string;
  optimized_query?: string | null;
  removed_filler?: string[];
  answer?: string | null;
  provider_used?: string | null;
  candidate?: CandidateInfo | null;
  lookup_latency_ms?: number | null;
  total_latency_ms?: number | null;
}

export interface DashboardSummary {
  total_queries: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_ratio: number;
  avg_lookup_latency_ms: number;
  avg_fallback_latency_ms: number;
  estimated_calls_avoided: number;
  estimated_cost_saved_usd: number;
  estimated_cost_saved_inr: number;
  active_threshold: number;
  target_fhr: number;
  observed_fhr: number | null;
  upper_confidence_bound: number | null;
  model_status: Record<string, string>;
}

export interface CacheEntry {
  id: string;
  faiss_id: number | null;
  question: string;
  answer: string;
  policy_id: string;
  policy_version: string;
  domain: string;
  jurisdiction: string;
  employee_category: string;
  numerical_limits: Record<string, number>;
  is_verified: boolean;
  is_active: boolean;
  hit_count: number;
  created_at: string;
}

export interface Policy {
  id: string;
  policy_id: string;
  name: string;
  domain: string;
  jurisdiction: string;
  employee_category: string;
  current_version: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface ModelStatusResponse {
  embedding_transformer: {
    model_name: string;
    embedding_dim: number;
    device: string;
    is_ready: boolean;
  };
  faiss_index: {
    total_vectors: number;
    dimension: number;
    metric: string;
  };
  classifier: any;
  calibrator: any;
}

export interface ThresholdResult {
  threshold: number;
  evaluated_hits: number;
  false_hits: number;
  observed_fhr: number;
  upper_confidence_bound: number;
  meets_target: boolean;
}

export interface EvaluationResultsResponse {
  id: string;
  target_fhr: number;
  confidence_level: number;
  selected_threshold: number | null;
  status: string;
  sample_size: number;
  false_hits: number;
  observed_fhr: number;
  upper_confidence_bound: number;
  results: ThresholdResult[];
  created_at: string;
  is_active: boolean;
}

export interface ClusterInfo {
  cluster_id: number;
  name: string;
  size: number;
  representative_questions: string[];
  keywords: string[];
}

export interface ClusterPoint {
  question: string;
  cluster_id: number;
  x: number;
  y: number;
}

export interface ClusterAnalyticsResponse {
  status: string;
  cluster_count: number;
  total_queries: number;
  clusters: ClusterInfo[];
  points: ClusterPoint[];
}

export interface AuditLog {
  id: string;
  query_text: string;
  domain_filter: string | null;
  decision: string;
  rejection_reasons: string[];
  candidate_question: string | null;
  cosine_similarity: number | null;
  classifier_score: number | null;
  calibrated_probability: number | null;
  applied_threshold: number | null;
  policy_condition_passed: boolean;
  condition_mismatches: string[];
  returned_answer: string;
  is_cached_result: boolean;
  provider_used: string;
  lookup_latency_ms: number;
  total_latency_ms: number;
  created_at: string;
}

export interface SettingsData {
  cache_threshold: number;
  min_cosine_similarity: number;
  top_k: number;
  target_fhr: number;
  confidence_level: number;
  fallback_provider: string;
  openai_model: string;
  openai_api_key_configured: boolean;
  openai_api_key?: string;
  grok_api_key_configured?: boolean;
  grok_api_key?: string;
  company_name?: string;
  location?: string;
}
