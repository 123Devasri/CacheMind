import re
import csv
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
import numpy as np

from app.core.config import settings
from app.models.entities import Policy, PolicyVersion, CachedEntry
from app.ml.embeddings import embedding_service
from app.ml.faiss_index import faiss_service
from app.ml.policy_validation import normalize_text, extract_policy_conditions

# Common enterprise topic keywords mapped to query templates
TOPIC_KEYWORDS = {
    "annual leave": ("annual leave entitlement", "Privilege or Annual leave days"),
    "privilege leave": ("privilege leave", "Privilege Leave days"),
    "sick leave": ("sick leave", "Sick Leave allocation"),
    "casual leave": ("casual leave", "Casual Leave days"),
    "maternity": ("maternity leave", "paid maternity leave duration and benefits"),
    "paternity": ("paternity leave", "paid paternity leave duration"),
    "bereavement": ("bereavement leave", "compassionate or bereavement leave"),
    "work from home": ("work from home", "remote work and WFH policy"),
    "remote work": ("remote work", "remote working guidelines"),
    "hybrid": ("hybrid working", "hybrid work schedule"),
    "broadband": ("broadband reimbursement", "monthly broadband and internet allowance"),
    "internet": ("internet allowance", "Wi-Fi and internet reimbursement"),
    "cafeteria": ("cafeteria facilities", "campus cafeteria and meal subsidies"),
    "meal allowance": ("meal allowance", "digital meal allowance and food vouchers"),
    "food voucher": ("food voucher card", "Pluxee or Sodexo food card entitlement"),
    "dinner": ("late evening dinner", "complimentary dinner for extended shifts"),
    "cab": ("cab drop facilities", "corporate cab transportation for night shifts"),
    "travel": ("travel allowance", "business travel and daily per diem"),
    "hotel": ("hotel accommodation", "travel lodging and hotel allowance"),
    "relocation": ("relocation grant", "employee relocation benefits and packing assistance"),
    "notice period": ("notice period", "resignation notice period requirements"),
    "probation": ("probation period", "probation duration and confirmation terms"),
    "health insurance": ("group health insurance", "medical insurance coverage"),
    "mediclaim": ("mediclaim insurance", "mediclaim hospitalization benefits"),
    "working hours": ("office working hours", "standard business hours and shift schedules"),
    "laptop": ("company laptop", "IT hardware and company equipment guidelines"),
    "byod": ("BYOD policy", "personal device usage on company networks")
}

