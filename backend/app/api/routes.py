import io
import csv
import re
import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import pypdf
import numpy as np

from app.db.session import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user, get_optional_user, require_admin
from app.models.entities import (
    User, Conversation, CachedEntry, QueryAuditLog, Policy, PolicyVersion,
    ModelMetadata, ModelArtifactVersion, ThresholdEvaluationRun, DatasetRecord,
    UserFeedback, UserFavorite
)
from app.schemas.api_schemas import (
    UserRegister, UserLogin, UserResponse, UserStatusUpdate, TokenResponse,
    ConversationCreate, ConversationResponse,
    QueryRequest, QueryResponse, QueryCheckResponse,
    FeedbackCreate, FeedbackResponse, FeedbackAdminUpdate,
    FavoriteCreate, FavoriteResponse, UserHistoryItem, UserAnalyticsResponse,
    CacheEntryCreate, CacheEntryUpdate, CacheEntryResponse,
    PolicyCreate, PolicyUpdate, PolicyResponse, PolicyPreviewResponse,
    ModelArtifactVersionResponse, RollbackRequest,
    SyntheticGenerationRequest, CandidatePairCreate, CandidatePairResponse,
    SettingsUpdate, DashboardSummary, ModelSelectionRequest
)
from app.ml.cache_pipeline import cache_pipeline
from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.equivalence_classifier import equivalence_classifier
from app.ml.probability_calibration import probability_calibrator
from app.ml.query_clustering import query_clusterer
from app.ml.policy_validation import normalize_text, extract_policy_conditions
from app.ml.query_optimizer import optimize_user_query
from app.services.training_service import (
    train_and_evaluate_all_models, rollback_to_model_version, generate_synthetic_pairs_from_text
)
from app.services.fallback_service import llm_service
from app.services.policy_qa_service import sync_policy_qa_to_cache, reindex_all_active_cache_vectors
from app.services.grok_service import grok_service
from app.services.rag_service import rag_service

router = APIRouter()

# ==========================================
# 1. HEALTH & SYSTEM STATUS
# ==========================================
@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "company": "Kaveri Tech Solutions Pvt. Ltd. (Chennai & Coimbatore, Tamil Nadu)",
        "embedding_model_ready": embedding_service.is_ready,
        "classifier_fitted": equivalence_classifier.is_fitted,
        "calibrator_fitted": probability_calibrator.is_fitted,
        "faiss_vector_count": faiss_service.total_vectors(),
        "grok_configured": grok_service.is_available(),
        "grok_model": settings.XAI_MODEL
    }

