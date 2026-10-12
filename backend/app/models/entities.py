import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    policy_id = Column(String, unique=True, index=True, nullable=False) # e.g. "HR-LEAVE-01"
    name = Column(String, nullable=False)
    domain = Column(String, index=True, nullable=False) # HR, IT, FINANCE
    jurisdiction = Column(String, default="GLOBAL") # US, INDIA, UK, GLOBAL
    employee_category = Column(String, default="ALL") # FULL_TIME, CONTRACTOR, INTERN, ALL
    current_version = Column(String, default="1.0")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan")
    cached_entries = relationship("CachedEntry", back_populates="policy")


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    policy_id = Column(String, ForeignKey("policies.policy_id"), nullable=False)
    version = Column(String, nullable=False)
    change_summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    effective_date = Column(DateTime, default=datetime.datetime.utcnow)
    
    policy = relationship("Policy", back_populates="versions")


class CachedEntry(Base):
    __tablename__ = "cached_entries"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    faiss_id = Column(Integer, unique=True, index=True, nullable=True) # ID mapping to FAISS vector index
    question = Column(Text, nullable=False)
    normalized_question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    
    policy_id = Column(String, ForeignKey("policies.policy_id"), nullable=False)
    policy_version = Column(String, nullable=False, default="1.0")
    domain = Column(String, index=True, nullable=False)
    
    # Structured condition metadata
    jurisdiction = Column(String, default="GLOBAL")
    employee_category = Column(String, default="ALL")
    numerical_limits = Column(JSON, default=dict) # e.g. {"days": 20, "amount": 1000}
    effective_period = Column(String, nullable=True)
    exceptions = Column(JSON, default=list)
    
    is_verified = Column(Boolean, default=True) # Must be True for cache reuse
    is_active = Column(Boolean, default=True)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    policy = relationship("Policy", back_populates="cached_entries")


class QueryAuditLog(Base):
    __tablename__ = "query_audit_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    query_text = Column(Text, nullable=False)
    domain_filter = Column(String, nullable=True)
    
    decision = Column(String, nullable=False) # "HIT", "REJECTED_POLICY_MISMATCH", "REJECTED_LOW_SCORE", "REJECTED_SAFETY", "FALLBACK_MOCK", "FALLBACK_LLM"
    rejection_reasons = Column(JSON, default=list)
    
    candidate_cache_id = Column(String, ForeignKey("cached_entries.id"), nullable=True)
    candidate_faiss_id = Column(Integer, nullable=True)
    candidate_question = Column(Text, nullable=True)
    
    # ML Scoring Metrics
    cosine_similarity = Column(Float, nullable=True)
    classifier_score = Column(Float, nullable=True)
    calibrated_probability = Column(Float, nullable=True)
    applied_threshold = Column(Float, nullable=True)
    
    # Deterministic checks
    policy_condition_passed = Column(Boolean, default=False)
    condition_mismatches = Column(JSON, default=list)
    
    returned_answer = Column(Text, nullable=False)
    is_cached_result = Column(Boolean, default=False)
    provider_used = Column(String, default="cache") # "cache", "local_mock", "openai"
    
    lookup_latency_ms = Column(Float, default=0.0)
    total_latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    model_name = Column(String, unique=True, nullable=False) # "equivalence_classifier", "probability_calibrator", "query_clusterer", "faiss_index"
    version = Column(String, default="1.0.0")
    status = Column(String, default="uninitialized") # "ready", "training", "error", "uninitialized"
    artifact_path = Column(String, nullable=True)
    hyperparameters = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    last_trained_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class ThresholdEvaluationRun(Base):
    __tablename__ = "threshold_evaluation_runs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    target_fhr = Column(Float, default=0.01) # 1% target
    confidence_level = Column(Float, default=0.95)
    selected_threshold = Column(Float, nullable=True)
    status = Column(String, default="completed") # "passed", "conservative_fallback", "insufficient_data"
    
    sample_size = Column(Integer, default=0)
    false_hits = Column(Integer, default=0)
    observed_fhr = Column(Float, default=0.0)
    upper_confidence_bound = Column(Float, default=0.0)
    
    detailed_results = Column(JSON, default=list) # List of candidate thresholds evaluated with FHR and UCB
    dataset_version = Column(String, default="v1.0")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=False)


class DatasetRecord(Base):
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    file_path = Column(String, nullable=False)
    row_count = Column(Integer, default=0)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    split_info = Column(JSON, default=dict) # {"train": 60, "cal": 20, "val": 10, "test": 10}
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