def clean_clause_text(text: str) -> str:
    """Cleans up clause text for question generation and grounded answers."""
    cleaned = re.sub(r'\s+', ' ', text).strip()
    # Remove leading numbering like "1. ", "Clause 2: ", "- "
    cleaned = re.sub(r'^(?:(?:\d+[\.\)]|\-|\*|Clause\s+\d+[:\.]?|Section\s+\d+[:\.]?)\s*)+', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def split_policy_into_clauses(content: str) -> List[str]:
    """
    Extracts semantic clauses and paragraphs from policy content.
    Splits by paragraph, bullet point, or multi-sentence blocks.
    """
    # Split on double or single newlines
    raw_lines = [clean_clause_text(p) for p in re.split(r'\n+', content) if len(clean_clause_text(p)) > 20]
    
    clauses = []
    for block in raw_lines:
        if len(block) > 250:
            # Cleanly split on sentence boundaries (period/exclamation/question mark followed by space and uppercase letter)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z])', block) if len(s.strip()) > 25]
            if len(sentences) > 1:
                clauses.extend(sentences)
            else:
                clauses.append(block)
        else:
            clauses.append(block)

    return clauses

def extract_clause_topic(clause: str, policy_name: str) -> Tuple[str, str]:
    """
    Extracts the topic keyword and a clean descriptive topic phrase for question formulation.
    """
    lower_clause = clause.lower()
    
    # Check known keywords
    for kw, (short_topic, descriptive) in TOPIC_KEYWORDS.items():
        if kw in lower_clause:
            return short_topic, descriptive
            
    # Fallback: extract key nouns or first meaningful segment
    words = [w for w in re.findall(r'[a-zA-Z]{3,}', lower_clause) if w not in {"the", "and", "for", "with", "all", "are", "under", "per", "from", "shall", "will", "this", "that"}]
    if len(words) >= 2:
        topic = f"{words[0]} {words[1]}"
        return topic, f"policy on {topic}"
        
    clean_name = policy_name.replace("Policy", "").strip()
    return clean_name.lower(), f"{clean_name} guidelines"

def generate_qa_pairs_for_clause(clause: str, policy: Policy) -> List[Dict[str, Any]]:
    """
    Generates high-accuracy natural questions and authoritative grounded answers for a policy clause.
    """
    short_topic, desc_topic = extract_clause_topic(clause, policy.name)
    conditions = extract_policy_conditions(clause, default_domain=policy.domain)
    
    qa_list = []
    
    # Construct grounded answer referencing policy ID and name
    grounded_answer = (
        f"Under policy {policy.policy_id} ({policy.name}):\n\n"
        f"{clause}"
    )

    # Question Variant 1: Direct Topic Inquiry
    q1 = f"What is the company policy regarding {desc_topic}?"
    qa_list.append({
        "question": q1,
        "answer": grounded_answer,
        "topic": short_topic
    })

    # Question Variant 2: Specific Entitlement / Limit Inquiry (if numbers exist)
    nums = conditions.numerical_limits or {}
    if nums:
        unit = list(nums.keys())[0]
        val = nums[unit]
        if unit in ["days", "weeks", "months", "hours"]:
            q2 = f"How many {unit} of {short_topic} are provided to employees under {policy.policy_id}?"
        elif unit in ["inr", "rs", "usd", "amount"]:
            q2 = f"What is the maximum {short_topic} allowance or reimbursement amount under {policy.policy_id}?"
        elif unit == "percent":
            q2 = f"What percentage of {short_topic} is covered under {policy.policy_id}?"
        else:
            q2 = f"What is the entitlement limit for {short_topic} under policy {policy.policy_id}?"
            
        qa_list.append({
            "question": q2,
            "answer": grounded_answer,
            "topic": short_topic
        })
    else:
        # Rules / guidelines inquiry
        q2 = f"What are the official rules and guidelines concerning {short_topic} at Kaveri Tech Solutions?"
        qa_list.append({
            "question": q2,
            "answer": grounded_answer,
            "topic": short_topic
        })

    # Question Variant 3: Conversational Employee Query
    if policy.employee_category and policy.employee_category != "ALL":
        cat_label = policy.employee_category.lower().replace("_", " ")
        q3 = f"Can {cat_label} employees claim or receive {short_topic} in {policy.jurisdiction.title()}?"
    else:
        q3 = f"How does the {short_topic} policy work for employees in {policy.jurisdiction.title()}?"
        
    qa_list.append({
        "question": q3,
        "answer": grounded_answer,
        "topic": short_topic
    })

    # Question Variant 4: Policy Code Specific Query
    q4 = f"What is stated in policy {policy.policy_id} regarding {short_topic}?"
    qa_list.append({
        "question": q4,
        "answer": grounded_answer,
        "topic": short_topic
    })

    return qa_list

def generate_qa_pairs_for_policy(policy: Policy) -> List[Dict[str, Any]]:
    """
    Parses a policy document into comprehensive Question-Answer pairs.
    """
    clauses = split_policy_into_clauses(policy.content)
    if not clauses:
        clauses = [clean_clause_text(policy.content)]

    all_pairs = []
    seen_questions = set()

    for clause in clauses:
        clause_qas = generate_qa_pairs_for_clause(clause, policy)
        for item in clause_qas:
            norm_q = normalize_text(item["question"])
            if norm_q not in seen_questions:
                seen_questions.add(norm_q)
                conds = extract_policy_conditions(clause, default_domain=policy.domain)
                all_pairs.append({
                    "question": item["question"],
                    "normalized_question": norm_q,
                    "answer": item["answer"],
                    "policy_id": policy.policy_id,
                    "policy_version": policy.current_version or "1.0",
                    "domain": policy.domain or "HR",
                    "jurisdiction": policy.jurisdiction or "INDIA",
                    "employee_category": policy.employee_category or "ALL",
                    "numerical_limits": conds.numerical_limits or {},
                    "is_verified": True,
                    "is_active": True
                })

    return all_pairs

def sync_policy_qa_to_cache(policy: Policy, db: Session) -> int:
    """
    Converts a single newly created or updated policy into Q&A pairs,
    updates CachedEntry records in DB, and re-indexes them into FAISS.
    """
    print(f"[PolicyQAService] Generating Q&A pairs for policy: {policy.policy_id} ({policy.name})...")
    
    # 1. Invalidate or deactivate older cache entries for this policy if updating
    db.query(CachedEntry).filter(
        CachedEntry.policy_id == policy.policy_id
    ).update({"is_active": False}, synchronize_session=False)
    db.commit()

    # 2. Generate new Q&A pairs
    qa_pairs = generate_qa_pairs_for_policy(policy)
    if not qa_pairs:
        print(f"[PolicyQAService] No Q&A pairs generated for policy {policy.policy_id}.")
        return 0

    # 3. Insert new verified CachedEntry records
    for item in qa_pairs:
        # Check if identical question already exists in db
        existing = db.query(CachedEntry).filter(
            CachedEntry.normalized_question == item["normalized_question"]
        ).first()

        if existing:
            existing.answer = item["answer"]
            existing.policy_id = item["policy_id"]
            existing.policy_version = item["policy_version"]
            existing.domain = item["domain"]
            existing.jurisdiction = item["jurisdiction"]
            existing.employee_category = item["employee_category"]
            existing.numerical_limits = item["numerical_limits"]
            existing.is_verified = True
            existing.is_active = True
        else:
            entry = CachedEntry(
                question=item["question"],
                normalized_question=item["normalized_question"],
                answer=item["answer"],
                policy_id=item["policy_id"],
                policy_version=item["policy_version"],
                domain=item["domain"],
                jurisdiction=item["jurisdiction"],
                employee_category=item["employee_category"],
                numerical_limits=item["numerical_limits"],
                is_verified=True,
                is_active=True,
                hit_count=0
            )
            db.add(entry)
            
    db.commit()

    # 4. Re-index all active CachedEntry vectors in FAISS
    reindex_all_active_cache_vectors(db)

    print(f"[PolicyQAService] Successfully indexed {len(qa_pairs)} Q&A pairs for {policy.policy_id}.")
    return len(qa_pairs)

def reindex_all_active_cache_vectors(db: Session) -> int:
    """
    Scans all active CachedEntry records in DB, embeds questions with all-MiniLM-L6-v2,
    and rebuilds the FAISS index with accurate IDs.
    """
    active_entries: List[CachedEntry] = db.query(CachedEntry).filter(
        CachedEntry.is_active == True,
        CachedEntry.is_verified == True
    ).order_by(CachedEntry.created_at.asc()).all()

    if not active_entries:
        print("[PolicyQAService] No active cache entries to index.")
        return 0

    # Reset faiss_id to avoid unique constraint collisions during batch update
    db.query(CachedEntry).update({CachedEntry.faiss_id: None})
    db.commit()

    entry_ids = [e.id for e in active_entries]
    questions_to_embed = [e.normalized_question or normalize_text(e.question) for e in active_entries]

    vectors = embedding_service.encode(questions_to_embed, normalize=True)
    count = faiss_service.rebuild_index(entry_ids, vectors)

    # Link faiss_id back in DB
    for idx, e in enumerate(active_entries):
        e.faiss_id = idx
    db.commit()

    print(f"[PolicyQAService] Rebuilt FAISS index with {count} active Q&A vectors.")
    return count

def sync_all_policies_to_cache_and_training(db: Session) -> Dict[str, Any]:
    """
    Complete synchronization function:
    1. Iterates over all active policies in DB.
    2. Generates Q&A pairs for any policy missing in cache or needing refresh.
    3. Rebuilds FAISS index.
    4. Enriches synthetic training datasets (positive & negative pairs) with active policy clauses.
    """
    policies: List[Policy] = db.query(Policy).filter(Policy.status == "active").all()
    print(f"[PolicyQAService] Synchronizing {len(policies)} active policies to Cache and Training Datasets...")

    total_qa_generated = 0
    training_pairs_to_add = []

    for pol in policies:
        # Check active cache entries count for this policy
        cached_count = db.query(CachedEntry).filter(
            CachedEntry.policy_id == pol.policy_id,
            CachedEntry.is_active == True
        ).count()

        # If policy has few or no cached entries, generate and store them
        if cached_count < 3:
            qa_pairs = generate_qa_pairs_for_policy(pol)
            for item in qa_pairs:
                existing = db.query(CachedEntry).filter(
                    CachedEntry.normalized_question == item["normalized_question"]
                ).first()

                if existing:
                    existing.answer = item["answer"]
                    existing.policy_id = item["policy_id"]
                    existing.policy_version = item["policy_version"]
                    existing.domain = item["domain"]
                    existing.jurisdiction = item["jurisdiction"]
                    existing.employee_category = item["employee_category"]
                    existing.numerical_limits = item["numerical_limits"]
                    existing.is_verified = True
                    existing.is_active = True
                else:
                    entry = CachedEntry(
                        question=item["question"],
                        normalized_question=item["normalized_question"],
                        answer=item["answer"],
                        policy_id=item["policy_id"],
                        policy_version=item["policy_version"],
                        domain=item["domain"],
                        jurisdiction=item["jurisdiction"],
                        employee_category=item["employee_category"],
                        numerical_limits=item["numerical_limits"],
                        is_verified=True,
                        is_active=True,
                        hit_count=0
                    )
                    db.add(entry)
            db.commit()
            total_qa_generated += len(qa_pairs)

        # Generate training pairs (positives & hard negatives) for model retraining
        clauses = split_policy_into_clauses(pol.content)
        for clause in clauses[:5]:
            short_top, desc_top = extract_clause_topic(clause, pol.name)
            conds = extract_policy_conditions(clause, default_domain=pol.domain)
            nums = conds.numerical_limits or {}

            # Positive paraphrase pair
            p_q1 = f"What is the company policy regarding {desc_top}?"
            p_q2 = f"Could you explain the employee guidelines for {desc_top} under {pol.policy_id}?"
            training_pairs_to_add.append({
                "q1": p_q1,
                "q2": p_q2,
                "label": 1,
                "group": f"{pol.policy_id.lower()}_positive_pair",
                "split": "train"
            })

            # Negative numerical contrast if numbers present
            if nums:
                unit = list(nums.keys())[0]
                val = nums[unit]
                wrong_val = val * 2 if val > 0 else 5
                training_pairs_to_add.append({
                    "q1": f"Is the {short_top} limit {val} {unit} under {pol.policy_id}?",
                    "q2": f"Is the {short_top} limit {wrong_val} {unit} under {pol.policy_id}?",
                    "label": 0,
                    "group": f"{pol.policy_id.lower()}_numeric_neg",
                    "split": "train"
                })

            # Negative category contrast
            training_pairs_to_add.append({
                "q1": f"Do full-time employees qualify for {short_top} under {pol.policy_id}?",
                "q2": f"Do external third-party contractors qualify for {short_top} under {pol.policy_id}?",
                "label": 0,
                "group": f"{pol.policy_id.lower()}_category_neg",
                "split": "train"
            })

    # Re-index all active cache entries into FAISS
    indexed_vectors = reindex_all_active_cache_vectors(db)

    # Append new training pairs to split CSV if present
    split_csv_path = settings.DATASETS_DIR / "enterprise_policy_pairs_split.csv"
    if split_csv_path.exists() and training_pairs_to_add:
        existing_rows = []
        with open(split_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or ["q1", "q2", "label", "group", "split"]
            existing_rows = list(reader)

        existing_pairs_set = {(r["q1"], r["q2"]) for r in existing_rows}
        new_valid = [r for r in training_pairs_to_add if (r["q1"], r["q2"]) not in existing_pairs_set]

        if new_valid:
            with open(split_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(new_valid)
            print(f"[PolicyQAService] Added {len(new_valid)} synthetic training pairs to {split_csv_path.name}")

    return {
        "status": "success",
        "total_qa_generated": total_qa_generated,
        "indexed_vectors": indexed_vectors,
        "training_pairs_added": len(training_pairs_to_add)
    }
