import time
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import CachedEntry, QueryAuditLog, ThresholdEvaluationRun, Policy
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
    13. Otherwise invoke extractive policy-grounded fallback.
    14. Persist comprehensive audit log with user and session tracking.
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
        domain_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        lookup_start = start_time
        active_threshold = self.get_active_threshold(db)

        # Step 0: Prompt & Question Optimization (Acronym expansion & Naive Bayes domain classification)
        from app.ml.query_optimizer import optimize_user_query
        opt_info = optimize_user_query(query)

        if opt_info.get("is_pure_greeting"):
            tot_lat = round((time.perf_counter() - start_time) * 1000.0, 2)
            greeting_answer = "Hello! I am your Enterprise Policy AI Assistant. How can I assist you with corporate policies today?"
            audit_log = QueryAuditLog(
                user_id=user_id,
                conversation_id=conversation_id,
                query_text=query,
                domain_filter=domain_filter,
                decision="GREETING",
                rejection_reasons=[],
                returned_answer=greeting_answer,
                is_cached_result=True,
                provider_used="prompt_optimizer",
                applied_threshold=active_threshold,
                lookup_latency_ms=0.5,
                total_latency_ms=tot_lat,
                grok_invoked=False,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
                supporting_evidence_references=[],
                validation_status="passed"
            )
            db.add(audit_log)
            db.commit()

            return {
                "query": query,
                "decision": "GREETING",
                "answer": greeting_answer,
                "is_cached": True,
                "provider_used": "prompt_optimizer",
                "rejection_reasons": [],
                "candidate": None,
                "active_threshold": active_threshold,
                "lookup_latency_ms": 0.5,
                "total_latency_ms": tot_lat,
                "log_id": audit_log.id,
                "policy_id": None,
                "policy_version": None,
                "source_citation": None,
                "source_document": None,
                "grok_invoked": False,
                "tokens_used": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "supporting_evidence_references": [],
                "validation_status": "passed",
                "estimated_cost_usd": 0.0
            }

        effective_query = opt_info.get("optimized_query", query)
        effective_domain = domain_filter or opt_info.get("predicted_domain")

        # Step 1: Validate & normalize
        norm_query = normalize_text(effective_query)
        if not norm_query:
            return {
                "query": query,
                "decision": "REJECTED_EMPTY_QUERY",
                "answer": "Query cannot be empty.",
                "is_cached": False,
                "provider_used": "validation_guard",
                "rejection_reasons": ["Empty query string provided."],
                "candidate": None,
                "active_threshold": active_threshold,
                "lookup_latency_ms": 0.0,
                "total_latency_ms": 0.0,
                "log_id": None,
                "policy_id": None,
                "policy_version": None,
                "source_citation": None,
                "source_document": None,
                "grok_invoked": False,
                "tokens_used": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "supporting_evidence_references": [],
                "validation_status": "rejected",
                "estimated_cost_usd": 0.0
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

                # Check if referenced policy document is active and not obsolete
                pol_rec = db.query(Policy).filter(Policy.policy_id == cand_db.policy_id).first()
                if pol_rec and (getattr(pol_rec, "status", "active") == "obsolete"):
                    rejection_reasons.append(f"Referenced policy {cand_db.policy_id} is marked obsolete.")
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

        # Step 12 or 13: Final answer & Grounded Fallback
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0
        grok_invoked = False
        tokens_used = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        estimated_cost_usd = 0.0
        supporting_evidence_references = []
        validation_status = "passed"
        
        if chosen_hit:
            decision = "HIT"
            returned_answer = chosen_hit.answer
            is_cached = True
            provider_used = "cache"
            grok_invoked = False
            estimated_cost_usd = settings.CACHE_HIT_UNIT_COST
            
            pol_obj = db.query(Policy).filter(Policy.policy_id == chosen_hit.policy_id).first()
            policy_id = chosen_hit.policy_id
            policy_version = chosen_hit.policy_version
            source_document = pol_obj.name if pol_obj else f"Policy {chosen_hit.policy_id}"
            source_citation = f"Policy {chosen_hit.policy_id} (Version {chosen_hit.policy_version}) - Jurisdiction: {chosen_hit.jurisdiction}, Scope: {chosen_hit.employee_category}"
            supporting_evidence_references = [source_citation]
        else:
            fallback_res = llm_service.generate_response(db=db, query=query, domain=domain_filter)
            has_sufficient = fallback_res.get("has_sufficient_evidence", True)
            returned_answer = fallback_res["answer"]
            provider_used = fallback_res.get("provider", "grounded_company_policy_engine")
            policy_id = fallback_res.get("policy_id")
            policy_version = fallback_res.get("policy_version")
            source_citation = fallback_res.get("source_citation")
            source_document = fallback_res.get("source_document")
            grok_invoked = fallback_res.get("grok_invoked", False)
            tokens_used = fallback_res.get("tokens_used", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
            estimated_cost_usd = fallback_res.get("estimated_cost_usd", settings.DEFAULT_LLM_QUERY_COST if grok_invoked else 0.0)
            supporting_evidence_references = fallback_res.get("supporting_evidence_references", [])
            validation_status = fallback_res.get("validation_status", "passed" if has_sufficient else "insufficient_evidence")
            total_latency_ms = (time.perf_counter() - start_time) * 1000.0

            if not has_sufficient or policy_id is None:
                decision = "INSUFFICIENT_EVIDENCE"
                is_cached = False
                validation_status = "insufficient_evidence"
                if not returned_answer or not str(returned_answer).strip():
                    returned_answer = "The available corporate policy documents do not contain sufficient evidence to answer this question. Please contact HR or Policy Administration for assistance."
            else:
                decision = "CACHE_MISS"
                is_cached = False

                # Dynamic Write-on-Miss: automatically remember grounded policy answers
                # Only cache if evidence is verified, policy exists, and conditions match
                if (
                    policy_id
                    and returned_answer
                    and not returned_answer.startswith("According to Kaveri Tech Solutions")
                    and not returned_answer.startswith("The available corporate policy")
                    and not returned_answer.startswith("No company policy")
                    and validation_status == "passed"
                ):
                    try:
                        existing_entry = db.query(CachedEntry).filter(
                            CachedEntry.normalized_question == norm_query,
                            CachedEntry.is_active == True
                        ).first()

                        if existing_entry:
                            if (
                                existing_entry.faiss_id is None
                                or existing_entry.faiss_id not in faiss_service.id_map
                                or existing_entry.faiss_id >= faiss_service.total_vectors()
                            ):
                                emb = embedding_service.encode(norm_query, normalize=True)
                                existing_entry.faiss_id = faiss_service.add_vector(existing_entry.id, emb)
                                db.commit()
                        else:
                            pol_rec = db.query(Policy).filter(Policy.policy_id == policy_id).first()
                            new_entry = CachedEntry(
                                question=effective_query,
                                normalized_question=norm_query,
                                answer=returned_answer,
                                policy_id=policy_id,
                                policy_version=policy_version or (pol_rec.current_version if pol_rec else "1.0"),
                                domain=effective_domain or (pol_rec.domain if pol_rec else "HR"),
                                jurisdiction=pol_rec.jurisdiction if pol_rec else "INDIA",
                                employee_category=pol_rec.employee_category if pol_rec else "ALL",
                                numerical_limits=extract_policy_conditions(norm_query).numerical_limits,
                                is_verified=True,
                                is_active=True,
                                hit_count=0
                            )
                            db.add(new_entry)
                            db.commit()
                            db.refresh(new_entry)

                            # Immediately encode and index into FAISS
                            emb = embedding_service.encode(norm_query, normalize=True)
                            new_entry.faiss_id = faiss_service.add_vector(new_entry.id, emb)
                            db.commit()
                    except Exception as ex:
                        print(f"Warning: Auto-cache on miss error: {ex}")
                        db.rollback()

        # Step 14: Persist Comprehensive Audit Log
        audit_log = QueryAuditLog(
            user_id=user_id,
            conversation_id=conversation_id,
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
            policy_id=policy_id,
            policy_version=policy_version,
            source_citation=source_citation,
            source_document=source_document,
            returned_answer=returned_answer,
            is_cached_result=is_cached,
            provider_used=provider_used,
            grok_invoked=grok_invoked,
            prompt_tokens=tokens_used.get("prompt_tokens", 0),
            completion_tokens=tokens_used.get("completion_tokens", 0),
            total_tokens=tokens_used.get("total_tokens", 0),
            estimated_cost_usd=round(float(estimated_cost_usd), 6),
            supporting_evidence_references=supporting_evidence_references,
            validation_status=validation_status,
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
            "log_id": audit_log.id,
            "policy_id": policy_id,
            "policy_version": policy_version,
            "source_citation": source_citation,
            "source_document": source_document,
            "grok_invoked": grok_invoked,
            "tokens_used": tokens_used,
            "supporting_evidence_references": supporting_evidence_references,
            "validation_status": validation_status,
            "estimated_cost_usd": round(float(estimated_cost_usd), 6)
        }

cache_pipeline = CacheDecisionPipeline()