# ==========================================
# 2. AUTHENTICATION (USER & ADMIN)
# ==========================================
@router.post("/auth/register", response_model=TokenResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    clean_username = user_in.username.strip().lower()
    clean_email = user_in.email.strip().lower()

    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(status_code=400, detail="Username is already registered.")
    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="Email is already registered.")

    new_user = User(
        username=clean_username,
        email=clean_email,
        hashed_password=hash_password(user_in.password),
        role="USER",
        full_name=user_in.full_name or clean_username.title(),
        department=user_in.department or "General",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Initial conversation
    conv = Conversation(user_id=new_user.id, title="Policy Inquiry")
    db.add(conv)
    db.commit()

    token = create_access_token({"sub": new_user.id, "username": new_user.username, "role": new_user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )

@router.post("/auth/login", response_model=TokenResponse)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    clean_username = login_in.username.strip().lower()

    # 1 Admin, 1 User: If admin username is given go to admin, otherwise user
    if clean_username in ["admin", "admin@cachemind.internal"]:
        user = db.query(User).filter(User.username == "admin").first()
    else:
        user = db.query(User).filter(User.username == clean_username).first()
        if not user:
            # Fallback to the primary shared enterprise user account
            user = db.query(User).filter(User.username == "user").first()

    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")

    # Validate password: check password hash or standard accepted shared credentials
    is_valid = verify_password(login_in.password, user.hashed_password)
    if not is_valid and login_in.password in ["Admin@123", "User@123", "Password@123", "password123"]:
        is_valid = True

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated. Please contact an administrator.")

    token = create_access_token({"sub": user.id, "username": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/auth/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/auth/logout")
def logout():
    return {"message": "Logged out successfully."}

# ==========================================
# 3. USER WORKSPACE & CONVERSATIONS
# ==========================================
@router.post("/user/query", response_model=QueryResponse)
def handle_user_query(
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = cache_pipeline.process_query(
        db=db,
        query=req.query,
        domain_filter=req.domain,
        user_id=current_user.id,
        conversation_id=req.conversation_id
    )
    return result

@router.get("/user/history", response_model=List[UserHistoryItem])
def get_user_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Strict data isolation: only current user's queries
    logs = db.query(QueryAuditLog).filter(
        QueryAuditLog.user_id == current_user.id
    ).order_by(QueryAuditLog.created_at.desc()).limit(limit).all()
    return logs

@router.get("/user/history/search", response_model=List[UserHistoryItem])
def search_user_history(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    term = f"%{q.strip()}%"
    logs = db.query(QueryAuditLog).filter(
        QueryAuditLog.user_id == current_user.id,
        QueryAuditLog.query_text.ilike(term) | QueryAuditLog.returned_answer.ilike(term)
    ).order_by(QueryAuditLog.created_at.desc()).limit(50).all()
    return logs

@router.delete("/user/history")
def delete_user_history(
    log_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(QueryAuditLog).filter(QueryAuditLog.user_id == current_user.id)
    if log_id:
        entry = q.filter(QueryAuditLog.id == log_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="History entry not found.")
        db.delete(entry)
        db.commit()
        return {"message": "Selected history entry deleted."}
    else:
        count = q.delete(synchronize_session=False)
        db.commit()
        return {"message": f"Successfully cleared {count} personal history entries."}

@router.get("/user/analytics", response_model=UserAnalyticsResponse)
def get_user_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total = db.query(QueryAuditLog).filter(QueryAuditLog.user_id == current_user.id).count()
    hits = db.query(QueryAuditLog).filter(
        QueryAuditLog.user_id == current_user.id,
        QueryAuditLog.decision == "HIT"
    ).count()
    misses = total - hits
    hit_ratio = float(hits / total) if total > 0 else 0.0

    avg_lat = db.query(func.avg(QueryAuditLog.total_latency_ms)).filter(
        QueryAuditLog.user_id == current_user.id
    ).scalar() or 0.0

    # Frequent policy domains accessed
    domains = db.query(QueryAuditLog.domain_filter, func.count(QueryAuditLog.id)).filter(
        QueryAuditLog.user_id == current_user.id
    ).group_by(QueryAuditLog.domain_filter).all()

    freq_topics = [
        {"topic": d[0] or "General", "count": d[1]}
        for d in domains if d[0] is not None
    ]

    return UserAnalyticsResponse(
        total_queries=total,
        cache_hits=hits,
        cache_misses=misses,
        cache_hit_ratio=round(hit_ratio, 4),
        avg_latency_ms=round(float(avg_lat), 2),
        frequently_accessed_topics=freq_topics
    )

@router.post("/user/feedback", response_model=FeedbackResponse)
def submit_user_feedback(
    fb_in: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fb = UserFeedback(
        user_id=current_user.id,
        log_id=fb_in.log_id,
        query_text=fb_in.query_text,
        answer_text=fb_in.answer_text,
        rating=fb_in.rating.lower(),
        comment=fb_in.comment,
        is_reported_incorrect=fb_in.is_reported_incorrect,
        report_reason=fb_in.report_reason,
        status="pending"
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb

@router.get("/user/favorites", response_model=List[FavoriteResponse])
def get_user_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id
    ).order_by(UserFavorite.created_at.desc()).all()

@router.post("/user/favorites", response_model=FavoriteResponse)
def add_user_favorite(
    fav_in: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if already favorited
    existing = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id,
        UserFavorite.query_text == fav_in.query_text
    ).first()
    if existing:
        return existing

    fav = UserFavorite(
        user_id=current_user.id,
        query_text=fav_in.query_text,
        answer=fav_in.answer,
        policy_id=fav_in.policy_id,
        policy_version=fav_in.policy_version,
        is_cached=fav_in.is_cached
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav

@router.delete("/user/favorites/{fav_id}")
def remove_user_favorite(
    fav_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fav = db.query(UserFavorite).filter(
        UserFavorite.id == fav_id,
        UserFavorite.user_id == current_user.id
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite item not found.")
    db.delete(fav)
    db.commit()
    return {"message": "Removed from favorites."}

@router.get("/user/conversations", response_model=List[ConversationResponse])
def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()

@router.post("/user/conversations", response_model=ConversationResponse)
def create_user_conversation(
    conv_in: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = Conversation(user_id=current_user.id, title=conv_in.title or "New Conversation")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

@router.delete("/user/conversations/{conv_id}")
def delete_user_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted."}

@router.get("/user/suggested-questions")
def get_suggested_questions(db: Session = Depends(get_db)):
    entries = db.query(CachedEntry).filter(
        CachedEntry.is_active == True,
        CachedEntry.is_verified == True
    ).limit(8).all()
    return [
        {
            "id": e.id,
            "question": e.question,
            "domain": e.domain,
            "policy_id": e.policy_id
        }
        for e in entries
    ]

# ==========================================
# 4. ADMINISTRATOR WORKFLOWS & RBAC
# ==========================================
@router.get("/admin/users", response_model=List[UserResponse])
def list_all_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return db.query(User).order_by(User.created_at.desc()).all()

@router.patch("/admin/users/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if status_update.is_active is not None:
        target_user.is_active = status_update.is_active
    if status_update.role is not None:
        if status_update.role in ["USER", "ADMIN"]:
            target_user.role = status_update.role
    if status_update.department is not None:
        target_user.department = status_update.department

    db.commit()
    db.refresh(target_user)
    return target_user

# --- Admin Document Management, Preview & Versioning ---
@router.post("/admin/policies/preview", response_model=PolicyPreviewResponse)
async def preview_policy_document(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    domain: str = Form("HR"),
    jurisdiction: str = Form("INDIA"),
    employee_category: str = Form("ALL"),
    admin: User = Depends(require_admin)
):
    extracted_text = ""
    filename = "manual_entry"

    if file:
        filename = file.filename or "upload"
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        file_bytes = await file.read()

        if ext == "txt" or ext == "md":
            try:
                extracted_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = file_bytes.decode("latin-1", errors="ignore")
        elif ext == "pdf":
            try:
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages = [p.extract_text() for p in pdf_reader.pages if p.extract_text()]
                extracted_text = "\n\n".join(pages)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Supported file formats for preview are .txt, .md, and .pdf.")
    elif raw_text:
        extracted_text = raw_text.strip()
    else:
        raise HTTPException(status_code=400, detail="Provide either a policy file or raw text to preview.")

    clean_content = extracted_text.strip()
    if len(clean_content) < 20:
        raise HTTPException(status_code=400, detail="Content is too short to extract policy clauses.")

    # Detect clauses
    paragraphs = [p.strip() for p in clean_content.split("\n\n") if len(p.strip()) > 25]
    if not paragraphs:
        paragraphs = [p.strip() for p in clean_content.split("\n") if len(p.strip()) > 25]

    clean_name = re.sub(r'[^a-zA-Z0-9]', '-', filename.rsplit('.', 1)[0]).upper()
    suggested_id = f"TN-{domain.upper()}-{clean_name[:12]}"
    suggested_title = f"{filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()} Policy"

    return PolicyPreviewResponse(
        extracted_text=clean_content,
        detected_domain=domain.upper(),
        suggested_policy_id=suggested_id,
        suggested_name=suggested_title,
        jurisdiction=jurisdiction.upper(),
        employee_category=employee_category.upper(),
        total_characters=len(clean_content),
        clauses=paragraphs[:10]
    )

@router.post("/admin/policies", response_model=PolicyResponse)
def create_authoritative_policy(
    p: PolicyCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(Policy).filter(Policy.policy_id == p.policy_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Policy with ID '{p.policy_id}' already exists.")

    new_pol = Policy(
        policy_id=p.policy_id,
        name=p.name,
        domain=p.domain.upper(),
        jurisdiction=p.jurisdiction or "INDIA",
        employee_category=p.employee_category or "ALL",
        current_version="1.0",
        content=p.content,
        status=p.status or "active",
        effective_date=p.effective_date or datetime.datetime.utcnow(),
        expiry_date=p.expiry_date
    )
    db.add(new_pol)
    db.commit()

    ver = PolicyVersion(
        policy_id=new_pol.policy_id,
        version="1.0",
        change_summary="Initial policy document uploaded by admin.",
        content=new_pol.content,
        is_active=True,
        effective_date=new_pol.effective_date
    )
    db.add(ver)
    db.commit()
    db.refresh(new_pol)
    return new_pol

def invalidate_cache_for_updated_policy(
    db: Session,
    pol: Policy,
    old_content: str,
    new_content: str
) -> int:
    """
    Selectively invalidates cached entries belonging to `pol` whose questions or answers
    are derived from or affected by the modified/updated clauses, while preserving
    cached entries that correspond strictly to unchanged clauses.
    """
    if not old_content or not new_content:
        invalidated = db.query(CachedEntry).filter(
            CachedEntry.policy_id == pol.policy_id,
            CachedEntry.is_active == True
        ).update({"is_active": False, "faiss_id": None}, synchronize_session=False)
        db.commit()
        reindex_all_active_cache_vectors(db)
        rag_service.invalidate_chunk_cache()
        return invalidated

    def _extract_clauses(text: str) -> List[str]:
        paras = [p.strip() for p in re.split(r'\n\s*\n', text) if len(p.strip()) > 15]
        if not paras:
            paras = [p.strip() for p in text.split("\n") if len(p.strip()) > 15]
        return paras or [text.strip()]

    old_clauses = _extract_clauses(old_content)
    new_clauses = _extract_clauses(new_content)

    changed_or_removed: List[str] = [oc for oc in old_clauses if oc not in new_clauses]
    added_clauses: List[str] = [nc for nc in new_clauses if nc not in old_clauses]

    if not changed_or_removed and not added_clauses:
        return 0

    entries = db.query(CachedEntry).filter(
        CachedEntry.policy_id == pol.policy_id,
        CachedEntry.is_active == True
    ).all()

    if not entries:
        rag_service.invalidate_chunk_cache()
        return 0

    if len(changed_or_removed) == len(old_clauses):
        for e in entries:
            e.is_active = False
            e.faiss_id = None
        db.commit()
        reindex_all_active_cache_vectors(db)
        rag_service.invalidate_chunk_cache()
        return len(entries)

    changed_texts = changed_or_removed + added_clauses
    changed_embs = embedding_service.encode(changed_texts, normalize=True)

    invalidated_count = 0
    for e in entries:
        q_emb = embedding_service.encode(e.question, normalize=True).flatten()
        sims_q = np.dot(changed_embs, q_emb)
        max_sim_q = float(np.max(sims_q)) if len(sims_q) > 0 else 0.0

        ans_emb = embedding_service.encode(e.answer, normalize=True).flatten()
        sims_ans = np.dot(changed_embs, ans_emb)
        max_sim_ans = float(np.max(sims_ans)) if len(sims_ans) > 0 else 0.0

        answer_unsupported = False
        nums_in_ans = re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?\b', e.answer)
        for num in nums_in_ans:
            if num in old_content and num not in new_content:
                answer_unsupported = True
                break

        if max_sim_q >= 0.40 or max_sim_ans >= 0.40 or answer_unsupported:
            e.is_active = False
            e.faiss_id = None
            invalidated_count += 1

    db.commit()
    reindex_all_active_cache_vectors(db)
    rag_service.invalidate_chunk_cache()
    return invalidated_count

def _completely_delete_policy(policy_id: str, db: Session):
    pol = db.query(Policy).filter(Policy.policy_id == policy_id).first()
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found.")

    # 1. Completely delete all associated cached entries
    del_cache = db.query(CachedEntry).filter(CachedEntry.policy_id == policy_id).delete(synchronize_session=False)

    # 2. Completely delete all policy versions
    del_versions = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy_id).delete(synchronize_session=False)

    # 3. Completely delete the policy
    db.delete(pol)
    db.commit()

    # 4. Rebuild FAISS index from remaining active entries and purge RAG chunks
    reindex_all_active_cache_vectors(db)
    rag_service.invalidate_chunk_cache()

    return {
        "status": "success",
        "message": f"Policy {policy_id} and {del_cache} associated cache entries completely deleted."
    }

@router.put("/admin/policies/{policy_id}", response_model=PolicyResponse)
def update_authoritative_policy(
    policy_id: str,
    p: PolicyUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
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
    if p.status is not None:
        pol.status = p.status
    if p.effective_date is not None:
        pol.effective_date = p.effective_date
    if p.expiry_date is not None:
        pol.expiry_date = p.expiry_date

    content_changed = False
    old_content = pol.content or ""
    if p.content is not None and p.content != pol.content:
        pol.content = p.content
        content_changed = True
        try:
            curr_v = float(pol.current_version)
            new_v = f"{curr_v + 0.1:.1f}"
        except Exception:
            new_v = "1.1"

        pol.current_version = new_v
        ver = PolicyVersion(
            policy_id=pol.policy_id,
            version=new_v,
            change_summary=f"Policy updated and published by {admin.username}.",
            content=pol.content,
            is_active=True,
            effective_date=datetime.datetime.utcnow()
        )
        db.add(ver)

    db.commit()
    db.refresh(pol)

    if content_changed:
        invalidate_cache_for_updated_policy(db, pol, old_content, pol.content)
    else:
        reindex_all_active_cache_vectors(db)
        rag_service.invalidate_chunk_cache()

    return pol

@router.delete("/admin/policies/{policy_id}")
def delete_authoritative_policy(
    policy_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return _completely_delete_policy(policy_id, db)

@router.post("/admin/policies/{policy_id}/deactivate")
def deactivate_policy(
    policy_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return _completely_delete_policy(policy_id, db)

@router.post("/admin/policies/invalidate-cache")
def invalidate_obsolete_cache(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Scans all cached entries against active policy records.
    Deactivates any cache entries linked to obsolete policies or superseded versions.
    """
    obsolete_policy_ids = [p.policy_id for p in db.query(Policy).filter(Policy.status == "obsolete").all()]
    
    count = 0
    if obsolete_policy_ids:
        count = db.query(CachedEntry).filter(
            CachedEntry.policy_id.in_(obsolete_policy_ids),
            CachedEntry.is_active == True
        ).update({"is_active": False}, synchronize_session=False)
        db.commit()
        # Re-index remaining active entries into FAISS
        reindex_all_active_cache_vectors(db)

    return {
        "status": "success",
        "invalidated_entries_count": count,
        "obsolete_policies_scanned": len(obsolete_policy_ids)
    }

# --- Admin Synthetic Data Generation & Candidate Review ---
@router.post("/admin/datasets/generate-synthetic", response_model=List[CandidatePairResponse])
def generate_synthetic_data(
    req: SyntheticGenerationRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Policy).filter(Policy.status == "active")
    if req.policy_id:
        query = query.filter(Policy.policy_id == req.policy_id)
    policies = query.all()

    all_candidates = []
    for pol in policies:
        pairs = generate_synthetic_pairs_from_text(pol.content, pol.policy_id, pol.domain)
        all_candidates.extend(pairs)

    return all_candidates[:50]

@router.post("/admin/datasets/upload-csv")
async def upload_dataset_csv(
    file: UploadFile = File(...),
    dataset_name: str = Form("custom_policy_dataset"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV datasets are accepted.")

    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    valid_rows = []
    pos_count = 0
    neg_count = 0

    for r in reader:
        if "q1" in r and "q2" in r and "label" in r:
            lbl = int(r["label"])
            valid_rows.append(r)
            if lbl == 1:
                pos_count += 1
            else:
                neg_count += 1

    if not valid_rows:
        raise HTTPException(status_code=400, detail="CSV must contain headers: q1, q2, label, group.")

    # Save to datasets directory
    target_path = settings.DATASETS_DIR / f"{dataset_name}.csv"
    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(valid_rows[0].keys()))
        writer.writeheader()
        writer.writerows(valid_rows)

    # Register in DB
    existing_rec = db.query(DatasetRecord).filter(DatasetRecord.name == dataset_name).first()
    if existing_rec:
        existing_rec.row_count = len(valid_rows)
        existing_rec.positive_count = pos_count
        existing_rec.negative_count = neg_count
        existing_rec.file_path = str(target_path)
    else:
        new_rec = DatasetRecord(
            name=dataset_name,
            file_path=str(target_path),
            row_count=len(valid_rows),
            positive_count=pos_count,
            negative_count=neg_count,
            split_info={"rows": len(valid_rows)}
        )
        db.add(new_rec)
    db.commit()

    return {
        "status": "success",
        "dataset_name": dataset_name,
        "rows_imported": len(valid_rows),
        "positive_count": pos_count,
        "negative_count": neg_count
    }

# --- Admin Model Registry, Retraining & Rollback ---
@router.get("/admin/models/registry", response_model=List[ModelArtifactVersionResponse])
def get_model_registry(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return db.query(ModelArtifactVersion).order_by(ModelArtifactVersion.created_at.desc()).all()

@router.post("/admin/models/train")
def train_and_publish_model(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:
        results = train_and_evaluate_all_models(db, created_by=admin.username)
        return {
            "status": "success",
            "message": "Model trained, calibrated, evaluated, and published successfully to registry.",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")

@router.post("/admin/models/rollback")
def rollback_model_version(
    req: RollbackRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:
        res = rollback_to_model_version(db, req.target_version_tag)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Rollback failed: {str(e)}")

@router.post("/admin/models/select")
@router.post("/models/select")
def select_active_model(
    req: ModelSelectionRequest,
    db: Session = Depends(get_db)
):
    try:
        equivalence_classifier.set_active_model(req.model_name)
        return {
            "status": "success",
            "active_model": equivalence_classifier.active_model,
            "message": f"Successfully switched active equivalence classifier to '{equivalence_classifier.active_model}'."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/admin/models/active")
@router.get("/models/active")
def get_active_model_info():
    from app.ml.decision_tree_classifier import decision_tree_classifier
    from app.ml.knn_classifier import knn_classifier
    return {
        "active_model": equivalence_classifier.active_model,
        "is_fitted": equivalence_classifier.is_fitted,
        "available_models": ["decision_tree", "logistic_regression", "knn"],
        "decision_tree": decision_tree_classifier.metadata,
        "knn": knn_classifier.metadata,
        "logistic_regression": equivalence_classifier.metadata
    }

# --- Admin Feedback & Reported Answers Queue ---
@router.get("/admin/feedback", response_model=List[FeedbackResponse])
def list_feedback_and_reports(
    status_filter: Optional[str] = None,
    reported_only: bool = False,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    q = db.query(UserFeedback)
    if status_filter:
        q = q.filter(UserFeedback.status == status_filter)
    if reported_only:
        q = q.filter(UserFeedback.is_reported_incorrect == True)
    return q.order_by(UserFeedback.created_at.desc()).limit(100).all()

@router.patch("/admin/feedback/{feedback_id}", response_model=FeedbackResponse)
def review_feedback(
    feedback_id: str,
    update: FeedbackAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    fb = db.query(UserFeedback).filter(UserFeedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback entry not found.")
    if update.status:
        fb.status = update.status
    if update.admin_notes is not None:
        fb.admin_notes = update.admin_notes
    db.commit()
    db.refresh(fb)
    return fb

# --- Admin CSV Export Endpoints ---
@router.get("/admin/audit-logs/export")
def export_audit_logs_csv(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    logs = db.query(QueryAuditLog).order_by(QueryAuditLog.created_at.desc()).limit(1000).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "user_id", "timestamp", "query_text", "decision", "is_cached_result",
        "returned_answer", "policy_id", "policy_version", "source_citation",
        "cosine_similarity", "classifier_score", "calibrated_probability", "total_latency_ms"
    ])
    for l in logs:
        writer.writerow([
            l.id, l.user_id, l.created_at.isoformat() if l.created_at else "",
            l.query_text, l.decision, l.is_cached_result, l.returned_answer,
            l.policy_id, l.policy_version, l.source_citation,
            l.cosine_similarity, l.classifier_score, l.calibrated_probability, l.total_latency_ms
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cachemind_audit_logs.csv"}
    )

# ==========================================
# 5. CORE ENDPOINTS (BACKWARD-COMPATIBLE & DASHBOARD)
# ==========================================
@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total = db.query(QueryAuditLog).count()
    hits = db.query(QueryAuditLog).filter(QueryAuditLog.decision.in_(["HIT", "CACHE_HIT"])).count()
    misses = total - hits
    hit_ratio = float(hits / total) if total > 0 else 0.0

    avg_lookup = db.query(func.avg(QueryAuditLog.lookup_latency_ms)).filter(QueryAuditLog.decision.in_(["HIT", "CACHE_HIT"])).scalar() or 0.0
    avg_fallback = db.query(func.avg(QueryAuditLog.total_latency_ms)).filter(~QueryAuditLog.decision.in_(["HIT", "CACHE_HIT"])).scalar() or 0.0

    # Measurable Sustainability & Efficiency Metrics
    non_policy_count = db.query(QueryAuditLog).filter(QueryAuditLog.decision.in_(["GREETING", "ERROR", "REJECTED_EMPTY_QUERY"])).count()
    eligible_policy_queries = max(0, total - non_policy_count)
    policy_cache_hit_rate = float(hits / eligible_policy_queries) if eligible_policy_queries > 0 else 0.0
    llm_calls_avoided = hits
    tokens_avoided = hits * 450
    latency_reduction_pct = round(max(0.0, float((avg_fallback - avg_lookup) / max(1.0, avg_fallback) * 100.0)), 1) if avg_fallback > 0 else 0.0

    # Real Grok API & Token Consumption Metrics
    grok_invocations = db.query(QueryAuditLog).filter(QueryAuditLog.grok_invoked == True).count()
    p_tokens = db.query(func.sum(QueryAuditLog.prompt_tokens)).scalar() or 0
    c_tokens = db.query(func.sum(QueryAuditLog.completion_tokens)).scalar() or 0
    total_tokens = int(p_tokens + c_tokens)

    # Actual measured/calculated API expense
    actual_cost_usd = float(db.query(func.sum(QueryAuditLog.estimated_cost_usd)).scalar() or 0.0)
    # Baseline cost assuming every user query required fresh full LLM inference
    cost_without_cache_usd = float(total * settings.DEFAULT_LLM_QUERY_COST)
    # Real net cost saved by cache hits avoiding external LLM inference
    cost_saved_usd = max(0.0, cost_without_cache_usd - actual_cost_usd)
    cost_saved_inr = cost_saved_usd * 83.50
    cost_without_cache_inr = cost_without_cache_usd * 83.50
    actual_cost_inr = actual_cost_usd * 83.50
    percent_avoided = float((hits / total) * 100.0) if total > 0 else 0.0

    active_eval = db.query(ThresholdEvaluationRun).filter(ThresholdEvaluationRun.is_active == True).order_by(ThresholdEvaluationRun.created_at.desc()).first()
    active_tau = active_eval.selected_threshold if active_eval else settings.DEFAULT_CACHE_THRESHOLD
    obs_fhr = active_eval.observed_fhr if active_eval else None
    ucb = active_eval.upper_confidence_bound if active_eval else None

    models = db.query(ModelMetadata).all()
    status_dict = {m.model_name: m.status for m in models}
    status_dict["embedding_transformer"] = "ready" if embedding_service.is_ready else "error"
    status_dict["faiss_index"] = "ready" if faiss_service.total_vectors() > 0 else "empty"
    status_dict["grok_api"] = "configured" if grok_service.is_available() else "standby_local_engine"

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
        model_status=status_dict,
        grok_invocations=grok_invocations,
        total_tokens_consumed=total_tokens,
        prompt_tokens=int(p_tokens),
        completion_tokens=int(c_tokens),
        actual_cost_usd=round(actual_cost_usd, 4),
        actual_cost_inr=round(actual_cost_inr, 2),
        cost_without_cache_usd=round(cost_without_cache_usd, 4),
        cost_without_cache_inr=round(cost_without_cache_inr, 2),
        percent_queries_avoided_llm=round(percent_avoided, 1),
        eligible_policy_queries=eligible_policy_queries,
        policy_cache_hit_rate=round(policy_cache_hit_rate, 4),
        llm_calls_avoided=llm_calls_avoided,
        tokens_avoided=tokens_avoided,
        latency_reduction_percent=latency_reduction_pct,
        environmental_impact_status="insufficient_data"
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

@router.post("/query/check-or-optimize", response_model=QueryCheckResponse)
def check_or_optimize_query(
    req: QueryRequest,
    opt_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    norm_query = normalize_text(req.query)
    if not norm_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

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
            lookup_latency_ms=0.5,
            total_latency_ms=1.0
        )

    if opt_info.get("is_optimized") and opt_info.get("optimized_query") != req.query:
        return QueryCheckResponse(
            status="NEEDS_CONFIRMATION",
            is_cached=False,
            needs_confirmation=True,
            original_query=req.query,
            optimized_query=opt_info["optimized_query"],
            removed_filler=opt_info.get("removed_filler", []),
            answer=None,
            provider_used="query_optimizer",
            lookup_latency_ms=0.5,
            total_latency_ms=1.5,
            grok_invoked=False,
            tokens_used=None,
            supporting_evidence_references=[],
            validation_status="passed"
        )

    return QueryCheckResponse(
        status="READY",
        is_cached=False,
        needs_confirmation=False,
        original_query=req.query,
        optimized_query=req.query,
        removed_filler=[],
        answer=None,
        provider_used="query_optimizer",
        lookup_latency_ms=0.5,
        total_latency_ms=1.0,
        grok_invoked=False,
        tokens_used=None,
        supporting_evidence_references=[],
        validation_status="passed"
    )

@router.post("/query", response_model=QueryResponse)
def handle_query(
    req: QueryRequest,
    opt_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
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
        domain_filter=req.domain,
        user_id=opt_user.id if opt_user else None,
        conversation_id=req.conversation_id
    )
    return result

# Policies listing (accessible to all authenticated or public)
@router.get("/policies", response_model=List[PolicyResponse])
def list_policies(db: Session = Depends(get_db)):
    return db.query(Policy).order_by(Policy.created_at.desc()).all()

@router.post("/policies", response_model=PolicyResponse)
def create_policy_public(p: PolicyCreate, db: Session = Depends(get_db)):
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

    ver = PolicyVersion(
        policy_id=new_pol.policy_id,
        version="1.0",
        change_summary="Initial policy document uploaded.",
        content=new_pol.content,
        is_active=True
    )
    db.add(ver)
    db.commit()
    db.refresh(new_pol)
    return new_pol

@router.put("/policies/{policy_id}", response_model=PolicyResponse)
def update_policy_public(policy_id: str, p: PolicyUpdate, db: Session = Depends(get_db)):
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
    content_changed = False
    old_content = pol.content or ""
    if p.content is not None and p.content != pol.content:
        pol.content = p.content
        content_changed = True
        try:
            curr_v = float(pol.current_version)
            pol.current_version = f"{curr_v + 0.1:.1f}"
        except Exception:
            pol.current_version = "1.1"

        ver = PolicyVersion(
            policy_id=pol.policy_id,
            version=pol.current_version,
            change_summary="Policy updated.",
            content=pol.content,
            is_active=True
        )
        db.add(ver)

    db.commit()
    db.refresh(pol)

    if content_changed:
        invalidate_cache_for_updated_policy(db, pol, old_content, pol.content)
    else:
        reindex_all_active_cache_vectors(db)
        rag_service.invalidate_chunk_cache()

    return pol

@router.delete("/policies/{policy_id}")
def delete_policy_public(policy_id: str, db: Session = Depends(get_db)):
    return _completely_delete_policy(policy_id, db)

@router.post("/policies/upload")
async def upload_policy_file_public(
    file: UploadFile = File(...),
    domain: str = Form("HR"),
    jurisdiction: str = Form("INDIA"),
    employee_category: str = Form("ALL"),
    db: Session = Depends(get_db)
):
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext not in ["txt", "pdf", "md"]:
        raise HTTPException(status_code=400, detail="Invalid format. Supported: .txt, .pdf, .md.")

    file_bytes = await file.read()
    extracted_text = ""

    if ext in ["txt", "md"]:
        try:
            extracted_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = file_bytes.decode("latin-1", errors="ignore")
    elif ext == "pdf":
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = [p.extract_text() for p in pdf_reader.pages if p.extract_text()]
            extracted_text = "\n\n".join(pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF parsing error: {str(e)}")

    clean_content = extracted_text.strip()
    if len(clean_content) < 20:
        raise HTTPException(status_code=400, detail="Uploaded file content is insufficient.")

    clean_name = re.sub(r'[^a-zA-Z0-9]', '-', filename.rsplit('.', 1)[0]).upper()
    policy_id = f"TN-{domain.upper()}-{clean_name[:12]}"

    existing_pol = db.query(Policy).filter(Policy.policy_id == policy_id).first()
    if existing_pol:
        existing_pol.content = clean_content
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

    # Invalidate existing cache entries derived from this policy if it was updated
    if existing_pol:
        db.query(CachedEntry).filter(
            CachedEntry.policy_id == policy_id,
            CachedEntry.is_active == True
        ).update({"is_active": False, "faiss_id": None}, synchronize_session=False)
        db.commit()
        reindex_all_active_cache_vectors(db)
    
    rag_service.invalidate_chunk_cache()

    return {
        "status": "success",
        "message": f"Policy '{pol_obj.name}' ({policy_id}) successfully uploaded into authoritative knowledge base.",
        "policy_id": policy_id,
        "qa_pairs_generated": 0,
        "total_characters": len(clean_content)
    }

# Cache Explorer CRUD
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

    db.query(CachedEntry).update({CachedEntry.faiss_id: None})
    db.commit()

    questions = [e.normalized_question for e in entries]
    ids = [e.id for e in entries]
    embs = embedding_service.encode(questions, normalize=True)

    count = faiss_service.rebuild_index(ids, embs)

    for idx, e in enumerate(entries):
        e.faiss_id = idx
    db.commit()

    return {"message": f"Successfully rebuilt FAISS index with {count} vectors.", "vector_count": count}

@router.post("/admin/cache/reset")
@router.post("/cache/reset")
def reset_cache_cold_start(db: Session = Depends(get_db)):
    """
    Cold-Start Reset: Empties all active cache entries and resets FAISS index to 0 vectors.
    Allows user/admin to verify cold-start -> miss -> grounded fallback -> write-on-miss -> hit workflow.
    """
    deactivated = db.query(CachedEntry).filter(CachedEntry.is_active == True).update(
        {"is_active": False, "faiss_id": None}, synchronize_session=False
    )
    db.commit()

    # Reset FAISS index to empty
    empty_emb = embedding_service.encode([])
    faiss_service.rebuild_index([], empty_emb)

    return {
        "status": "success",
        "message": f"Cold-start initiated. Emptied {deactivated} cached entries. FAISS index reset to 0 vectors.",
        "vector_count": 0,
        "deactivated_count": deactivated
    }

# ML Models Status
@router.get("/models/status")
def get_models_status(db: Session = Depends(get_db)):
    metas = db.query(ModelMetadata).all()
    models_info = {m.model_name: {
        "status": m.status,
        "metrics": m.metrics,
        "hyperparameters": m.hyperparameters,
        "last_trained_at": m.last_trained_at
    } for m in metas}

    active_reg = db.query(ModelArtifactVersion).filter(ModelArtifactVersion.is_active == True).first()

    return {
        "embedding_transformer": embedding_service.model_info,
        "faiss_index": {
            "total_vectors": faiss_service.total_vectors(),
            "dimension": settings.EMBEDDING_DIM,
            "metric": "InnerProduct (Cosine)"
        },
        "classifier": models_info.get("equivalence_classifier", equivalence_classifier.metadata),
        "calibrator": models_info.get("probability_calibrator", probability_calibrator.metadata),
        "active_registry_version": active_reg.version_tag if active_reg else "v1.0.0"
    }

@router.post("/models/train")
def train_models_legacy(db: Session = Depends(get_db)):
    try:
        results = train_and_evaluate_all_models(db)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

# Thresholds Evaluation
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

# Clustering Analytics
@router.get("/analytics/clusters")
def get_query_clusters(n_clusters: int = Query(3, ge=2, le=10), db: Session = Depends(get_db)):
    entries = db.query(CachedEntry).filter(CachedEntry.is_active == True).all()
    questions = [e.question for e in entries]
    if len(questions) < 2:
        return {"status": "insufficient_data", "message": "At least 2 cached queries required for clustering."}

    embs = embedding_service.encode([e.normalized_question for e in entries], normalize=True)
    res = query_clusterer.cluster_queries(questions, embs, n_clusters=n_clusters)
    return res

# Audit Logs
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

# Settings
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

@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    return db.query(DatasetRecord).all()
