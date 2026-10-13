import json
import urllib.request
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import numpy as np

from app.core.config import settings
from app.models.entities import Policy, PolicyVersion
from app.ml.embeddings import embedding_service
from app.ml.policy_validation import normalize_text

class GroundedCompanyPolicyService:
    """
    Real-world Grounded Inference Service for Kaveri Tech Solutions Pvt. Ltd. (Chennai, Tamil Nadu).
    Strictly answers queries based on the company policies stored in the database.
    Zero mock data. If Grok or OpenAI API key is configured, uses it with strict grounding;
    otherwise executes local semantic retrieval across stored company policy documents.
    """
    def __init__(self):
        pass

    def generate_response(
        self,
        db: Session,
        query: str,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Fetch all active policies from the company database
        policies_query = db.query(Policy)
        if domain and domain.upper() in ["HR", "IT", "FINANCE"]:
            policies_query = policies_query.filter(Policy.domain == domain.upper())
        policies: List[Policy] = policies_query.all()

        if not policies:
            # Fallback to all policies if domain-filtered returned none
            policies = db.query(Policy).all()

        if not policies:
            return {
                "provider": "company_knowledge_engine",
                "model": "grounded-retriever-v1",
                "is_mock": False,
                "answer": "No company policy records are currently configured in the database. Please contact the Admin to upload policy documents."
            }

        # 2. Break policies into semantic chunks/clauses
        chunks = []
        for pol in policies:
            paragraphs = [p.strip() for p in pol.content.split("\n") if len(p.strip()) > 20]
            if not paragraphs:
                paragraphs = [pol.content.strip()]
            for p in paragraphs:
                chunks.append({
                    "policy_id": pol.policy_id,
                    "policy_name": pol.name,
                    "domain": pol.domain,
                    "jurisdiction": pol.jurisdiction,
                    "text": p
                })

        if not chunks:
            return {
                "provider": "company_knowledge_engine",
                "model": "grounded-retriever-v1",
                "is_mock": False,
                "answer": "No detailed policy clauses found in the company knowledge base."
            }

        # 3. Compute semantic similarity between query and policy chunks
        query_emb = embedding_service.encode(query, normalize=True).flatten()
        chunk_texts = [c["text"] for c in chunks]
        chunk_embs = embedding_service.encode(chunk_texts, normalize=True)
        
        sims = np.dot(chunk_embs, query_emb)
        top_indices = np.argsort(sims)[::-1][:3]
        
        best_sim = float(sims[top_indices[0]])
        relevant_chunks = [chunks[i] for i in top_indices if float(sims[i]) >= 0.40]
        
        if best_sim < 0.40 or not relevant_chunks:
            return {
                "provider": "company_knowledge_engine",
                "model": "grounded-retriever-v1",
                "is_mock": False,
                "answer": f"According to Kaveri Tech Solutions' corporate policy knowledge base, there are no documented guidelines matching '{query}'. Please verify with the HR or IT operations desk at the Chennai OMR headquarters."
            }

        top_chunk = relevant_chunks[0]

        # 4. Check if Grok (xAI) or OpenAI API is configured
        grok_api_key = getattr(settings, "GROK_API_KEY", "") or getattr(settings, "XAI_API_KEY", "")
        openai_api_key = getattr(settings, "OPENAI_API_KEY", "")
        
        grounding_context = "\n\n".join([
            f"Policy {c['policy_id']} ({c['policy_name']}) [{c['jurisdiction']}]:\n{c['text']}"
            for c in relevant_chunks
        ])

        # A) Grok API call if provided
        if grok_api_key:
            try:
                url = "https://api.x.ai/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {grok_api_key}"
                }
                payload = {
                    "model": "grok-beta",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are the official enterprise assistant for Kaveri Tech Solutions Pvt. Ltd., based in Chennai & Coimbatore, Tamil Nadu, India. "
                                "Answer the employee's inquiry strictly and accurately using ONLY the provided company policy excerpts below. "
                                "Do not invent policies or cite information outside these excerpts. Mention the policy code in your answer.\n\n"
                                f"Company Policy Excerpts:\n{grounding_context}"
                            )
                        },
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.1
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    answer = data["choices"][0]["message"]["content"]
                    return {
                        "provider": "grok_api",
                        "model": "grok-beta",
                        "is_mock": False,
                        "answer": answer
                    }
            except Exception as e:
                print(f"Grok API call failed: {e}. Falling back to local grounded synthesis.")

        # B) OpenAI API call if configured
        if openai_api_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_api_key}"
                }
                payload = {
                    "model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are the enterprise assistant for Kaveri Tech Solutions Pvt. Ltd., Tamil Nadu, India. "
                                "Answer strictly based on the following verified company policies. Reference the policy code.\n\n"
                                f"{grounding_context}"
                            )
                        },
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.1
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    answer = data["choices"][0]["message"]["content"]
                    return {
                        "provider": "openai",
                        "model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                        "is_mock": False,
                        "answer": answer
                    }
            except Exception as e:
                print(f"OpenAI call failed: {e}. Falling back to local grounded synthesis.")

        # C) High-accuracy Local Semantic Grounding (Zero Mock Data, Strictly Derived from Admin Policies)
        answer_text = (
            f"Under policy {top_chunk['policy_id']} ({top_chunk['policy_name']}):\n\n"
            f"{top_chunk['text']}"
        )
        if len(relevant_chunks) > 1 and relevant_chunks[1]["policy_id"] == top_chunk["policy_id"]:
            answer_text += f"\n\nAdditionally: {relevant_chunks[1]['text']}"

        top_pol = db.query(Policy).filter(Policy.policy_id == top_chunk["policy_id"]).first()
        pol_version = top_pol.current_version if top_pol else "1.0"

        return {
            "provider": "grounded_company_policy_engine",
            "model": "all-MiniLM-L6-v2-rag",
            "is_mock": False,
            "answer": answer_text,
            "policy_id": top_chunk["policy_id"],
            "policy_version": pol_version,
            "source_document": top_chunk["policy_name"],
            "source_citation": f"Clause from {top_chunk['policy_id']} (v{pol_version}): {top_chunk['text'][:180]}"
        }

llm_service = GroundedCompanyPolicyService()

