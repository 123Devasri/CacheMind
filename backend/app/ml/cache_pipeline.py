import time
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import CachedEntry, QueryAuditLog, ThresholdEvaluationRun
from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.policy_validation import extract_policy_conditions, validate_condition_safety, normalize_text
from app.ml.feature_engineering import build_pair_features
from app.ml.equivalence_classifier import equivalence_classifier
from app.ml.probability_calibration import probability_calibrator
from app.services.fallback_service import llm_service

class CacheDecisionPipeline:
    """
    Central Decision Service enforcing the 14-step governed semantic cache decision pipeline:
    1. Validate & normalize incoming question.
    2. Extract policy scope & structured conditions.
    3. Sentence Transformer embedding.
    4. FAISS top-K retrieval.
    5. Filter candidates below minimum cosine similarity.
    6. Check policy versions & mandatory conditions (fail closed).
    7. Generate identical 8-dim feature vector.
    8. Logistic Regression equivalence score.
    9. Isotonic Regression probability calibration.
    10. Compare with active statistical threshold.
    11. Final verification checks.
    12. Return verified cached answer if all checks pass.
    13. Otherwise invoke LLM fallback / local mock.
    14. Persist comprehensive audit log.
    """
    def __init__(self):
        pass

    def get_active_threshold(self, db: Session) -> float:
        active_eval = db.query(ThresholdEvaluationRun).filter(ThresholdEvaluationRun.is_active == True).order_by(ThresholdEvaluationRun.created_at.desc()).first()
        if active_eval and active_eval.selected_threshold is not None:
            return float(active_eval.selected_threshold)
        return float(settings.DEFAULT_CACHE_THRESHOLD)

    def process_query(
        self,
        db: Session,
        query: str,
        domain_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        lookup_start = start_time

        # Step 1: Validate & normalize
        norm_query = normalize_text(query)
        if not norm_query:
            return {
                "decision": "REJECTED_EMPTY_QUERY",
                "answer": "Query cannot be empty.",
                "is_cached": False,
                "reasons": ["Empty query string provided."],
                "latency_ms": 0.0
            }

        # Step 2: Extract conditions
        query_conditions = extract_policy_conditions(norm_query, default_domain=domain_filter)

        # Step 3: Embed
        query_embedding = embedding_service.encode(norm_query, normalize=True)

        # Step 4: FAISS search
        candidates = faiss_service.search(
            query_embedding,
            top_k=settings.DEFAULT_TOP_K,
            min_similarity=settings.DEFAULT_MIN_COSINE_SIM
        )
        lookup_latency_ms = (time.perf_counter() - lookup_start) * 1000.0

        active_threshold = self.get_active_threshold(db)

        chosen_hit = None
        rejection_reasons = []
        best_candidate_info = None

        if not candidates:
            rejection_reasons.append("No candidates retrieved above minimum similarity threshold.")
        else:
            # Evaluate retrieved candidates
            for cand in candidates:
                cand_db: Optional[CachedEntry] = db.query(CachedEntry).filter(
                    CachedEntry.id == cand["entry_id"],
                    CachedEntry.is_active == True
                ).first()

                if not cand_db:
                    continue

                # Must be verified
                if not cand_db.is_verified:
                    rejection_reasons.append(f"Candidate {cand_db.id} is marked unverified.")
                    continue

                # Step 6: Deterministic condition safety
                cand_cond_dict = {
                    "domain": cand_db.domain,
                    "jurisdiction": cand_db.jurisdiction,
                    "employee_category": cand_db.employee_category,
                    "numerical_limits": cand_db.numerical_limits or {},
                    "is_negated": False, # Verified cache entries represent standard affirmative policy clauses
                    "policy_version": cand_db.policy_version
                }
                is_safe, mismatch_reasons = validate_condition_safety(query_conditions, cand_cond_dict)

                # Step 7: Feature generation
                features = build_pair_features(
                    q1_text=norm_query,
                    q2_text=cand_db.normalized_question,
                    cosine_sim=cand["similarity"],
                    q1_cond=query_conditions,
                    q2_cond_dict=cand_cond_dict
                )

                # Step 8: Classifier score
                raw_score = equivalence_classifier.predict_score(features)

                # Step 9: Calibrated probability
                calibrated_prob = probability_calibrator.calibrate(raw_score)

                candidate_eval = {
                    "cache_id": cand_db.id,
                    "faiss_id": cand["faiss_id"],
                    "question": cand_db.question,
                    "cosine_similarity": round(float(cand["similarity"]), 4),
                    "classifier_score": round(float(raw_score), 4),
                    "calibrated_probability": round(float(calibrated_prob), 4),
                    "applied_threshold": active_threshold,
                    "policy_condition_passed": is_safe,
                    "condition_mismatches": mismatch_reasons
                }

                if best_candidate_info is None or cand["similarity"] > best_candidate_info["cosine_similarity"]:
                    best_candidate_info = candidate_eval

                # Step 10 & 11: Threshold & safety checks
                if not is_safe:
                    rejection_reasons.extend(mismatch_reasons)
                    continue

                if calibrated_prob < active_threshold:
                    rejection_reasons.append(
                        f"Calibrated probability {calibrated_prob:.4f} below threshold {active_threshold:.4f}."
                    )
                    continue

                # Safe candidate found!
                chosen_hit = cand_db
                cand_db.hit_count += 1
                db.commit()
                break

        # Step 12 or 13: Final answer & Fallback
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        if chosen_hit:
            decision = "HIT"
            returned_answer = chosen_hit.answer
            is_cached = True
            provider_used = "cache"
        else:
            decision = "CACHE_MISS"
            is_cached = False
            fallback_res = llm_service.generate_response(query, domain=domain_filter)
            returned_answer = fallback_res["answer"]
            provider_used = fallback_res["provider"]
            total_latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Step 14: Persist Audit Log
        audit_log = QueryAuditLog(
            query_text=query,
            domain_filter=domain_filter,
            decision=decision,
            rejection_reasons=rejection_reasons,
            candidate_cache_id=best_candidate_info["cache_id"] if best_candidate_info else None,
            candidate_faiss_id=best_candidate_info["faiss_id"] if best_candidate_info else None,
            candidate_question=best_candidate_info["question"] if best_candidate_info else None,
            cosine_similarity=best_candidate_info["cosine_similarity"] if best_candidate_info else None,
            classifier_score=best_candidate_info["classifier_score"] if best_candidate_info else None,
            calibrated_probability=best_candidate_info["calibrated_probability"] if best_candidate_info else None,
            applied_threshold=active_threshold,
            policy_condition_passed=best_candidate_info["policy_condition_passed"] if best_candidate_info else False,
            condition_mismatches=best_candidate_info["condition_mismatches"] if best_candidate_info else [],
            returned_answer=returned_answer,
            is_cached_result=is_cached,
            provider_used=provider_used,
            lookup_latency_ms=round(lookup_latency_ms, 2),
            total_latency_ms=round(total_latency_ms, 2)
        )
        db.add(audit_log)
        db.commit()

        return {
            "query": query,
            "decision": decision,
            "is_cached": is_cached,
            "answer": returned_answer,
            "provider_used": provider_used,
            "rejection_reasons": rejection_reasons,
            "candidate": best_candidate_info,
            "active_threshold": active_threshold,
            "lookup_latency_ms": round(lookup_latency_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "log_id": audit_log.id
        }

cache_pipeline = CacheDecisionPipeline()
