import re
from typing import Dict, Any, List

# Pure greetings that shouldn't be searched as corporate policies
PURE_GREETINGS = [
    r"^(hi|hello|hey|heyy|howdy|greetings|vanakkam|namaste)$",
    r"^(hi|hello|hey)\s+(there|assistant|bot|cachemind|team)$",
    r"^(good\s+(morning|afternoon|evening|day))$",
    r"^(how\s+are\s+you|how\s+r\s+u|how\s+do\s+you\s+do|what'?s\s+up)$",
    r"^(hi|hello|hey)[,\s]+(how\s+are\s+you|how\s+r\s+u|hope\s+you\s+are\s+well)[!?.]*$"
]

# Conversational intros, pleasantries, and fillers to strip from inquiries
PREFIX_FILLERS = [
    r"^(hi|hello|hey|greetings|vanakkam|namaste)[,\s]+",
    r"^(good\s+(morning|afternoon|evening|day))[,\s]+",
    r"^(how\s+are\s+you|hope\s+you\s+are\s+doing\s+well|hope\s+all\s+is\s+well)[,?\s]+",
    r"^(can\s+you\s+(please\s+)?tell\s+me|could\s+you\s+(please\s+)?tell\s+me|please\s+tell\s+me|tell\s+me|pls\s+tell\s+me)\s+(about\s+)?",
    r"^(i\s+need\s+to\s+know\s+(about\s+)?|i\s+want\s+to\s+know\s+(about\s+)?|i\s+would\s+like\s+to\s+know\s+(about\s+)?)",
    r"^(i\s+would\s+like\s+to\s+ask|i\s+just\s+wanted\s+to\s+ask|i\s+wanted\s+to\s+ask\s+(about\s+)?)",
    r"^(could\s+someone\s+clarify|can\s+you\s+clarify|could\s+you\s+explain|please\s+explain)\s+(about\s+)?",
    r"^(can\s+you\s+help\s+me\s+(with|understand)|help\s+me\s+understand|i\s+am\s+looking\s+for\s+info(rmation)?\s+on)",
    r"^(just\s+wondering\s+about|quick\s+question\s+(regarding|about)|quick\s+question)\s+",
    r"^(can\s+you\s+let\s+me\s+know|pls\s+let\s+me\s+know|please\s+let\s+me\s+know)\s+(about\s+)?"
]

# Mid-sentence or closing fillers
MISC_FILLERS = [
    r"\b(hi|hello|hey)\b",
    r"\b(how\s+are\s+you|how\s+r\s+u|hope\s+you\s+are\s+well)\b",
    r"\b(can\s+you\s+please\s+tell\s+me|could\s+you\s+please\s+tell\s+me|please\s+tell\s+me)\b",
    r"\b(i\s+need\s+to\s+know\s+about|i\s+need\s+to\s+know|i\s+want\s+to\s+know\s+about|i\s+want\s+to\s+know)\b",
    r"\b(thank\s+you|thanks\s+in\s+advance|thanks\s+a\s+lot|thanks)\b",
    r"\b(asap|urgently|please\s+help)\b"
]

def optimize_user_query(raw_query: str) -> Dict[str, Any]:
    """
    Analyzes an incoming user query:
    1. Detects pure conversational greetings (e.g. 'hi', 'hello', 'good morning')
    2. Strips conversational filler and extracts the clean canonical question
    3. Returns whether the query was optimized or is a pure greeting.
    """
    if not raw_query or not raw_query.strip():
        return {
            "is_pure_greeting": False,
            "is_optimized": False,
            "original_query": raw_query,
            "optimized_query": raw_query,
            "removed_filler": []
        }

    original = raw_query.strip()
    norm = original.lower().strip()
    norm_no_punct = re.sub(r'[?!.,;:]+', '', norm).strip()

    # 1. Check if it is a pure greeting
    for g_pat in PURE_GREETINGS:
        if re.match(g_pat, norm_no_punct, flags=re.IGNORECASE):
            return {
                "is_pure_greeting": True,
                "is_optimized": False,
                "original_query": original,
                "optimized_query": original,
                "removed_filler": [original]
            }

    # 2. Check for conversational query containing actual intent
    working = original
    removed = []

    # Strip prefix fillers iteratively
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

    # Also clean misc fillers if any remain
    for m_pat in MISC_FILLERS:
        found = re.findall(m_pat, working, flags=re.IGNORECASE)
        if found:
            for item in found:
                item_str = item if isinstance(item, str) else item[0]
                if item_str and item_str not in removed:
                    removed.append(item_str)
            working = re.sub(m_pat, " ", working, flags=re.IGNORECASE)

    # Clean redundant punctuation and excessive spaces
    working = re.sub(r'^[?!.,;:\s]+', '', working)
    working = re.sub(r'\s+', ' ', working).strip()

    # If nothing was left or it was too short, fallback to original
    if len(working) < 4:
        return {
            "is_pure_greeting": False,
            "is_optimized": False,
            "original_query": original,
            "optimized_query": original,
            "removed_filler": []
        }

    # Reformulate cleanly into a professional question if needed
    cleaned_lower = working.lower()
    question_starters = ["what", "how", "when", "where", "why", "who", "which", "is", "are", "do", "does", "can", "may", "will", "must"]
    words = working.split()
    first_word = words[0].lower() if words else ""

    if first_word not in question_starters:
        # e.g. "this and this info" or "the leave policy for permanent staff in Tamil Nadu"
        # Convert to: "What is the policy regarding this and this info?"
        core_topic = re.sub(r'^(the|our|about|regarding)\s+', '', working, flags=re.IGNORECASE).strip()
        if any(term in cleaned_lower for term in ["leave", "wfh", "remote", "travel", "per diem", "allowance", "vpn", "insurance", "reimbursement", "relocation", "policy", "rule"]):
            optimized_candidate = f"What is the policy regarding {core_topic.rstrip('?.')}?"
        else:
            optimized_candidate = f"What is the policy regarding {core_topic.rstrip('?.')}?"
    else:
        # Already starts with question starter (e.g. "How many days...", "Is VPN mandatory...")
        optimized_candidate = f"{working[0].upper()}{working[1:].rstrip('?.')}?"

    # Compare whether a meaningful transformation happened
    orig_tokens = set(re.findall(r'\b\w+\b', original.lower()))
    opt_tokens = set(re.findall(r'\b\w+\b', optimized_candidate.lower()))
    
    # Check if filler phrases were removed
    has_meaningful_change = len(removed) > 0 and len(orig_tokens - opt_tokens) > 0

    return {
        "is_pure_greeting": False,
        "is_optimized": has_meaningful_change,
        "original_query": original,
        "optimized_query": optimized_candidate if has_meaningful_change else original,
        "removed_filler": removed
    }
