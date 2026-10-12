import csv
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.config import settings
from app.models.entities import (
    CachedEntry, QueryAuditLog, Policy, ModelMetadata,
    ThresholdEvaluationRun, DatasetRecord
)
from app.schemas.api_schemas import (
    QueryRequest, QueryResponse, CacheEntryCreate,
    CacheEntryUpdate, CacheEntryResponse, SettingsUpdate,
    DashboardSummary
)
from app.ml.cache_pipeline import cache_pipeline
from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.equivalence_classifier import equivalence_classifier
from app.ml.probability_calibration import probability_calibrator
from app.ml.query_clustering import query_clusterer
from app.ml.policy_validation import normalize_text, extract_policy_conditions
from app.services.training_service import train_and_evaluate_all_models

router = APIRouter()

# 1. Health Endpoint
@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "embedding_model_ready": embedding_service.is_ready,
        "classifier_fitted": equivalence_classifier.is_fitted,
        "calibrator_fitted": probability_calibrator.is_fitted,
        "faiss_vector_count": faiss_service.total_vectors()
    }

# 2. Dashboard Summary
@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total = db.query(QueryAuditLog).count()
    hits = db.query(QueryAuditLog).filter(QueryAuditLog.decision == "HIT").count()
    misses = total - hits
    hit_ratio = float(hits / total) if total > 0 else 0.0

    # Latencies
    avg_lookup = db.query(func.avg(QueryAuditLog.lookup_latency_ms)).filter(QueryAuditLog.decision == "HIT").scalar() or 0.0
    avg_fallback = db.query(func.avg(QueryAuditLog.total_latency_ms)).filter(QueryAuditLog.decision != "HIT").scalar() or 0.0

    # Cost savings (estimated $0.002 per LLM call avoided)
    cost_saved = float(hits * 0.002)

    # Active threshold evaluation
    active_eval = db.query(ThresholdEvaluationRun).filter(ThresholdEvaluationRun.is_active == True).order_by(ThresholdEvaluationRun.created_at.desc()).first()

    active_tau = active_eval.selected_threshold if active_eval else settings.DEFAULT_CACHE_THRESHOLD
    obs_fhr = active_eval.observed_fhr if active_eval else None
    ucb = active_eval.upper_confidence_bound if active_eval else None

    # Model statuses
    models = db.query(ModelMetadata).all()
    status_dict = {m.model_name: m.status for m in models}
    status_dict["embedding_transformer"] = "ready" if embedding_service.is_ready else "error"
    status_dict["faiss_index"] = "ready" if faiss_service.total_vectors() > 0 else "empty"

    return DashboardSummary(
        total_queries=total,
        cache_hits=hits,
        cache_misses=misses,
        cache_hit_ratio=round(hit_ratio, 4),
        avg_lookup_latency_ms=round(float(avg_lookup), 2),
        avg_fallback_latency_ms=round(float(avg_fallback), 2),
        estimated_calls_avoided=hits,
        estimated_cost_saved_usd=round(cost_saved, 4),
        active_threshold=round(float(active_tau), 3),
        target_fhr=settings.TARGET_FHR,
        observed_fhr=obs_fhr,
        upper_confidence_bound=ucb,
        model_status=status_dict
    )

# 3. Query Playground Endpoint
@router.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest, db: Session = Depends(get_db)):
    result = cache_pipeline.process_query(
        db=db,
        query=req.query,
        domain_filter=req.domain
    )
    return result

# 4. Cache Explorer CRUD
@router.get("/cache", response_model=List[CacheEntryResponse])
def list_cache_entries(
    domain: Optional[str] = None,
    verified_only: bool = False,
    db: Session = Depends(get_db)
):
    q = db.query(CachedEntry).filter(CachedEntry.is_active == True)
    if domain:
        q = q.filter(CachedEntry.domain == domain.upper())
    if verified_only:
        q = q.filter(CachedEntry.is_verified == True)
    return q.order_by(CachedEntry.created_at.desc()).all()

@router.post("/cache", response_model=CacheEntryResponse)
def create_cache_entry(entry: CacheEntryCreate, db: Session = Depends(get_db)):
    norm_q = normalize_text(entry.question)
    cached_obj = CachedEntry(
        question=entry.question,
        normalized_question=norm_q,
        answer=entry.answer,
        policy_id=entry.policy_id,
        domain=entry.domain.upper(),
        jurisdiction=entry.jurisdiction or "GLOBAL",
        employee_category=entry.employee_category or "ALL",
        numerical_limits=entry.numerical_limits or {},
        is_verified=entry.is_verified,
        is_active=True
    )
    db.add(cached_obj)
    db.commit()
    db.refresh(cached_obj)

    # Encode and index in FAISS
    emb = embedding_service.encode(norm_q, normalize=True)
    cached_obj.faiss_id = faiss_service.add_vector(cached_obj.id, emb)
    db.commit()

    return cached_obj

