import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="USER", index=True, nullable=False) # "USER", "ADMIN"
    full_name = Column(String, default="")
    department = Column(String, default="General")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")


class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    policy_id = Column(String, unique=True, index=True, nullable=False) # e.g. "TN-HR-LEAVE-01"
    name = Column(String, nullable=False)
    domain = Column(String, index=True, nullable=False) # HR, IT, FINANCE
    jurisdiction = Column(String, default="INDIA") # INDIA, US, UK, GLOBAL
    employee_category = Column(String, default="ALL") # FULL_TIME, CONTRACTOR, INTERN, ALL
    current_version = Column(String, default="1.0")
    content = Column(Text, nullable=False)
    content_hash = Column(String, nullable=True) # SHA-256 content hash for granular change detection
    parsed_sections = Column(JSON, default=list) # Section breakdown with headings, text, and section hashes
    status = Column(String, default="active") # "active", "obsolete", "draft"
    effective_date = Column(DateTime, default=datetime.datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
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
    content_hash = Column(String, nullable=True)
    parsed_sections = Column(JSON, default=list)
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
    
    # Granular Dependency Tracking Metadata
    source_section_ids = Column(JSON, default=list) # List of exact section/chunk IDs: ["TN-HR-LEAVE-01-sec-01"]
    source_content_hashes = Column(JSON, default=dict) # Map: {section_id: content_hash} at time of caching
    source_citation = Column(Text, nullable=True)
    last_validated_at = Column(DateTime, default=datetime.datetime.utcnow)
    invalidation_reason = Column(String, nullable=True)
    
    # Structured condition metadata
    jurisdiction = Column(String, default="INDIA")
    employee_category = Column(String, default="ALL")
    numerical_limits = Column(JSON, default=dict) # e.g. {"days": 18, "amount": 1000}
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
    request_id = Column(String, nullable=True, index=True) # Idempotent request identifier
    query_category = Column(String, default="POLICY", index=True) # "POLICY", "GREETING", "TECHNICAL_ERROR"
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    
    query_text = Column(Text, nullable=False)
    domain_filter = Column(String, nullable=True)
    
    decision = Column(String, nullable=False) # "HIT", "CACHE_MISS", "INSUFFICIENT_EVIDENCE", "DOCUMENT_CONFLICT", "GREETING", "ERROR"
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
    
    # Policy Citation & Version
    policy_id = Column(String, nullable=True)
    policy_version = Column(String, nullable=True)
    source_section_ids = Column(JSON, default=list)
    source_citation = Column(Text, nullable=True)
    source_document = Column(String, nullable=True)
    error_reason = Column(String, nullable=True)
    
    returned_answer = Column(Text, nullable=False)
    is_cached_result = Column(Boolean, default=False)
    provider_used = Column(String, default="cache") # "cache", "grounded_company_policy_engine", "openai", "grok"
    
    # Grok API & Cost Tracking Metrics
    grok_invoked = Column(Boolean, default=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    supporting_evidence_references = Column(JSON, default=list)
    validation_status = Column(String, default="passed") # "passed", "insufficient_evidence", "conflict", "error"
    
    lookup_latency_ms = Column(Float, default=0.0)
    total_latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class InsufficientDataQuestion(Base):
    """
    Persistent store for genuine unanswered policy questions.
    Provides administrators with visibility into policy gaps, recurrence frequency,
    and automatic resolution when updated policies cover previously missing evidence.
    """
    __tablename__ = "insufficient_data_questions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    policy_scope = Column(String, default="ALL") # e.g. "HR", "FINANCE", "TN-HR-LEAVE-01"
    
    retrieval_status = Column(String, default="INSUFFICIENT_EVIDENCE", index=True)
    # "INSUFFICIENT_EVIDENCE", "DOCUMENT_CONFLICT", "RETRIEVAL_ERROR", "LLM_ERROR"
    reason = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True) # Top similarity score
    
    occurrence_count = Column(Integer, default=1)
    first_asked_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_asked_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    status = Column(String, default="PENDING", index=True) # "PENDING", "REVIEWED", "RESOLVED"
    admin_notes = Column(Text, nullable=True)
    resolved_by_policy_id = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    log_id = Column(String, ForeignKey("query_audit_logs.id", ondelete="SET NULL"), nullable=True)


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    log_id = Column(String, ForeignKey("query_audit_logs.id", ondelete="SET NULL"), nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    rating = Column(String, nullable=False) # "helpful", "not_helpful"
    comment = Column(Text, nullable=True)
    is_reported_incorrect = Column(Boolean, default=False)
    report_reason = Column(String, nullable=True)
    status = Column(String, default="pending") # "pending", "reviewed", "resolved"
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="feedbacks")


class UserFavorite(Base):
    __tablename__ = "user_favorites"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    query_text = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    policy_id = Column(String, nullable=True)
    policy_version = Column(String, nullable=True)
    is_cached = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="favorites")


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


class ModelArtifactVersion(Base):
    """
    Model Registry Table: Tracks versioned snapshots of ML pipeline artifacts
    for safe atomic publication, audit tracking, and instantaneous rollback.
    """
    __tablename__ = "model_artifact_versions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    version_tag = Column(String, unique=True, index=True, nullable=False) # e.g. "v1.0.0", "v1.0.1"
    classifier_path = Column(String, nullable=False)
    calibrator_path = Column(String, nullable=False)
    faiss_index_path = Column(String, nullable=False)
    faiss_id_map_path = Column(String, nullable=False)
    selected_threshold = Column(Float, nullable=False, default=0.50)
    target_fhr = Column(Float, nullable=False, default=0.01)
    observed_fhr = Column(Float, nullable=True)
    upper_confidence_bound = Column(Float, nullable=True)
    sample_size = Column(Integer, default=0)
    metrics = Column(JSON, default=dict)
    hyperparameters = Column(JSON, default=dict)
    dataset_version = Column(String, default="v1.0")
    is_active = Column(Boolean, default=False, index=True)
    created_by = Column(String, default="administrator")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


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
