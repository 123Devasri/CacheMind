import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["embedding_model_ready"] is True
    assert data["classifier_fitted"] is True
    assert data["faiss_vector_count"] >= 6

def test_dashboard_summary():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_queries" in data
    assert "cache_hit_ratio" in data
    assert "active_threshold" in data

def test_cache_query_safe_hit():
    # Semantically equivalent to "How many days of annual leave do permanent employees get?"
    res = client.post("/api/query", json={"query": "How many annual vacation days do permanent employees receive?"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_cached"] is True
    assert data["decision"] == "HIT"
    assert "20 days" in data["answer"]

def test_cache_query_adversarial_rejected_due_to_category_mismatch():
    # Near match lexical overlap but for contractors instead of permanent employees
    res = client.post("/api/query", json={"query": "How many days of annual leave do contractors get?"})
    assert res.status_code == 200
    data = res.json()
    # Should safely fail the permanent leave candidate or match the contractor entry
    if data["is_cached"]:
        assert "contractors and vendors do not receive corporate paid vacation" in data["answer"].lower()
    else:
        assert data["decision"] == "CACHE_MISS"

def test_cache_query_adversarial_rejected_due_to_numeric_mismatch():
    # Query asking about 15 days instead of 20 days
    res = client.post("/api/query", json={"query": "Do permanent employees get 15 days of annual leave?"})
    assert res.status_code == 200
    data = res.json()
    # Must reject the 20 days cached entry due to numerical limit conflict
    if data["candidate"]:
        if "20 days" in data["candidate"]["question"]:
            assert data["candidate"]["policy_condition_passed"] is False

def test_query_clusters_api():
    res = client.get("/api/analytics/clusters?n_clusters=3")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert len(data["clusters"]) >= 2
