import re
import hashlib
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Policy, PolicyVersion
from app.ml.embeddings import embedding_service
from app.ml.policy_validation import normalize_text, PolicyConditions

def parse_policy_sections(content: str, policy_id: str = "") -> List[Dict[str, Any]]:
    """
    Parses a policy document into structured sections, preserving headings,
    hierarchical paths, page markers, and sha256 content hashes.
    Supports markdown headers, numbered sections, all-caps titles, and paragraph splitting.
    """
    if not content or not content.strip():
        return []

    lines = content.split("\n")
    sections = []
    current_heading = "General Overview"
    current_page = None
    current_lines = []
    sec_idx = 1

    def _flush_section():
        nonlocal sec_idx, current_lines
        sec_text = "\n".join(current_lines).strip()
        if sec_text and len(sec_text) > 10:
            c_hash = hashlib.sha256(f"{current_heading}\n{sec_text}".encode("utf-8")).hexdigest()[:16]
            sections.append({
                "section_id": f"{policy_id}-sec-{sec_idx:02d}" if policy_id else f"sec-{sec_idx:02d}",
                "heading": current_heading,
                "text": sec_text,
                "content_hash": c_hash,
                "page_number": current_page
            })
            sec_idx += 1
        current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_lines.append("")
            continue

        # Page marker detection: [Page 2], --- Page 2 ---, Page 2 of 5
        page_match = re.search(r'(?:\[Page\s*(\d+)\]|---\s*Page\s*(\d+)\s*---|Page\s*(\d+)\s*of\s*\d+)', stripped, re.IGNORECASE)
        if page_match:
            p_num = next(g for g in page_match.groups() if g is not None)
            current_page = int(p_num)
            continue

        # Section Heading detection:
        is_heading = False
        h_text = ""

        # Markdown or explicit Section / Article / Clause prefix
        heading_match = re.match(r'^(?:#{1,4}\s+|(?:\d+\.|\d+\))\s+|(?:Section|Article|Clause|Policy)\s+\d+[:.]?\s*)([A-Za-z0-9].{2,80})$', stripped, re.IGNORECASE)
        if heading_match and len(stripped) < 90:
            is_heading = True
            h_text = heading_match.group(1).strip()
        elif stripped.endswith(":") and len(stripped) < 60 and not any(p in stripped for p in [".", ";"]):
            is_heading = True
            h_text = stripped.rstrip(":").strip()
        elif stripped.isupper() and 3 < len(stripped) < 60 and not any(p in stripped for p in [".", ";", ","]):
            is_heading = True
            h_text = stripped.title().strip()

        if is_heading:
            _flush_section()
            current_heading = h_text or stripped.lstrip("#").strip()
            continue

        current_lines.append(line)

    _flush_section()

    # Paragraph fallback if only 1 giant section was created but content has multiple distinct paragraphs
    if len(sections) <= 1:
        raw_paras = [p.strip() for p in re.split(r'\n\s*\n', content) if len(p.strip()) > 15]
        if len(raw_paras) > 1:
            sections = []
            for idx, p in enumerate(raw_paras, 1):
                p_lines = [l.strip() for l in p.split("\n") if l.strip()]
                if p_lines and len(p_lines[0]) < 60 and not p_lines[0].endswith("."):
                    p_heading = p_lines[0].rstrip(":").strip()
                    p_body = "\n".join(p_lines[1:]).strip() or p
                else:
                    p_heading = f"Clause {idx}"
                    p_body = p

                c_hash = hashlib.sha256(f"{p_heading}\n{p_body}".encode("utf-8")).hexdigest()[:16]
                sections.append({
                    "section_id": f"{policy_id}-sec-{idx:02d}" if policy_id else f"sec-{idx:02d}",
                    "heading": p_heading,
                    "text": p_body,
                    "content_hash": c_hash,
                    "page_number": None
                })

    return sections


