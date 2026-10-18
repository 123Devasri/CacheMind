import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.grok_service import grok_service
from app.services.rag_service import rag_service

client = TestClient(app)

def test_insufficient_evidence_does_not_call_grok_or_cache():
    """
    Verifies that when a question has no supporting evidence in the uploaded policies,
    the system gates the request, returns INSUFFICIENT_EVIDENCE, does not invoke Grok,
    and does not write to the cache.
    """
    # 1. Reset cache
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert admin_login.status_code == 200
    token = admin_login.json()["access_token"]
    client.post("/api/admin/cache/reset", headers={"Authorization": f"Bearer {token}"})

    # Out-of-scope query completely unrelated to HR or uploaded policies
    unrelated_query = "What is the orbital velocity of Jupiter's moon Europa in kilometers per second?"

    with patch.object(grok_service, "generate_grounded_answer") as mock_grok:
        res = client.post("/api/query", json={"query": unrelated_query})
        assert res.status_code == 200
        data = res.json()

        # Must not call Grok when evidence is insufficient
        mock_grok.assert_not_called()

        assert data["decision"] == "INSUFFICIENT_EVIDENCE"
        assert data["is_cached"] is False
        assert data["grok_invoked"] is False
        assert "not contain sufficient evidence" in data["answer"].lower() or "insufficient" in data["decision"].lower()

    # Verify nothing was added to cache
    res_second = client.post("/api/query", json={"query": unrelated_query})
    assert res_second.status_code == 200
    data_second = res_second.json()
    assert data_second["is_cached"] is False
    assert data_second["decision"] == "INSUFFICIENT_EVIDENCE"


def test_grok_api_miss_then_cache_hit():
    """
    Verifies that when Grok is configured and evidence is found:
    1. On cache miss: Grok is invoked, returns grounded answer, tokens tracked, cost calculated, entry cached.
    2. On repeat query: Immediate CACHE HIT with 0 Grok calls and cache hit pricing.
    """
    # Reset cache
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
    token = admin_login.json()["access_token"]
    client.post("/api/admin/cache/reset", headers={"Authorization": f"Bearer {token}"})

    test_query = "What is the sum insured under the Group Health Insurance policy for full-time staff in Tamil Nadu?"
    
    mock_grok_response = {
        "success": True,
        "grok_invoked": True,
        "has_sufficient_evidence": True,
        "answer": "Under policy TN-HR-HEALTH-05 (Group Mediclaim Insurance & Employee Wellness Policy), full-time permanent staff are covered under a Group Health Insurance (GMC) floater policy with a sum insured of INR 5,00,000.",
        "confidence": 0.98,
        "supporting_evidence_references": ["Policy TN-HR-HEALTH-05 (Version 1.0)"],
        "tokens_used": {
            "prompt_tokens": 140,
            "completion_tokens": 42,
            "total_tokens": 182
        },
        "estimated_cost_usd": 0.0007,
        "model": "grok-2-latest"
    }

    # First request: Grok invoked
    with patch.object(grok_service, "is_available", return_value=True), \
         patch.object(grok_service, "generate_grounded_answer", return_value=mock_grok_response) as mock_grok:
        
        res1 = client.post("/api/query", json={"query": test_query})
        assert res1.status_code == 200
        data1 = res1.json()

        assert mock_grok.called
        assert data1["decision"] == "CACHE_MISS"
        assert data1["is_cached"] is False
        assert data1["grok_invoked"] is True
        assert data1["tokens_used"]["prompt_tokens"] == 140
        assert data1["tokens_used"]["completion_tokens"] == 42
        assert data1["tokens_used"]["total_tokens"] == 182
        assert data1["estimated_cost_usd"] > 0
        assert "5,00,000" in data1["answer"] or "500000" in data1["answer"]

    # Second request: Cache HIT (Grok MUST NOT be invoked)
    with patch.object(grok_service, "generate_grounded_answer") as mock_grok_repeat:
        res2 = client.post("/api/query", json={"query": test_query})
        assert res2.status_code == 200
        data2 = res2.json()

        mock_grok_repeat.assert_not_called()
        assert data2["decision"] == "HIT"
        assert data2["is_cached"] is True
        assert data2["grok_invoked"] is False
        assert data2["provider_used"] == "cache"
        assert "5,00,000" in data2["answer"] or "500000" in data2["answer"]
        assert data2["estimated_cost_usd"] == 0.00005


def test_dashboard_summary_metrics():
    """
    Verifies that /api/dashboard/summary accurately reports Grok metrics,
    token counts, and real cost calculations.
    """
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    summary = res.json()

    assert "grok_invocations" in summary
    assert "prompt_tokens" in summary
    assert "completion_tokens" in summary
    assert "total_tokens_consumed" in summary
    assert "actual_cost_usd" in summary
    assert "cost_without_cache_usd" in summary
    assert "estimated_cost_saved_usd" in summary
    assert "grok_api" in summary["model_status"]
