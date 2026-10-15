from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Policy
from app.ml.policy_validation import extract_policy_conditions
from app.services.rag_service import rag_service
from app.services.grok_service import grok_service

class GroundedCompanyPolicyService:
    """
    Document-Grounded Inference Service.
    Retrieves approved evidence from policy documents, checks sufficiency,
    and invokes Grok API (xAI) for grounded answer generation with token tracking.
    """
    def __init__(self):
        pass

    def generate_response(
        self,
        db: Session,
        query: str,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Extract query constraints
        query_conditions = extract_policy_conditions(query, default_domain=domain)

        # 2. Document-Grounded RAG Evidence Retrieval
        rag_res = rag_service.retrieve_evidence(
            db=db,
            query=query,
            query_conditions=query_conditions,
            top_k=4
        )

        if not rag_res["has_sufficient_evidence"] or not rag_res["evidence_passages"]:
            return {
                "provider": "evidence_guard",
                "model": "grounded-evidence-verifier",
                "is_mock": False,
                "answer": "The available corporate policy documents do not contain sufficient evidence to answer this question. Please contact HR or Policy Administration for assistance.",
                "has_sufficient_evidence": False,
                "grok_invoked": False,
                "tokens_used": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "estimated_cost_usd": 0.0,
                "policy_id": None,
                "policy_version": None,
                "source_document": None,
                "source_citation": None,
                "supporting_evidence_references": [],
                "validation_status": "insufficient_evidence"
            }

        evidence_passages = rag_res["evidence_passages"]
        top_passage = evidence_passages[0]
        pol_id = top_passage["policy_id"]
        pol_ver = top_passage.get("policy_version", "1.0")
        pol_name = top_passage.get("policy_name", "Corporate Policy")

        # 3. Call Grok API if available
        if grok_service.is_available():
            grok_res = grok_service.generate_grounded_answer(
                query=query,
                query_conditions=query_conditions,
                retrieved_evidence=evidence_passages
            )
            if grok_res.get("success"):
                return {
                    "provider": "grok_api",
                    "model": grok_res.get("model", settings.XAI_MODEL),
                    "is_mock": False,
                    "answer": grok_res.get("answer"),
                    "has_sufficient_evidence": grok_res.get("has_sufficient_evidence", True),
                    "grok_invoked": True,
                    "tokens_used": grok_res.get("tokens_used", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
                    "estimated_cost_usd": grok_res.get("estimated_cost_usd", 0.0),
                    "policy_id": pol_id,
                    "policy_version": pol_ver,
                    "source_document": pol_name,
                    "source_citation": f"Policy {pol_id} (v{pol_ver}) - Scope: {top_passage.get('employee_category', 'ALL')}",
                    "supporting_evidence_references": grok_res.get("supporting_evidence_references") or [f"Policy {pol_id} (Version {pol_ver})"],
                    "applicable_conditions": grok_res.get("applicable_conditions", {}),
                    "confidence_status": grok_res.get("confidence_status", "high"),
                    "validation_status": "passed" if grok_res.get("has_sufficient_evidence") else "insufficient_evidence"
                }
            else:
                # Grok API call attempted but failed -> log and gracefully fall back to local grounded synthesis
                print(f"Notice: Grok API call error: {grok_res.get('error')}. Falling back to verified local synthesis.")

        # 4. High-Precision Local Grounded Synthesis Engine (Zero Mock Data)
        local_res = rag_service.synthesize_local_grounded_answer(
            query=query,
            evidence_passages=evidence_passages
        )
        return {
            "provider": local_res["provider"],
            "model": local_res["model"],
            "is_mock": False,
            "answer": local_res["answer"],
            "has_sufficient_evidence": True,
            "grok_invoked": False,
            "tokens_used": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "estimated_cost_usd": 0.0,
            "policy_id": pol_id,
            "policy_version": pol_ver,
            "source_document": pol_name,
            "source_citation": local_res["source_citation"],
            "supporting_evidence_references": local_res["supporting_evidence_references"],
            "validation_status": "passed"
        }

llm_service = GroundedCompanyPolicyService()
