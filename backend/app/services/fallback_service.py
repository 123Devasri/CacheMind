from typing import Optional, Dict, Any
from app.core.config import settings

class LLMFallbackService:
    def __init__(self):
        pass

    def generate_response(self, query: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes fallback inference when cache miss occurs.
        Uses OpenAI if API key provided and configured; otherwise deterministic local mock.
        Clearly tags mock responses to ensure zero deception.
        """
        provider = settings.FALLBACK_PROVIDER
        
        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                # Real provider call if configured
                import urllib.request
                import json
                
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
                }
                payload = {
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are an enterprise assistant. Answer based on corporate policies."},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.2
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    answer = data["choices"][0]["message"]["content"]
                    return {
                        "provider": "openai",
                        "model": settings.OPENAI_MODEL,
                        "is_mock": False,
                        "answer": answer
                    }
            except Exception as e:
                print(f"OpenAI call failed, falling back to local mock: {e}")

        # Deterministic Local Mock Provider
        q_lower = query.lower()
        if "leave" in q_lower or "pto" in q_lower or "vacation" in q_lower:
            ans = "[Local Mock Assistant] Based on company HR policy: Full-time permanent employees are eligible for 20 paid leave days annually, while contractors do not accrue corporate PTO unless specifically stipulated in their vendor contract."
        elif "wfh" in q_lower or "remote" in q_lower or "work from home" in q_lower:
            ans = "[Local Mock Assistant] Based on company IT & Workplace policy: Full-time employees can work remotely up to 2 days per week upon manager approval. Equipment stipends apply only to full-time staff."
        elif "travel" in q_lower or "flight" in q_lower or "per diem" in q_lower or "expense" in q_lower:
            ans = "[Local Mock Assistant] Based on Global Finance policy: Travel meal allowances are set at $75/day in the US and INR 3,000/day in India. Receipts are strictly mandatory for all expense reimbursements exceeding $25."
        elif "vpn" in q_lower or "laptop" in q_lower or "software" in q_lower:
            ans = "[Local Mock Assistant] Based on Enterprise IT policy: Enterprise VPN and Okta SSO are required for all remote access. IT support operates 24/7 via the helpdesk portal."
        else:
            ans = f"[Local Mock Assistant] No verified cache record matched your query. This is a newly synthesized fallback response for query: '{query}'."

        return {
            "provider": "local_mock",
            "model": "deterministic-mock-v1",
            "is_mock": True,
            "answer": ans
        }

llm_service = LLMFallbackService()
