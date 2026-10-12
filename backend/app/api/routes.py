import io
import csv
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
import pypdf

from app.db.session import get_db
from app.core.config import settings
from app.models.entities import (
    CachedEntry, QueryAuditLog, Policy, PolicyVersion, ModelMetadata,
    ThresholdEvaluationRun, DatasetRecord
)
from app.schemas.api_schemas import (
    QueryRequest, QueryResponse, QueryCheckResponse,
    CacheEntryCreate, CacheEntryUpdate, CacheEntryResponse,
    PolicyCreate, PolicyUpdate, PolicyResponse,
    SettingsUpdate, DashboardSummary
)
from app.ml.cache_pipeline import cache_pipeline
from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.equivalence_classifier import equivalence_classifier
from app.ml.probability_calibration import probability_calibrator
from app.ml.query_clustering import query_clusterer
from app.ml.policy_validation import normalize_text, extract_policy_conditions
from app.ml.query_optimizer import optimize_user_query
from app.services.training_service import train_and_evaluate_all_models
from app.services.fallback_service import llm_service

router = APIRouter()

# 1. Health Endpoint
@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "company": "Kaveri Tech Solutions Pvt. Ltd. (Chennai & Coimbatore, Tamil Nadu)",
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

    # Cost savings: $0.002 per call, and INR 18.00 per call in India context
    cost_saved_usd = float(hits * 0.002)
    cost_saved_inr = float(hits * 18.00)

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
        estimated_cost_saved_usd=round(cost_saved_usd, 4),
        estimated_cost_saved_inr=round(cost_saved_inr, 2),
        active_threshold=round(float(active_tau), 3),
        target_fhr=settings.TARGET_FHR,
        observed_fhr=obs_fhr,
        upper_confidence_bound=ucb,
        model_status=status_dict
    )

GREETING_RESPONSE_TEXT = (
    "Hello! I am CacheMind, the enterprise AI policy assistant for Kaveri Tech Solutions "
    "(OMR Chennai & Tidel Park Coimbatore, Tamil Nadu).\n\n"
    "How can I assist you with corporate policies today? You can ask me about:\n"
    "• 🌴 **Tamil Nadu Leave & Festival Holidays** (18 Privilege Leaves, 12 Casual Leaves, Pongal holiday calendar)\n"
    "• 💻 **Hybrid Work & Broadband Reimbursement** (2 days/week WFH, INR 1,500/month internet reimbursement)\n"
    "• ✈️ **Domestic Travel Per Diem** (INR 3,500/day Tier-1 Chennai vs INR 2,500/day Tier-2 Coimbatore)\n"
    "• 🏥 **Group Medical Insurance** (INR 5,00,000 floater at Apollo, MIOT & Kauvery hospitals)\n"
    "• 🔒 **Enterprise IT & VPN Security Guidelines**"
)

# 3. Two-Stage Query Flow (User Experience):
# Step A: Check Cache in Background. If Miss -> Optimize query in background & ask confirmation if filler detected
@router.post("/query/check-or-optimize", response_model=QueryCheckResponse)
def check_or_optimize_query(req: QueryRequest, db: Session = Depends(get_db)):
    """
    1. Detects pure greetings (hi, hello) and returns natural enterprise assistance.
    2. Checks for existence/answer in the cache in background.
    3. If cache hit -> returns response directly.
    4. If cache miss:
       - Runs query optimizer in background.
       - If optimized, returns needs_confirmation=True with suggested prompt.
       - If not optimized (already clean), performs grounded search over company policies.
    """
    norm_query = normalize_text(req.query)
    if not norm_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Check for pure greeting first
    opt_info = optimize_user_query(req.query)
    if opt_info.get("is_pure_greeting"):
        return QueryCheckResponse(
            status="GREETING",
            is_cached=False,
            needs_confirmation=False,
            original_query=req.query,
            optimized_query=None,
            removed_filler=[],
            answer=GREETING_RESPONSE_TEXT,
            provider_used="enterprise_greeting_handler",
            lookup_latency_ms=1.5,
            total_latency_ms=2.5
        )

    # 1. Background cache lookup
    cache_result = cache_pipeline.process_query(
        db=db,
        query=req.query,
        domain_filter=req.domain
    )

    if cache_result.get("is_cached"):
        return QueryCheckResponse(
            status="HIT",
            is_cached=True,
            needs_confirmation=False,
            original_query=req.query,
            optimized_query=None,
            removed_filler=[],
            answer=cache_result["answer"],
            provider_used=cache_result["provider_used"],
            candidate=cache_result.get("candidate"),
            lookup_latency_ms=cache_result.get("lookup_latency_ms"),
            total_latency_ms=cache_result.get("total_latency_ms")
        )

    # 2. Cache Miss: Check if query contains conversational filler to optimize
    if opt_info["is_optimized"]:
        return QueryCheckResponse(
            status="NEEDS_CONFIRMATION",
            is_cached=False,
            needs_confirmation=True,
            original_query=req.query,
            optimized_query=opt_info["optimized_query"],
            removed_filler=opt_info["removed_filler"],
            answer=None,
            provider_used=None,
            lookup_latency_ms=cache_result.get("lookup_latency_ms"),
            total_latency_ms=cache_result.get("total_latency_ms")
        )

    # 3. If no optimization needed, return the grounded policy answer from the cache miss execution
    return QueryCheckResponse(
        status="CACHE_MISS",
        is_cached=False,
        needs_confirmation=False,
        original_query=req.query,
        optimized_query=None,
        removed_filler=[],
        answer=cache_result["answer"],
        provider_used=cache_result["provider_used"],
        candidate=cache_result.get("candidate"),
        lookup_latency_ms=cache_result.get("lookup_latency_ms"),
        total_latency_ms=cache_result.get("total_latency_ms")
    )

