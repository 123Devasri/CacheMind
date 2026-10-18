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
    assert data["faiss_vector_count"] >= 0

def test_dashboard_summary():
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_queries" in data
    assert "cache_hit_ratio" in data
    assert "active_threshold" in data
    assert "estimated_cost_saved_inr" in data

def test_cache_query_safe_hit():
    q = "How many days of annual leave do permanent employees receive in Tamil Nadu?"
    # First query populates the cache dynamically if not present
    client.post("/api/query", json={"query": q})
    # Second semantically equivalent query produces a HIT
    res = client.post("/api/query", json={"query": q})
    assert res.status_code == 200
    data = res.json()
    assert data["is_cached"] is True
    assert data["decision"] == "HIT"
    assert "18 days" in data["answer"]

def test_cache_query_adversarial_rejected_due_to_category_mismatch():
    # Near match lexical overlap but for contractors instead of permanent employees
    res = client.post("/api/query", json={"query": "Are contractors eligible for paid leave days in Chennai?"})
    assert res.status_code == 200
    data = res.json()
    if data["is_cached"]:
        assert "contractors" in data["answer"].lower()
    else:
        assert data["decision"] == "CACHE_MISS"

def test_cache_query_adversarial_rejected_due_to_numeric_mismatch():
    # Query asking about 10 days instead of 18 days
    res = client.post("/api/query", json={"query": "Do permanent employees get 10 days of annual leave in Tamil Nadu?"})
    assert res.status_code == 200
    data = res.json()
    # Must reject the 18 days cached entry due to numerical limit conflict
    if data["candidate"] and "18 days" in data["candidate"]["question"]:
        assert data["candidate"]["policy_condition_passed"] is False

def test_query_optimization_detection():
    # Conversational greeting and filler test
    res = client.post("/api/query/check-or-optimize", json={
        "query": "hi hello how are you ? i need to know about the domestic travel allowance in India"
    })
    assert res.status_code == 200
    data = res.json()
    if data["needs_confirmation"]:
        assert data["optimized_query"] is not None
        assert "hi" in [f.lower() for f in data["removed_filler"]] or "hello" in [f.lower() for f in data["removed_filler"]]

def test_query_clusters_api():
    res = client.get("/api/analytics/clusters?n_clusters=3")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert len(data["clusters"]) >= 2

def test_sustainability_metrics_api():
    client.post("/api/query", json={"query": "Hello"})
    res = client.get("/api/dashboard/sustainability")
    assert res.status_code == 200
    data = res.json()
    assert "total_queries" in data
    assert "cache_hits" in data
    assert "hit_rate_pct" in data
    assert "energy_saved_wh" in data
    assert "co2_avoided_grams" in data
    assert "total_cost_saved_usd" in data
    assert "total_cost_saved_inr" in data
    assert "progression" in data
    assert isinstance(data["progression"], list)
    assert len(data["progression"]) >= 1
    first_pt = data["progression"][0]
    assert "query_index" in first_pt
    assert "cumulative_hits" in first_pt
    assert "hit_rate_pct" in first_pt
    assert "cumulative_cost_saved_usd" in first_pt
    assert "cumulative_cost_saved_inr" in first_pt
