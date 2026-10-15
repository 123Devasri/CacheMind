import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.entities import CachedEntry

client = TestClient(app)

def test_cache_miss_then_cache_hit_write_on_miss():
    """
    Verifies that when a question is asked for the first time,
    it executes grounded search (CACHE_MISS), saves the answer to cache and FAISS,
    and the second time the exact or equivalent query is submitted,
    it returns a CACHE HIT with ultra-low latency.
    """
    # Clean up and reset cache to cold start state
    admin_login = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "Admin@123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    reset_res = client.post("/api/admin/cache/reset", headers={"Authorization": f"Bearer {admin_token}"})
    assert reset_res.status_code == 200

    test_query = "How many weeks of paid maternity leave do eligible female employees receive?"

    # 1. First submission -> Expect CACHE_MISS (Grounded in policy TN-HR-LEAVE-01)
    res1 = client.post("/api/query", json={"query": test_query})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["decision"] == "CACHE_MISS"
    assert data1["is_cached"] is False
    assert "26 weeks" in data1["answer"]

    # 2. Second submission with the exact same query -> MUST BE CACHE_HIT!
    res2 = client.post("/api/query", json={"query": test_query})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["decision"] == "HIT"
    assert data2["is_cached"] is True
    assert data2["provider_used"] == "cache"
    assert "26 weeks" in data2["answer"]

    # 3. Third submission with semantic paraphrase -> MUST BE CACHE_HIT!
    paraphrase_query = "What is the duration of paid maternity leave for eligible female employees?"
    res3 = client.post("/api/query", json={"query": paraphrase_query})
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["decision"] == "HIT"
    assert data3["is_cached"] is True
    assert data3["provider_used"] == "cache"
    assert "26 weeks" in data3["answer"]