@router.patch("/cache/{entry_id}", response_model=CacheEntryResponse)
def update_cache_entry(entry_id: str, update: CacheEntryUpdate, db: Session = Depends(get_db)):
    obj = db.query(CachedEntry).filter(CachedEntry.id == entry_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Cache entry not found.")

    for k, v in update.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
        
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/cache/{entry_id}")
def delete_cache_entry(entry_id: str, db: Session = Depends(get_db)):
    obj = db.query(CachedEntry).filter(CachedEntry.id == entry_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Cache entry not found.")
    obj.is_active = False
    db.commit()
    return {"message": "Cache entry deactivated successfully."}

@router.post("/cache/rebuild-index")
def rebuild_cache_index(db: Session = Depends(get_db)):
    entries = db.query(CachedEntry).filter(
        CachedEntry.is_active == True,
        CachedEntry.is_verified == True
    ).all()

    if not entries:
        faiss_service.rebuild_index([], embedding_service.encode([]))
        return {"message": "Index rebuilt with 0 vectors.", "vector_count": 0}

    questions = [e.normalized_question for e in entries]
    ids = [e.id for e in entries]
    embs = embedding_service.encode(questions, normalize=True)

    count = faiss_service.rebuild_index(ids, embs)

    # Update faiss_ids in database
    for idx, e in enumerate(entries):
        e.faiss_id = idx
    db.commit()

    return {"message": f"Successfully rebuilt FAISS index with {count} vectors.", "vector_count": count}

# 5. ML Models Status & Actions
@router.get("/models/status")
def get_models_status(db: Session = Depends(get_db)):
    metas = db.query(ModelMetadata).all()
    models_info = {m.model_name: {
        "status": m.status,
        "metrics": m.metrics,
        "hyperparameters": m.hyperparameters,
        "last_trained_at": m.last_trained_at
    } for m in metas}

    return {
        "embedding_transformer": embedding_service.model_info,
        "faiss_index": {
            "total_vectors": faiss_service.total_vectors(),
            "dimension": settings.EMBEDDING_DIM,
            "metric": "InnerProduct (Cosine)"
        },
        "classifier": models_info.get("equivalence_classifier", equivalence_classifier.metadata),
        "calibrator": models_info.get("probability_calibrator", probability_calibrator.metadata)
    }

@router.post("/models/train")
def train_models(db: Session = Depends(get_db)):
    try:
        results = train_and_evaluate_all_models(db)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

# 6. Evaluation & Thresholds
@router.get("/evaluation/results")
def get_evaluation_results(db: Session = Depends(get_db)):
    run = db.query(ThresholdEvaluationRun).order_by(ThresholdEvaluationRun.created_at.desc()).first()
    if not run:
        return {"status": "not_evaluated", "message": "No evaluation runs performed yet."}
    return {
        "id": run.id,
        "target_fhr": run.target_fhr,
        "confidence_level": run.confidence_level,
        "selected_threshold": run.selected_threshold,
        "status": run.status,
        "sample_size": run.sample_size,
        "false_hits": run.false_hits,
        "observed_fhr": run.observed_fhr,
        "upper_confidence_bound": run.upper_confidence_bound,
        "results": run.detailed_results,
        "created_at": run.created_at,
        "is_active": run.is_active
    }

@router.post("/evaluation/activate-threshold")
def activate_threshold(threshold: float = Query(...), db: Session = Depends(get_db)):
    run = db.query(ThresholdEvaluationRun).order_by(ThresholdEvaluationRun.created_at.desc()).first()
    if run:
        run.selected_threshold = threshold
        run.is_active = True
        db.commit()
    return {"status": "activated", "active_threshold": threshold}

# 7. Query Analytics & Clusters
@router.get("/analytics/clusters")
def get_query_clusters(n_clusters: int = Query(3, ge=2, le=10), db: Session = Depends(get_db)):
    entries = db.query(CachedEntry).filter(CachedEntry.is_active == True).all()
    questions = [e.question for e in entries]
    if len(questions) < 2:
        return {"status": "insufficient_data", "message": "At least 2 cached queries required for clustering."}

    embs = embedding_service.encode([e.normalized_question for e in entries], normalize=True)
    res = query_clusterer.cluster_queries(questions, embs, n_clusters=n_clusters)
    return res

# 8. Audit Logs
@router.get("/audit-logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    decision: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(QueryAuditLog)
    if decision:
        q = q.filter(QueryAuditLog.decision == decision)
    logs = q.order_by(QueryAuditLog.created_at.desc()).limit(limit).all()
    return logs

# 9. Settings
@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    active_eval = db.query(ThresholdEvaluationRun).filter(ThresholdEvaluationRun.is_active == True).order_by(ThresholdEvaluationRun.created_at.desc()).first()
    active_tau = active_eval.selected_threshold if active_eval else settings.DEFAULT_CACHE_THRESHOLD

    return {
        "cache_threshold": active_tau,
        "min_cosine_similarity": settings.DEFAULT_MIN_COSINE_SIM,
        "top_k": settings.DEFAULT_TOP_K,
        "target_fhr": settings.TARGET_FHR,
        "confidence_level": settings.CONFIDENCE_LEVEL,
        "fallback_provider": settings.FALLBACK_PROVIDER,
        "openai_model": settings.OPENAI_MODEL,
        "openai_api_key_configured": bool(settings.OPENAI_API_KEY)
    }

@router.patch("/settings")
def update_settings(updates: SettingsUpdate):
    if updates.cache_threshold is not None:
        settings.DEFAULT_CACHE_THRESHOLD = updates.cache_threshold
    if updates.min_cosine_similarity is not None:
        settings.DEFAULT_MIN_COSINE_SIM = updates.min_cosine_similarity
    if updates.top_k is not None:
        settings.DEFAULT_TOP_K = updates.top_k
    if updates.target_fhr is not None:
        settings.TARGET_FHR = updates.target_fhr
    if updates.confidence_level is not None:
        settings.CONFIDENCE_LEVEL = updates.confidence_level
    if updates.fallback_provider is not None:
        settings.FALLBACK_PROVIDER = updates.fallback_provider
    if updates.openai_api_key is not None:
        settings.OPENAI_API_KEY = updates.openai_api_key
    if updates.openai_model is not None:
        settings.OPENAI_MODEL = updates.openai_model

    return {"status": "success", "message": "Settings updated."}

# 10. Datasets List
@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    return db.query(DatasetRecord).all()
