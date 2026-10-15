import re
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Policy, PolicyVersion
from app.ml.embeddings import embedding_service
from app.ml.policy_validation import normalize_text, PolicyConditions

class DocumentRAGService:
    """
    Production-Grade Document-Grounded RAG Service.
    Retrieves approved policy evidence from the database before invoking Grok,
    evaluates evidence sufficiency, and verifies domain/jurisdiction applicability.
    """
    def __init__(self):
        # In-memory chunk cache to avoid re-embedding unchanged policies on every query
        self._cache_version: int = 0
        self._cached_chunks: List[Dict[str, Any]] = []
        self._cached_embeddings: Optional[np.ndarray] = None

    def invalidate_chunk_cache(self):
        """Invalidates the chunk embedding cache when policies change."""
        self._cached_chunks = []
        self._cached_embeddings = None
        self._cache_version += 1

    def chunk_policy_document(self, policy: Policy) -> List[Dict[str, Any]]:
        """
        Segments a policy document into coherent semantic clauses and passages.
        Preserves policy identifier, title, version, jurisdiction, and category scope.
        """
        content = (policy.content or "").strip()
        if not content:
            return []

        # Split into clauses by double newlines or list items
        raw_paras = [p.strip() for p in re.split(r'\n\s*\n', content) if len(p.strip()) > 20]
        if not raw_paras:
            raw_paras = [p.strip() for p in content.split("\n") if len(p.strip()) > 20]
        if not raw_paras:
            raw_paras = [content]

        chunks = []
        for idx, p in enumerate(raw_paras, 1):
            chunks.append({
                "chunk_id": f"{policy.policy_id}-clause-{idx:02d}",
                "policy_id": policy.policy_id,
                "policy_name": policy.name,
                "policy_version": getattr(policy, "current_version", "1.0"),
                "domain": policy.domain,
                "jurisdiction": policy.jurisdiction or "INDIA",
                "employee_category": policy.employee_category or "ALL",
                "text": p
            })
        return chunks

    def retrieve_evidence(
        self,
        db: Session,
        query: str,
        query_conditions: Optional[PolicyConditions] = None,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """
        Searches admin-uploaded policy documents for passages relevant to the query.
        Returns:
            has_sufficient_evidence: bool
            evidence_passages: List[Dict]
            top_similarity: float
            rejection_reason: Optional[str]
        """
        # Fetch all active policies
        policies = db.query(Policy).filter(Policy.status == "active").all()
        if not policies:
            return {
                "has_sufficient_evidence": False,
                "evidence_passages": [],
                "top_similarity": 0.0,
                "rejection_reason": "No approved policy documents are currently configured in the knowledge base."
            }

        # Build chunks from all active policies
        all_chunks = []
        for pol in policies:
            all_chunks.extend(self.chunk_policy_document(pol))

        if not all_chunks:
            return {
                "has_sufficient_evidence": False,
                "evidence_passages": [],
                "top_similarity": 0.0,
                "rejection_reason": "Policy documents contain no extractable clauses."
            }

        # Encode query and chunk texts
        norm_query = normalize_text(query)
        query_emb = embedding_service.encode(norm_query, normalize=True).flatten()
        
        chunk_texts = [f"{c['policy_name']}: {c['text']}" for c in all_chunks]
        chunk_embs = embedding_service.encode(chunk_texts, normalize=True)

        # Compute cosine similarities
        sims = np.dot(chunk_embs, query_emb)

        # Apply metadata filtering / weighting if constraints exist
        if query_conditions:
            for i, c in enumerate(all_chunks):
                # Domain match boost
                if query_conditions.domain and query_conditions.domain != "GENERAL":
                    if c["domain"] == query_conditions.domain:
                        sims[i] += 0.05
                    elif c["domain"] not in [query_conditions.domain, "GENERAL"]:
                        sims[i] -= 0.10

                # Jurisdiction penalty if conflicting
                q_jur = (query_conditions.jurisdiction or "GLOBAL").upper()
                c_jur = (c["jurisdiction"] or "GLOBAL").upper()
                if q_jur != "GLOBAL" and c_jur != "GLOBAL" and q_jur != c_jur:
                    sims[i] -= 0.35 # Strong penalty for jurisdiction conflict

                # Employee category penalty if conflicting
                q_cat = (query_conditions.employee_category or "ALL").upper()
                c_cat = (c["employee_category"] or "ALL").upper()
                if q_cat != "ALL" and c_cat != "ALL" and q_cat != c_cat:
                    sims[i] -= 0.25 # Strong penalty for scope conflict

        sorted_indices = np.argsort(sims)[::-1]
        best_sim = float(sims[sorted_indices[0]])

        # Strict evidence threshold: if similarity is too low, treat as insufficient evidence
        MIN_EVIDENCE_SIMILARITY = 0.28
        if best_sim < MIN_EVIDENCE_SIMILARITY:
            return {
                "has_sufficient_evidence": False,
                "evidence_passages": [],
                "top_similarity": best_sim,
                "rejection_reason": f"Top similarity score ({best_sim:.3f}) is below the required evidence threshold ({MIN_EVIDENCE_SIMILARITY:.2f}). Available documents do not provide sufficient evidence to answer."
            }

        # Select top-k relevant chunks that pass the minimum threshold
        relevant_chunks = []
        for idx in sorted_indices[:top_k]:
            if float(sims[idx]) >= MIN_EVIDENCE_SIMILARITY:
                item = dict(all_chunks[idx])
                item["similarity"] = round(float(sims[idx]), 4)
                relevant_chunks.append(item)

        return {
            "has_sufficient_evidence": len(relevant_chunks) > 0,
            "evidence_passages": relevant_chunks,
            "top_similarity": best_sim,
            "primary_policy_id": relevant_chunks[0]["policy_id"] if relevant_chunks else None,
            "rejection_reason": None
        }

    def synthesize_local_grounded_answer(
        self,
        query: str,
        evidence_passages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        High-precision deterministic local synthesis engine.
        Used when Grok API is not configured or in offline environments.
        Strictly preserves policy clauses and citations with zero mock data.
        """
        if not evidence_passages:
            return {
                "answer": "The available corporate policy documents do not contain sufficient evidence to answer this question.",
                "has_sufficient_evidence": False,
                "provider": "grounded_company_policy_engine",
                "model": "all-MiniLM-L6-v2-rag",
                "policy_id": None,
                "policy_version": None,
                "source_document": None,
                "source_citation": None,
                "supporting_evidence_references": []
            }

        top = evidence_passages[0]
        pol_id = top["policy_id"]
        pol_name = top["policy_name"]
        pol_ver = top.get("policy_version", "1.0")
        
        answer_text = f"Under policy {pol_id} ({pol_name}):\n\n{top['text']}"
        if len(evidence_passages) > 1 and evidence_passages[1]["policy_id"] == pol_id:
            answer_text += f"\n\nAdditionally: {evidence_passages[1]['text']}"

        source_cit = f"Policy {pol_id} (Version {pol_ver}) - Scope: {top.get('employee_category', 'ALL')}"

        return {
            "answer": answer_text,
            "has_sufficient_evidence": True,
            "provider": "grounded_company_policy_engine",
            "model": "all-MiniLM-L6-v2-rag",
            "policy_id": pol_id,
            "policy_version": pol_ver,
            "source_document": pol_name,
            "source_citation": source_cit,
            "supporting_evidence_references": [source_cit]
        }

rag_service = DocumentRAGService()
