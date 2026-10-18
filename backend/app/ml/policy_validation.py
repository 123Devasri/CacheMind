import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PolicyConditions(BaseModel):
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    domain: Optional[str] = None # HR, IT, FINANCE
    jurisdiction: Optional[str] = None # US, INDIA, UK, GLOBAL
    employee_category: Optional[str] = None # FULL_TIME, CONTRACTOR, INTERN, ALL
    numerical_limits: Dict[str, float] = Field(default_factory=dict) # e.g. {"days": 20.0, "usd": 500.0}
    is_negated: bool = False
    action_type: Optional[str] = None # reimbursement, leave, wfh, device, termination

def normalize_text(text: str) -> str:
    """Normalize text: strip, lowercase, collapse spaces, standard punctuation cleanup."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_policy_conditions(text: str, default_domain: Optional[str] = None) -> PolicyConditions:
    """
    Deterministically extracts structured policy conditions from question text.
    Handles jurisdiction, employment category, numeric limits, domains, and negations.
    """
    clean = normalize_text(text)
    conditions = PolicyConditions()
    
    # 1. Domain detection
    if default_domain:
        conditions.domain = default_domain.upper()
    elif any(k in clean for k in ["leave", "vacation", "pto", "holiday", "sick", "bereavement", "maternity", "paternity"]):
        conditions.domain = "HR"
    elif any(k in clean for k in ["laptop", "vpn", "password", "software", "hardware", "wifi", "monitor", "it support"]):
        conditions.domain = "IT"
    elif any(k in clean for k in ["expense", "reimburse", "per diem", "allowance", "travel", "flight", "hotel", "mileage"]):
        conditions.domain = "FINANCE"
    else:
        conditions.domain = "GENERAL"

    # 2. Jurisdiction extraction (using word boundaries)
    if re.search(r'\b(india|inr|rupees|tamil nadu|tamilnadu|chennai|coimbatore|madurai|trichy|salem|bangalore|mumbai|delhi|hyderabad)\b', clean):
        conditions.jurisdiction = "INDIA"
    elif re.search(r'\b(united states|usa|us|u\.s\.|dollar|usd|\$)\b', clean) or '$' in clean:
        conditions.jurisdiction = "US"
    elif re.search(r'\b(united kingdom|uk|u\.k\.|britain|london|gbp|pound)\b', clean):
        conditions.jurisdiction = "UK"
    else:
        conditions.jurisdiction = "GLOBAL"

    # 3. Employee Category extraction
    if any(k in clean for k in ["contractor", "contract", "vendor", "freelance", "temp"]):
        conditions.employee_category = "CONTRACTOR"
    elif any(k in clean for k in ["intern", "trainee", "internship"]):
        conditions.employee_category = "INTERN"
    elif any(k in clean for k in ["full-time", "full time", "permanent", "salaried", "fte", "regular employee"]):
        conditions.employee_category = "FULL_TIME"
    elif any(k in clean for k in ["part-time", "part time"]):
        conditions.employee_category = "PART_TIME"
    else:
        conditions.employee_category = "ALL"

    # 4. Numerical limits extraction
    # Match numbers with units or currency
    day_matches = re.findall(r'(\d+)\s*(?:days?|day|working days?)', clean)
    if day_matches:
        conditions.numerical_limits["days"] = float(day_matches[0])
        
    dollar_matches = re.findall(r'(?:\$|usd\s*|dollars?\s*)(\d+(?:\.\d+)?)', clean)
    if dollar_matches:
        conditions.numerical_limits["usd"] = float(dollar_matches[0])
        
    inr_matches = re.findall(r'(?:rs\.?|inr\s*|rupees?\s*)(\d+(?:\.\d+)?)', clean)
    if inr_matches:
        conditions.numerical_limits["inr"] = float(inr_matches[0])
        
    # Generic numbers if no specific unit found
    if not conditions.numerical_limits:
        generic_numbers = re.findall(r'\b(\d+)\b', clean)
        if generic_numbers:
            conditions.numerical_limits["numeric_value"] = float(generic_numbers[0])

    # 5. Negation check
    if any(k in clean for k in ["not ", "n't ", "never", "cannot", "can't", "prohibited", "disallowed", "excluded"]):
        conditions.is_negated = True

    # 6. Policy version reference check
    ver_match = re.search(r'(?:version|v\.?|ver\.?)\s*(\d+(?:\.\d+)?)', clean)
    if ver_match:
        conditions.policy_version = ver_match.group(1)

    return conditions

def validate_condition_safety(query_cond: PolicyConditions, candidate_cond: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Mandatory Deterministic Safety Check:
    Returns (is_safe: bool, mismatch_reasons: List[str]).
    A cache hit is strictly forbidden if any mandatory constraint mismatches.
    """
    reasons = []

    # 1. Jurisdiction Check:
    cand_jur = (candidate_cond.get("jurisdiction") or "GLOBAL").upper()
    query_jur = (query_cond.jurisdiction or "GLOBAL").upper()
    if query_jur != "GLOBAL" and cand_jur != "GLOBAL" and query_jur != cand_jur:
        reasons.append(f"Jurisdiction mismatch: query requires '{query_jur}' but cached candidate is for '{cand_jur}'.")

    # 2. Employee Category Check:
    cand_cat = (candidate_cond.get("employee_category") or "ALL").upper()
    query_cat = (query_cond.employee_category or "ALL").upper()
    if query_cat != "ALL" and cand_cat != "ALL" and query_cat != cand_cat:
        reasons.append(f"Employee category mismatch: query is for '{query_cat}' but candidate is for '{cand_cat}'.")

    # 3. Numerical limit check:
    cand_nums = candidate_cond.get("numerical_limits") or {}
    for k, q_val in query_cond.numerical_limits.items():
        if k in cand_nums:
            c_val = float(cand_nums[k])
            if abs(q_val - c_val) > 1e-4:
                reasons.append(f"Numerical limit mismatch on {k}: query states {q_val} while cache has {c_val}.")

    # 4. Negation mismatch:
    cand_neg = candidate_cond.get("is_negated", False)
    if query_cond.is_negated != cand_neg:
        reasons.append("Negation mismatch: one statement is affirmative while the other is negative.")

    # 5. Policy version check:
    cand_ver = str(candidate_cond.get("policy_version", ""))
    if query_cond.policy_version and cand_ver and query_cond.policy_version != cand_ver:
        reasons.append(f"Policy version mismatch: query explicitly refers to version '{query_cond.policy_version}' while cache record is '{cand_ver}'.")

    is_safe = len(reasons) == 0
    return is_safe, reasons
