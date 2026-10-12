import re
import numpy as np
from typing import Dict, Any, List
from app.ml.policy_validation import PolicyConditions, normalize_text

def compute_jaccard_similarity(text1: str, text2: str) -> float:
    tokens1 = set(re.findall(r'\b\w+\b', normalize_text(text1)))
    tokens2 = set(re.findall(r'\b\w+\b', normalize_text(text2)))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return float(len(intersection) / len(union))

def compute_relative_length_diff(text1: str, text2: str) -> float:
    len1 = len(text1.strip())
    len2 = len(text2.strip())
    max_len = max(len1, len2)
    if max_len == 0:
        return 0.0
    return abs(len1 - len2) / max_len

def build_pair_features(
    q1_text: str,
    q2_text: str,
    cosine_sim: float,
    q1_cond: PolicyConditions,
    q2_cond_dict: Dict[str, Any]
) -> np.ndarray:
    """
    Constructs an explicit 8-dimensional feature vector for the binary equivalence classifier:
    1. Cosine similarity between query embeddings [0, 1]
    2. Token Jaccard similarity [0, 1]
    3. Relative string length difference [0, 1]
    4. Domain match flag (1 if match, 0 if mismatch)
    5. Jurisdiction match flag (1 if match, 0 if mismatch)
    6. Employee category match flag (1 if match, 0 if mismatch)
    7. Numerical limit conflict indicator (1 if mismatch, 0 if consistent/absent)
    8. Negation conflict indicator (1 if mismatch, 0 if consistent)
    """
    jaccard = compute_jaccard_similarity(q1_text, q2_text)
    rel_len = compute_relative_length_diff(q1_text, q2_text)
    
    # Domain match
    cand_domain = (q2_cond_dict.get("domain") or "GENERAL").upper()
    query_domain = (q1_cond.domain or "GENERAL").upper()
    domain_match = 1.0 if (query_domain == "GENERAL" or cand_domain == "GENERAL" or query_domain == cand_domain) else 0.0
    
    # Jurisdiction match
    cand_jur = (q2_cond_dict.get("jurisdiction") or "GLOBAL").upper()
    query_jur = (q1_cond.jurisdiction or "GLOBAL").upper()
    jur_match = 1.0 if (query_jur == "GLOBAL" or cand_jur == "GLOBAL" or query_jur == cand_jur) else 0.0
    
    # Category match
    cand_cat = (q2_cond_dict.get("employee_category") or "ALL").upper()
    query_cat = (q1_cond.employee_category or "ALL").upper()
    cat_match = 1.0 if (query_cat == "ALL" or cand_cat == "ALL" or query_cat == cand_cat) else 0.0
    
    # Numerical conflict
    cand_nums = q2_cond_dict.get("numerical_limits") or {}
    num_conflict = 0.0
    for k, q_val in q1_cond.numerical_limits.items():
        if k in cand_nums and abs(q_val - float(cand_nums[k])) > 1e-4:
            num_conflict = 1.0
            break
            
    # Negation conflict
    cand_neg = bool(q2_cond_dict.get("is_negated", False))
    neg_conflict = 1.0 if (q1_cond.is_negated != cand_neg) else 0.0
    
    features = np.array([
        float(cosine_sim),
        float(jaccard),
        float(rel_len),
        float(domain_match),
        float(jur_match),
        float(cat_match),
        float(num_conflict),
        float(neg_conflict)
    ], dtype=np.float32)
    
    return features

FEATURE_NAMES = [
    "cosine_similarity",
    "token_jaccard_similarity",
    "relative_length_diff",
    "domain_match",
    "jurisdiction_match",
    "employee_category_match",
    "numerical_conflict",
    "negation_conflict"
]
