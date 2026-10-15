from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# --- Auth & User Schemas ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = ""
    department: Optional[str] = "General"

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    full_name: str
    department: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserStatusUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None
    department: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Conversation Schemas ---
class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Query Schemas ---
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User question to look up")
    domain: Optional[str] = Field(None, description="Optional domain filter (HR, IT, FINANCE)")
    conversation_id: Optional[str] = Field(None, description="Optional conversation session ID")

class CandidateInfo(BaseModel):
    cache_id: str
    faiss_id: int
    question: str
    cosine_similarity: float
    classifier_score: float
    calibrated_probability: float
    applied_threshold: float
    policy_condition_passed: bool
    condition_mismatches: List[str]

class QueryResponse(BaseModel):
    query: str
    decision: str # "HIT", "CACHE_MISS", "INSUFFICIENT_EVIDENCE", "GREETING", "REJECTED_EMPTY_QUERY"
    is_cached: bool
    answer: str
    provider_used: str
    rejection_reasons: List[str]
    candidate: Optional[CandidateInfo] = None
    active_threshold: float
    lookup_latency_ms: float
    total_latency_ms: float
    log_id: Optional[str] = None
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    source_citation: Optional[str] = None
    source_document: Optional[str] = None
    # Grok API & Document Evidence Fields
    grok_invoked: bool = False
    tokens_used: Optional[Dict[str, int]] = None
    supporting_evidence_references: List[str] = Field(default_factory=list)
    validation_status: Optional[str] = "passed"
    estimated_cost_usd: Optional[float] = None

class QueryCheckResponse(BaseModel):
    status: str # "HIT", "CACHE_MISS", "INSUFFICIENT_EVIDENCE", "NEEDS_CONFIRMATION", "GREETING"
    is_cached: bool
    needs_confirmation: bool = False
    original_query: str
    optimized_query: Optional[str] = None
    removed_filler: List[str] = Field(default_factory=list)
    answer: Optional[str] = None
    provider_used: Optional[str] = None
    candidate: Optional[CandidateInfo] = None
    lookup_latency_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    source_citation: Optional[str] = None
    grok_invoked: bool = False
    tokens_used: Optional[Dict[str, int]] = None
    supporting_evidence_references: List[str] = Field(default_factory=list)
    validation_status: Optional[str] = "passed"

# --- User Feedback & Report Schemas ---
class FeedbackCreate(BaseModel):
    log_id: Optional[str] = None
    query_text: str
    answer_text: str
    rating: str = Field(..., description="'helpful' or 'not_helpful'")
    comment: Optional[str] = None
    is_reported_incorrect: bool = False
    report_reason: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    log_id: Optional[str]
    query_text: str
    answer_text: str
    rating: str
    comment: Optional[str]
    is_reported_incorrect: bool
    report_reason: Optional[str]
    status: str
    admin_notes: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FeedbackAdminUpdate(BaseModel):
    status: Optional[str] = Field(None, description="'pending', 'reviewed', 'resolved'")
    admin_notes: Optional[str] = None

# --- User Favorite Schemas ---
class FavoriteCreate(BaseModel):
    query_text: str
    answer: str
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    is_cached: bool = True

class FavoriteResponse(BaseModel):
    id: str
    user_id: str
    query_text: str
    answer: str
    policy_id: Optional[str]
    policy_version: Optional[str]
    is_cached: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- User History & Personal Analytics ---
class UserHistoryItem(BaseModel):
    id: str
    query_text: str
    decision: str
    is_cached_result: bool
    returned_answer: str
    provider_used: str
    policy_id: Optional[str]
    policy_version: Optional[str]
    source_citation: Optional[str]
    total_latency_ms: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserAnalyticsResponse(BaseModel):
    total_queries: int
    cache_hits: int
    cache_misses: int
    cache_hit_ratio: float
    avg_latency_ms: float
    frequently_accessed_topics: List[Dict[str, Any]]

# --- Cache Schemas ---
class CacheEntryCreate(BaseModel):
    question: str
    answer: str
    policy_id: str
    domain: str
    jurisdiction: Optional[str] = "INDIA"
    employee_category: Optional[str] = "ALL"
    numerical_limits: Optional[Dict[str, float]] = Field(default_factory=dict)
    is_verified: bool = True

class CacheEntryUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    policy_id: Optional[str] = None
    domain: Optional[str] = None
    jurisdiction: Optional[str] = None
    employee_category: Optional[str] = None
    numerical_limits: Optional[Dict[str, float]] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None

class CacheEntryResponse(BaseModel):
    id: str
    faiss_id: Optional[int]
    question: str
    answer: str
    policy_id: str
    policy_version: str
    domain: str
    jurisdiction: str
    employee_category: str
    numerical_limits: Dict[str, Any]
    is_verified: bool
    is_active: bool
    hit_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Policy Schemas ---