# Step B: Direct Execution (when user confirms optimized prompt or executes search)
@router.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest, db: Session = Depends(get_db)):
    opt_info = optimize_user_query(req.query)
    if opt_info.get("is_pure_greeting"):
        return QueryResponse(
            query=req.query,
            decision="GREETING",
            is_cached=False,
            answer=GREETING_RESPONSE_TEXT,
            provider_used="enterprise_greeting_handler",
            rejection_reasons=[],
            candidate=None,
            active_threshold=0.5,
            lookup_latency_ms=1.5,
            total_latency_ms=2.5
        )

    result = cache_pipeline.process_query(
        db=db,
        query=req.query,
        domain_filter=req.domain
    )
    return result

# 4. Company Policy Management (Admin)
@router.get("/policies", response_model=List[PolicyResponse])
def list_policies(db: Session = Depends(get_db)):
    return db.query(Policy).order_by(Policy.created_at.desc()).all()

@router.post("/policies", response_model=PolicyResponse)
def create_policy(p: PolicyCreate, db: Session = Depends(get_db)):
    existing = db.query(Policy).filter(Policy.policy_id == p.policy_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Policy with ID {p.policy_id} already exists.")

    new_pol = Policy(
        policy_id=p.policy_id,
        name=p.name,
        domain=p.domain.upper(),
        jurisdiction=p.jurisdiction or "INDIA",
        employee_category=p.employee_category or "ALL",
        current_version="1.0",
        content=p.content
    )
    db.add(new_pol)
    db.commit()

    # Add version record
    ver = PolicyVersion(
        policy_id=new_pol.policy_id,
        version="1.0",
        change_summary="Initial policy document uploaded by admin.",
        content=new_pol.content,
        is_active=True
    )
    db.add(ver)
    db.commit()
    db.refresh(new_pol)
    return new_pol

@router.put("/policies/{policy_id}", response_model=PolicyResponse)
def update_policy(policy_id: str, p: PolicyUpdate, db: Session = Depends(get_db)):
    pol = db.query(Policy).filter(Policy.policy_id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found.")

    if p.name is not None:
        pol.name = p.name
    if p.domain is not None:
        pol.domain = p.domain.upper()
    if p.jurisdiction is not None:
        pol.jurisdiction = p.jurisdiction.upper()
    if p.employee_category is not None:
        pol.employee_category = p.employee_category.upper()
    if p.content is not None:
        pol.content = p.content
        # Increment version
        try:
            curr_v = float(pol.current_version)
            pol.current_version = f"{curr_v + 0.1:.1f}"
        except Exception:
            pol.current_version = "1.1"

        ver = PolicyVersion(
            policy_id=pol.policy_id,
            version=pol.current_version,
            change_summary="Policy updated by admin.",
            content=pol.content,
            is_active=True
        )
        db.add(ver)

    db.commit()
    db.refresh(pol)
    return pol

@router.delete("/policies/{policy_id}")
def delete_policy(policy_id: str, db: Session = Depends(get_db)):
    pol = db.query(Policy).filter(Policy.policy_id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found.")
    db.delete(pol)
    db.commit()
    return {"message": f"Policy {policy_id} deleted successfully."}

# 5. File Upload for Policies (.txt and .pdf ONLY) - Model learns new data!
@router.post("/policies/upload")
async def upload_policy_file(
    file: UploadFile = File(...),
    domain: str = Form("HR"),
    jurisdiction: str = Form("INDIA"),
    employee_category: str = Form("ALL"),
    db: Session = Depends(get_db)
):
    """
    Accepts .txt and .pdf files ONLY.
    Extracts text, creates/updates policy, segments clauses, extracts Q&A pairs,
    encodes them into FAISS and cache database so the model learns the new data immediately.
    """
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext not in ["txt", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .txt and .pdf policy files are permitted."
        )

    file_bytes = await file.read()
    extracted_text = ""

    if ext == "txt":
        try:
            extracted_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = file_bytes.decode("latin-1", errors="ignore")
    elif ext == "pdf":
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for p in pdf_reader.pages:
                t = p.extract_text()
                if t:
                    pages_text.append(t)
            extracted_text = "\n\n".join(pages_text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF file: {str(e)}")

    clean_content = extracted_text.strip()
    if len(clean_content) < 20:
        raise HTTPException(status_code=400, detail="Uploaded file does not contain sufficient text content.")

    # Generate policy ID from filename
    clean_name = re.sub(r'[^a-zA-Z0-9]', '-', filename.rsplit('.', 1)[0]).upper()
    policy_id = f"TN-{domain.upper()}-{clean_name[:12]}"

    # Save or update policy
    existing_pol = db.query(Policy).filter(Policy.policy_id == policy_id).first()
    if existing_pol:
        existing_pol.content = clean_content
        existing_pol.domain = domain.upper()
        existing_pol.jurisdiction = jurisdiction.upper()
        existing_pol.employee_category = employee_category.upper()
        pol_obj = existing_pol
    else:
        pol_obj = Policy(
            policy_id=policy_id,
            name=f"{filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()} Policy",
            domain=domain.upper(),
            jurisdiction=jurisdiction.upper(),
            employee_category=employee_category.upper(),
            current_version="1.0",
            content=clean_content
        )
        db.add(pol_obj)
        db.commit()

        ver = PolicyVersion(
            policy_id=policy_id,
            version="1.0",
            change_summary=f"Uploaded from file {filename}",
            content=clean_content,
            is_active=True
        )
        db.add(ver)

    db.commit()

    # Automatically chunk into key clauses and learn into FAISS
    paragraphs = [p.strip() for p in clean_content.split("\n\n") if len(p.strip()) > 30]
    if not paragraphs:
        paragraphs = [p.strip() for p in clean_content.split("\n") if len(p.strip()) > 30]

    new_entries_indexed = 0
    for idx, clause in enumerate(paragraphs[:8]):  # Index top salient clauses
        # Formulate a natural question from clause
        first_sentence = clause.split(".")[0]
        q_text = f"What is the company policy regarding {first_sentence[:80]}?"
        norm_q = normalize_text(q_text)

        # Check existing
        existing_ce = db.query(CachedEntry).filter(CachedEntry.question == q_text).first()
        if not existing_ce:
            ce = CachedEntry(
                question=q_text,
                normalized_question=norm_q,
                answer=f"Under policy {policy_id} ({pol_obj.name}): {clause}",
                policy_id=policy_id,
                policy_version=pol_obj.current_version,
                domain=domain.upper(),
                jurisdiction=jurisdiction.upper(),
                employee_category=employee_category.upper(),
                numerical_limits={},
                is_verified=True,
                is_active=True,
                hit_count=0
            )
            db.add(ce)
            db.commit()
            db.refresh(ce)

            # Encode and add to FAISS
            emb = embedding_service.encode(norm_q, normalize=True)
            ce.faiss_id = faiss_service.add_vector(ce.id, emb)
            db.commit()
            new_entries_indexed += 1

    return {
        "status": "success",
        "message": f"Policy '{pol_obj.name}' ({policy_id}) successfully uploaded. Learned and indexed {new_entries_indexed} clauses into FAISS vector cache.",
        "policy_id": policy_id,
        "clauses_learned": new_entries_indexed,
        "total_characters": len(clean_content)
    }

# 6. Cache Explorer CRUD
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
        jurisdiction=entry.jurisdiction or "INDIA",
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

    # Reset faiss_id before rebuilding to prevent SQLite unique constraint violations
    db.query(CachedEntry).update({CachedEntry.faiss_id: None})
    db.commit()

    questions = [e.normalized_question for e in entries]
    ids = [e.id for e in entries]
    embs = embedding_service.encode(questions, normalize=True)

    count = faiss_service.rebuild_index(ids, embs)

    # Update faiss_ids in database
    for idx, e in enumerate(entries):
        e.faiss_id = idx
    db.commit()

    return {"message": f"Successfully rebuilt FAISS index with {count} vectors.", "vector_count": count}

# 7. ML Models Status & Actions
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

# 8. Evaluation & Thresholds
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

# 9. Query Analytics & Clusters
@router.get("/analytics/clusters")
def get_query_clusters(n_clusters: int = Query(3, ge=2, le=10), db: Session = Depends(get_db)):
    entries = db.query(CachedEntry).filter(CachedEntry.is_active == True).all()
    questions = [e.question for e in entries]
    if len(questions) < 2:
        return {"status": "insufficient_data", "message": "At least 2 cached queries required for clustering."}

    embs = embedding_service.encode([e.normalized_question for e in entries], normalize=True)
    res = query_clusterer.cluster_queries(questions, embs, n_clusters=n_clusters)
    return res

# 10. Audit Logs
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

# 11. Settings
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
        "openai_api_key_configured": bool(settings.OPENAI_API_KEY),
        "grok_api_key_configured": bool(getattr(settings, "GROK_API_KEY", "")),
        "company_name": "Kaveri Tech Solutions Pvt. Ltd.",
        "location": "OMR Chennai & Tidel Park Coimbatore, Tamil Nadu, India"
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
    if updates.grok_api_key is not None:
        settings.GROK_API_KEY = updates.grok_api_key

    return {"status": "success", "message": "Settings updated."}

# 12. Datasets List
@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    return db.query(DatasetRecord).all()
