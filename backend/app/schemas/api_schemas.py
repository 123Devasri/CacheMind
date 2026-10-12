from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Query schemas
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User question to look up")
    domain: Optional[str] = Field(None, description="Optional domain filter (HR, IT, FINANCE)")

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
    decision: str # "HIT", "CACHE_MISS", "REJECTED_EMPTY_QUERY"
    is_cached: bool
    answer: str
    provider_used: str
    rejection_reasons: List[str]
    candidate: Optional[CandidateInfo] = None
    active_threshold: float
    lookup_latency_ms: float
    total_latency_ms: float
    log_id: Optional[str] = None

# Cache schemas
class CacheEntryCreate(BaseModel):
    question: str
    answer: str
    policy_id: str
    domain: str
    jurisdiction: Optional[str] = "GLOBAL"
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
    
    class Config:
        from_attributes = True

# Settings schema
class SettingsUpdate(BaseModel):
    cache_threshold: Optional[float] = None
    min_cosine_similarity: Optional[float] = None
    top_k: Optional[int] = None
    target_fhr: Optional[float] = None
    confidence_level: Optional[float] = None
    fallback_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None

# Dashboard summary schema
class DashboardSummary(BaseModel):
    total_queries: int
    cache_hits: int
    cache_misses: int
    cache_hit_ratio: float
    avg_lookup_latency_ms: float
    avg_fallback_latency_ms: float
    estimated_calls_avoided: int
    estimated_cost_saved_usd: float
    active_threshold: float
    target_fhr: float
    observed_fhr: Optional[float]
    upper_confidence_bound: Optional[float]
    model_status: Dict[str, str]