class PolicyCreate(BaseModel):
    policy_id: str
    name: str
    domain: str
    jurisdiction: Optional[str] = "INDIA"
    employee_category: Optional[str] = "ALL"
    content: str
    status: Optional[str] = "active"
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    jurisdiction: Optional[str] = None
    employee_category: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None

class PolicyResponse(BaseModel):
    id: str
    policy_id: str
    name: str
    domain: str
    jurisdiction: str
    employee_category: str
    current_version: str
    content: str
    status: str
    effective_date: Optional[datetime]
    expiry_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PolicyPreviewResponse(BaseModel):
    extracted_text: str
    detected_domain: str
    suggested_policy_id: str
    suggested_name: str
    jurisdiction: str
    employee_category: str
    total_characters: int
    clauses: List[str]

# --- Model Registry & Rollback Schemas ---
class ModelArtifactVersionResponse(BaseModel):
    id: str
    version_tag: str
    classifier_path: str
    calibrator_path: str
    faiss_index_path: str
    faiss_id_map_path: str
    selected_threshold: float
    target_fhr: float
    observed_fhr: Optional[float]
    upper_confidence_bound: Optional[float]
    sample_size: int
    metrics: Dict[str, Any]
    hyperparameters: Dict[str, Any]
    dataset_version: str
    is_active: bool
    created_by: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RollbackRequest(BaseModel):
    target_version_tag: str

class ModelSelectionRequest(BaseModel):
    model_name: str # "decision_tree", "logistic_regression", "knn"

# --- Synthetic Data Generation & Candidate Pair Schemas ---
class SyntheticGenerationRequest(BaseModel):
    policy_id: Optional[str] = None
    num_pairs_per_clause: int = 2

class CandidatePairCreate(BaseModel):
    q1: str
    q2: str
    label: int = Field(..., ge=0, le=1)
    group: str
    pair_type: str = "positive" # "positive", "negative_numeric", "negative_jurisdiction", "negative_category"

class CandidatePairResponse(BaseModel):
    id: Optional[str] = None
    q1: str
    q2: str
    label: int
    group: str
    pair_type: str
    is_approved: bool = False

# --- Settings & Dashboard ---
class SettingsUpdate(BaseModel):
    cache_threshold: Optional[float] = None
    min_cosine_similarity: Optional[float] = None
    top_k: Optional[int] = None
    target_fhr: Optional[float] = None
    confidence_level: Optional[float] = None
    fallback_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    grok_api_key: Optional[str] = None

class DashboardSummary(BaseModel):
    total_queries: int
    cache_hits: int
    cache_misses: int
    cache_hit_ratio: float
    avg_lookup_latency_ms: float
    avg_fallback_latency_ms: float
    estimated_calls_avoided: int
    estimated_cost_saved_usd: float
    estimated_cost_saved_inr: float
    active_threshold: float
    target_fhr: float
    observed_fhr: Optional[float]
    upper_confidence_bound: Optional[float]
    model_status: Dict[str, str]
    # Real Grok API & Token Consumption Metrics
    grok_invocations: int = 0
    total_tokens_consumed: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    actual_cost_usd: float = 0.0
    actual_cost_inr: float = 0.0
    cost_without_cache_usd: float = 0.0
    cost_without_cache_inr: float = 0.0
    percent_queries_avoided_llm: float = 0.0
    # Measurable Sustainability & Efficiency Metrics
    eligible_policy_queries: int = 0
    policy_cache_hit_rate: float = 0.0
    llm_calls_avoided: int = 0
    tokens_avoided: int = 0
    latency_reduction_percent: float = 0.0
    environmental_impact_status: str = "insufficient_data"
    # Granular Cache State vs Immutable Historical Events
    current_active_cache_entries: int = 0
    current_invalidated_cache_entries: int = 0
    total_historical_cache_hits: int = 0
    historical_cache_hit_rate: float = 0.0
    insufficient_evidence_queries: int = 0
    document_conflict_queries: int = 0
    pending_insufficient_questions_count: int = 0

# --- Insufficient Data Questions Schemas ---
class InsufficientDataQuestionResponse(BaseModel):
    id: str
    request_id: Optional[str] = None
    query_text: str
    normalized_query: str
    user_id: Optional[str] = None
    policy_scope: str
    retrieval_status: str
    reason: Optional[str] = None
    confidence_score: Optional[float] = None
    occurrence_count: int = 1
    first_asked_at: datetime
    last_asked_at: datetime
    status: str
    admin_notes: Optional[str] = None
    resolved_by_policy_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    log_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class InsufficientDataQuestionUpdate(BaseModel):
    status: Optional[str] = None  # "PENDING", "REVIEWED", "RESOLVED"
    admin_notes: Optional[str] = None

class InsufficientDataQuestionListResponse(BaseModel):
    items: List[InsufficientDataQuestionResponse]
    total: int
    pending_count: int
    reviewed_count: int
    resolved_count: int