class DocumentRAGService:
    """
    Production-Grade Contextual Document-Grounded RAG Service.
    Retrieves approved policy evidence from the database before invoking Grok,
    evaluates evidence sufficiency, detects document conflicts, and tracks
    granular section dependencies and content hashes for precise cache governance.
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
        Segments a policy document into coherent semantic clauses and passages
        with hierarchical context, section IDs, headings, page numbers, and content hashes.
        Ensures chunks fit comfortably within transformer context window without truncation.
        """
        content = (policy.content or "").strip()
        if not content:
            return []

        sections = parse_policy_sections(content, policy.policy_id)
        chunks = []
        chk_idx = 1

        for sec in sections:
            heading = sec.get("heading", f"Clause {chk_idx}")
            page_info = f", Page {sec['page_number']}" if sec.get("page_number") else ""
            sec_text = sec["text"]

            # If section text is long (over 850 chars), split into coherent sub-paragraphs
            if len(sec_text) > 850:
                sub_paras = [p.strip() for p in re.split(r'\n\s*\n', sec_text) if len(p.strip()) > 15]
                if len(sub_paras) <= 1:
                    sentences = re.split(r'(?<=[.!?])\s+', sec_text)
                    sub_paras = []
                    curr_p = []
                    curr_len = 0
                    for s in sentences:
                        curr_p.append(s)
                        curr_len += len(s)
                        if curr_len >= 450:
                            sub_paras.append(" ".join(curr_p))
                            curr_p = []
                            curr_len = 0
                    if curr_p:
                        sub_paras.append(" ".join(curr_p))
            else:
                sub_paras = [sec_text]

            for s_idx, p_text in enumerate(sub_paras, 1):
                sub_heading = f"{heading} (Part {s_idx})" if len(sub_paras) > 1 else heading
                source_cit = f"Policy {policy.policy_id} ({policy.name}, v{getattr(policy, 'current_version', '1.0')}) - Section: {sub_heading}{page_info}"
                contextual_text = f"[{policy.name} | Section: {sub_heading}]\n{p_text}"

                chunks.append({
                    "chunk_id": f"{policy.policy_id}-chk-{chk_idx:02d}",
                    "section_id": sec["section_id"],
                    "policy_id": policy.policy_id,
                    "policy_name": policy.name,
                    "policy_version": getattr(policy, "current_version", "1.0"),
                    "domain": policy.domain,
                    "jurisdiction": policy.jurisdiction or "INDIA",
                    "employee_category": policy.employee_category or "ALL",
                    "heading": sub_heading,
                    "page_number": sec.get("page_number"),
                    "text": p_text,
                    "content_hash": sec["content_hash"],
                    "contextual_text": contextual_text,
                    "source_citation": source_cit
                })
                chk_idx += 1

        return chunks

    def retrieve_evidence(
        self,
        db: Session,
        query: str,
        query_conditions: Optional[PolicyConditions] = None,
        top_k: int = 4,
        domain: Optional[str] = None,
        min_similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Searches admin-uploaded policy documents for passages relevant to the query.
        Uses Hybrid Dense Embedding + Lexical Keyword Scoring for precision.
        """
        # Fetch all active policies
        policies = db.query(Policy).filter(Policy.status == "active").all()
        if not policies:
            return {
                "has_sufficient_evidence": False,
                "retrieval_status": "INSUFFICIENT_EVIDENCE",
                "evidence_passages": [],
                "top_similarity": 0.0,
                "primary_policy_id": None,
                "source_section_ids": [],
                "source_content_hashes": {},
                "rejection_reason": "No approved policy documents are currently configured in the knowledge base."
            }

        # Build chunks from all active policies
        all_chunks = []
        for pol in policies:
            all_chunks.extend(self.chunk_policy_document(pol))

        if not all_chunks:
            return {
                "has_sufficient_evidence": False,
                "retrieval_status": "INSUFFICIENT_EVIDENCE",
                "evidence_passages": [],
                "top_similarity": 0.0,
                "primary_policy_id": None,
                "source_section_ids": [],
                "source_content_hashes": {},
                "rejection_reason": "Policy documents contain no extractable clauses."
            }

        # 1. Dense Semantic Similarity
        norm_query = normalize_text(query)
        query_emb = embedding_service.encode(norm_query, normalize=True).flatten()
        
        chunk_texts = [c["contextual_text"] for c in all_chunks]
        chunk_embs = embedding_service.encode(chunk_texts, normalize=True)
        sims = np.dot(chunk_embs, query_emb)

        # 2. Lexical Keyword Overlap Boost (Hybrid Search)
        stop_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how",
                      "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
                      "do", "does", "did", "can", "could", "shall", "should", "will", "would",
                      "may", "might", "must", "the", "a", "an", "and", "or", "but", "in", "on",
                      "at", "to", "for", "with", "about", "against", "between", "into", "through",
                      "during", "before", "after", "above", "below", "of", "from", "up", "down",
                      "i", "me", "my", "myself", "we", "our", "you", "your", "he", "she", "it",
                      "they", "their", "this", "that", "these", "those", "get", "give", "tell", "explain"}
        query_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', norm_query.lower())) - stop_words

        if query_words:
            for i, c in enumerate(all_chunks):
                chunk_haystack = (c["heading"] + " " + c["text"]).lower()
                matches = sum(1 for w in query_words if w in chunk_haystack)
                overlap_ratio = matches / len(query_words)
                sims[i] += 0.20 * overlap_ratio

        # 3. Apply metadata filtering / weighting if constraints exist
        effective_domain = domain or (query_conditions.domain if query_conditions else None)
        if effective_domain and effective_domain != "GENERAL":
            for i, c in enumerate(all_chunks):
                if c["domain"] == effective_domain:
                    sims[i] += 0.05
                elif c["domain"] not in [effective_domain, "GENERAL"]:
                    sims[i] -= 0.10

        if query_conditions:
            for i, c in enumerate(all_chunks):
                # Jurisdiction penalty if conflicting
                q_jur = (query_conditions.jurisdiction or "GLOBAL").upper()
                c_jur = (c["jurisdiction"] or "GLOBAL").upper()
                if q_jur != "GLOBAL" and c_jur != "GLOBAL" and q_jur != c_jur:
                    sims[i] -= 0.35

                # Employee category penalty if conflicting
                q_cat = (query_conditions.employee_category or "ALL").upper()
                c_cat = (c["employee_category"] or "ALL").upper()
                if q_cat != "ALL" and c_cat != "ALL" and q_cat != c_cat:
                    sims[i] -= 0.25

        sorted_indices = np.argsort(sims)[::-1]
        best_sim = float(sims[sorted_indices[0]])

        # Evidence threshold: default 0.20 with hybrid scoring
        MIN_EVIDENCE_SIMILARITY = min_similarity if min_similarity is not None else 0.20
        if best_sim < MIN_EVIDENCE_SIMILARITY:
            return {
                "has_sufficient_evidence": False,
                "retrieval_status": "INSUFFICIENT_EVIDENCE",
                "evidence_passages": [],
                "top_similarity": best_sim,
                "primary_policy_id": None,
                "source_section_ids": [],
                "source_content_hashes": {},
                "rejection_reason": f"Top similarity score ({best_sim:.3f}) is below the required evidence threshold ({MIN_EVIDENCE_SIMILARITY:.2f}). Available documents do not provide sufficient evidence to answer."
            }

        # Select top-k relevant chunks that pass the minimum threshold
        relevant_chunks = []
        for idx in sorted_indices[:top_k]:
            if float(sims[idx]) >= MIN_EVIDENCE_SIMILARITY:
                item = dict(all_chunks[idx])
                item["similarity"] = round(float(sims[idx]), 4)
                relevant_chunks.append(item)

        # Detect Document Conflicts between top retrieved passages
        retrieval_status = "ANSWERED"
        if len(relevant_chunks) >= 2:
            chunk1, chunk2 = relevant_chunks[0], relevant_chunks[1]
            # Genuine conflict: different policies/versions for the SAME section/topic
            if (chunk1.get("policy_id") != chunk2.get("policy_id") and
                chunk1.get("heading", "").lower() == chunk2.get("heading", "").lower() and
                chunk2.get("similarity", 0) > 0.50):
                nums1 = set(re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?\b', chunk1["text"]))
                nums2 = set(re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?\b', chunk2["text"]))
                if nums1 and nums2 and not nums1.intersection(nums2):
                    retrieval_status = "DOCUMENT_CONFLICT"

        # Collect granular dependencies
        source_section_ids = [c["section_id"] for c in relevant_chunks[:2]]
        source_content_hashes = {c["section_id"]: c.get("content_hash", "") for c in relevant_chunks[:2]}

        return {
            "has_sufficient_evidence": len(relevant_chunks) > 0 and retrieval_status != "DOCUMENT_CONFLICT",
            "retrieval_status": retrieval_status,
            "evidence_passages": relevant_chunks,
            "top_similarity": best_sim,
            "primary_policy_id": relevant_chunks[0]["policy_id"] if relevant_chunks else None,
            "source_section_ids": source_section_ids,
            "source_content_hashes": source_content_hashes,
            "rejection_reason": "Conflicting evidence detected across retrieved policy documents." if retrieval_status == "DOCUMENT_CONFLICT" else None
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
                "source_section_ids": [],
                "source_content_hashes": {},
                "supporting_evidence_references": []
            }

        top = evidence_passages[0]
        pol_id = top["policy_id"]
        pol_name = top["policy_name"]
        pol_ver = top.get("policy_version", "1.0")
        heading = top.get("heading", "Governing Clause")
        page_info = f", Page {top['page_number']}" if top.get("page_number") else ""
        
        answer_text = f"Under policy {pol_id} ({pol_name}) - Section: {heading}:\n\n{top['text']}"
        if len(evidence_passages) > 1 and evidence_passages[1]["policy_id"] == pol_id:
            sec2_heading = evidence_passages[1].get("heading", "Clause 2")
            answer_text += f"\n\nAdditionally ({sec2_heading}): {evidence_passages[1]['text']}"

        source_cit = f"Policy {pol_id} ({pol_name}, v{pol_ver}) - Section: {heading}{page_info} (Scope: {top.get('employee_category', 'ALL')})"

        source_section_ids = [p["section_id"] for p in evidence_passages[:2]]
        source_content_hashes = {p["section_id"]: p.get("content_hash", "") for p in evidence_passages[:2]}

        return {
            "answer": answer_text,
            "has_sufficient_evidence": True,
            "provider": "grounded_company_policy_engine",
            "model": "all-MiniLM-L6-v2-rag",
            "policy_id": pol_id,
            "policy_version": pol_ver,
            "source_document": pol_name,
            "source_citation": source_cit,
            "source_section_ids": source_section_ids,
            "source_content_hashes": source_content_hashes,
            "supporting_evidence_references": [source_cit]
        }

rag_service = DocumentRAGService()
