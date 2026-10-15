import re
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.core.config import settings
from app.ml.naive_bayes_router import naive_bayes_router
from app.ml.policy_validation import extract_policy_conditions

# Pure greetings that shouldn't trigger policy document search
PURE_GREETINGS = [
    r"^(hi|hello|hey|heyy|howdy|greetings|vanakkam|namaste)[!?.]*$",
    r"^(hi|hello|hey)\s+(there|assistant|bot|cachemind|team)[!?.]*$",
    r"^(good\s+(morning|afternoon|evening|day))[!?.]*$",
    r"^(how\s+are\s+you|how\s+r\s+u|how\s+do\s+you\s+do|what'?s\s+up)[!?.]*$",
    r"^(hi|hello|hey)[,\s]+(good\s+(morning|afternoon|evening|day)|how\s+are\s+you|how\s+r\s+u|hope\s+you\s+are\s+well)[!?.]*$"
]

# Conversational intros and filler phrases
PREFIX_FILLERS = [
    r"^(hi|hello|hey|greetings|vanakkam|namaste)[,\s]+",
    r"^(good\s+(morning|afternoon|evening|day))[,\s]+",
    r"^(how\s+are\s+you|hope\s+you\s+are\s+doing\s+well|hope\s+all\s+is\s+well)[,?\s]+",
    r"^(can\s+you\s+(please\s+)?tell\s+me|could\s+you\s+(please\s+)?tell\s+me|please\s+tell\s+me|tell\s+me|pls\s+tell\s+me)\s+(about\s+)?",
    r"^(i\s+need\s+to\s+know\s+(about\s+)?|i\s+want\s+to\s+know\s+(about\s+)?|i\s+would\s+like\s+to\s+know\s+(about\s+)?)",
    r"^(i\s+would\s+like\s+to\s+ask|i\s+just\s+wanted\s+to\s+ask|i\s+wanted\s+to\s+ask\s+(about\s+)?)",
    r"^(could\s+someone\s+clarify|can\s+you\s+clarify|could\s+you\s+explain|please\s+explain)\s+(about\s+)?",
    r"^(can\s+you\s+help\s+me\s+(with|understand)|help\s+me\s+understand|i\s+am\s+looking\s+for\s+info(rmation)?\s+on)\s+",
    r"^(just\s+wondering\s+about|quick\s+question\s+(regarding|about)|quick\s+question)\s+",
    r"^(can\s+you\s+let\s+me\s+know|pls\s+let\s+me\s+know|please\s+let\s+me\s+know)\s+(about\s+)?"
]

# Trailing polite fillers
SUFFIX_FILLERS = [
    r"[,\s]+(please|pls|asap|urgently|thanks|thank\s+you|thanks\s+in\s+advance)[!?.]*$"
]

# Common typographical errors in corporate policy inquiries
COMMON_TYPOS = {
    "polcy": "policy",
    "polices": "policies",
    "reimbursment": "reimbursement",
    "reimbersement": "reimbursement",
    "elgible": "eligible",
    "eligiblity": "eligibility",
    "leav": "leave",
    "leaves": "leave",
    "maternty": "maternity",
    "paternty": "paternity",
    "vacatn": "vacation",
    "allowence": "allowance",
    "allowences": "allowances",
    "insurence": "insurance",
    "insurrance": "insurance",
    "hospitlization": "hospitalization",
    "permenant": "permanent",
    "contarctor": "contractor"
}

ACRONYMS_FILE = settings.BASE_DIR / "data" / "dictionaries" / "enterprise_acronyms.json"
ACRONYM_MAP = {}
if ACRONYMS_FILE.exists():
    try:
        with open(ACRONYMS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            ACRONYM_MAP = data.get("acronyms", {})
    except Exception as e:
        print(f"Error loading acronyms: {e}")

def correct_typos(text: str) -> tuple[str, list]:
    """Corrects unambiguous spelling errors in corporate policy vocabulary."""
    corrected = text
    applied = []
    tokens = re.findall(r'\b[a-zA-Z]+\b', text)
    for tok in tokens:
        lower = tok.lower()
        if lower in COMMON_TYPOS:
            rep = COMMON_TYPOS[lower]
            pattern = r'\b' + re.escape(tok) + r'\b'
            corrected = re.sub(pattern, rep, corrected, flags=re.IGNORECASE)
            applied.append(f"{tok} -> {rep}")
    return corrected, applied

def expand_enterprise_acronyms(text: str) -> tuple[str, list]:
    """Expands enterprise acronyms like WFH -> work from home, PL -> privilege leave."""
    expanded = text
    applied = []
    tokens = re.findall(r'\b[a-zA-Z]+\b', text)
    for tok in tokens:
        lower_tok = tok.lower()
        if lower_tok in ACRONYM_MAP:
            replacement = ACRONYM_MAP[lower_tok]
            # Avoid expanding if already followed or preceded by the expansion
            if replacement.lower() in text.lower():
                continue
            pattern = r'\b' + re.escape(tok) + r'\b'
            expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
            applied.append(f"{tok} -> {replacement}")
    return expanded, applied

def format_natural_question(text: str) -> str:
    """
    Ensures grammatical question phrasing without introducing nonsensical constructs
    like 'What is the policy regarding explain...'.
    """
    clean = text.strip()
    if not clean:
        return clean

    question_starters = [
        "what", "how", "when", "where", "why", "who", "which",
        "is", "are", "do", "does", "can", "could", "may", "will", "must", "should"
    ]
    words = clean.split()
    first_word = words[0].lower() if words else ""

    # If it already starts with a question word, just ensure sentence capitalization and '?'
    if first_word in question_starters:
        return f"{clean[0].upper()}{clean[1:].rstrip('?.!')}?"

    # Handle imperative verbs cleanly
    imperative_match = re.match(r'^(explain|describe|clarify|detail|outline|summarize)\s+(about\s+|the\s+|our\s+)?', clean, re.IGNORECASE)
    if imperative_match:
        subject = clean[imperative_match.end():].strip().rstrip('?.!')
        if subject:
            # e.g., 'explain network project' -> 'What is the network project policy?' or 'What is the network project?'
            if any(k in subject.lower() for k in ["policy", "procedure", "guideline", "rule"]):
                return f"What is the {subject}?"
            return f"What is the policy regarding {subject}?"

    # Handle bare topics like 'maternity leave' or 'travel expenses'
    bare_topic = re.sub(r'^(the|our|about|regarding)\s+', '', clean, flags=re.IGNORECASE).strip().rstrip('?.!')
    if any(k in bare_topic.lower() for k in ["policy", "guideline", "rule", "procedure"]):
        return f"What is the {bare_topic}?"
    return f"What is the policy regarding {bare_topic}?"

def optimize_user_query(raw_query: str) -> Dict[str, Any]:
    """
    Robust Query Optimization:
    1. Detects pure conversational greetings (e.g. 'hi', 'hello', 'good morning')
    2. Strips conversational fillers and opening pleasantries
    3. Corrects common domain spelling typos
    4. Expands enterprise acronyms (WFH -> work from home)
    5. Formulates grammatically clean question while strictly preserving numbers,
       dates, jurisdictions, employee categories, and negations.
    6. Uses Naïve Bayes to classify domain.
    """
    if not raw_query or not raw_query.strip():
        return {
            "is_pure_greeting": False,
            "is_optimized": False,
            "original_query": raw_query or "",
            "optimized_query": raw_query or "",
            "removed_filler": [],
            "expanded_acronyms": [],
            "predicted_domain": "HR",
            "domain_confidence": 0.5,
            "status": "EMPTY"
        }

    original = raw_query.strip()
    norm = original.lower().strip()
    norm_no_punct = re.sub(r'[?!.,;:]+', '', norm).strip()

    # 1. Pure greeting check
    for g_pat in PURE_GREETINGS:
        if re.match(g_pat, norm_no_punct, flags=re.IGNORECASE):
            return {
                "is_pure_greeting": True,
                "is_optimized": False,
                "original_query": original,
                "optimized_query": original,
                "removed_filler": [],
                "expanded_acronyms": [],
                "predicted_domain": "HR",
                "domain_confidence": 0.5,
                "status": "GREETING"
            }

    working = original
    removed = []

    # 2. Strip prefix fillers
    changed = True
    while changed:
        changed = False
        for p_pat in PREFIX_FILLERS:
            m = re.match(p_pat, working, flags=re.IGNORECASE)
            if m:
                matched_str = m.group(0).strip(" ,?;:")
                if matched_str and matched_str not in removed:
                    removed.append(matched_str)
                working = working[m.end():].strip()
                changed = True

    # Strip suffix fillers
    for s_pat in SUFFIX_FILLERS:
        m = re.search(s_pat, working, flags=re.IGNORECASE)
        if m:
            matched_str = m.group(0).strip(" ,?;:")
            if matched_str and matched_str not in removed:
                removed.append(matched_str)
            working = re.sub(s_pat, "", working, flags=re.IGNORECASE).strip()

    # 3. Correct typos
    working, applied_typos = correct_typos(working)

    # 4. Expand enterprise acronyms
    working, applied_acronyms = expand_enterprise_acronyms(working)

    # Clean whitespace & punctuation
    working = re.sub(r'^[?!.,;:\s]+', '', working)
    working = re.sub(r'\s+', ' ', working).strip()

    # Fallback to original if query became too short
    if len(working) < 3:
        return {
            "is_pure_greeting": False,
            "is_optimized": False,
            "original_query": original,
            "optimized_query": original,
            "removed_filler": [],
            "expanded_acronyms": [],
            "predicted_domain": "HR",
            "domain_confidence": 0.5,
            "status": "UNCHANGED"
        }

    # 5. Format natural question
    candidate = format_natural_question(working)

    # Safety check: Verify that critical conditions, numbers, and negations were NOT lost
    orig_cond = extract_policy_conditions(original)
    cand_cond = extract_policy_conditions(candidate)

    if orig_cond.is_negated != cand_cond.is_negated or orig_cond.numerical_limits != cand_cond.numerical_limits:
        # Rewriting altered critical numerical or negation logic; safely keep original
        candidate = f"{original[0].upper()}{original[1:].rstrip('?.!')}?"

    # Domain classification
    pred_domain, domain_conf, domain_probs = naive_bayes_router.predict_domain(candidate)

    # Only flag as optimized if there is a substantive change (filler removed, typos fixed, or acronyms expanded)
    is_substantive = bool(removed or applied_acronyms or applied_typos)
    if not is_substantive and candidate.lower().rstrip('?.') == original.lower().rstrip('?.'):
        is_substantive = False

    return {
        "is_pure_greeting": False,
        "is_optimized": is_substantive,
        "original_query": original,
        "optimized_query": candidate,
        "removed_filler": removed,
        "expanded_acronyms": applied_acronyms,
        "corrected_typos": applied_typos,
        "predicted_domain": pred_domain,
        "domain_confidence": domain_conf,
        "domain_probabilities": domain_probs,
        "status": "NEEDS_CONFIRMATION" if is_substantive else "READY"
    }
