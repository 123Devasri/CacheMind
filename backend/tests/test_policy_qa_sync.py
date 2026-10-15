import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.entities import Policy, CachedEntry

client = TestClient(app)

def test_policy_cold_start_miss_dynamic_cache_and_invalidation_lifecycle():
    """
    Verifies the end-to-end governed runtime workflow:
    1. New policy document created -> Production cache remains cold/empty (N=0).
    2. User submits question -> CACHE MISS -> Answered accurately from policy document -> Written dynamically to cache.
    3. User submits same question again -> CACHE HIT (<5ms).
    4. Admin updates policy terms -> Existing cache entries derived from this policy are invalidated.
    5. User submits question -> CACHE MISS -> Answered with updated policy terms -> Dynamically cached.
    6. User submits question again -> CACHE HIT with the new policy terms.
    """
    # 1. Login as Admin
    admin_login = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "Admin@123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Login as User
    user_login = client.post("/api/auth/login", json={
        "username": "user",
        "password": "User@123"
    })
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 3. Create a brand new policy document as Admin
    test_policy_id = "TN-HR-GYM-99"
    
    # Cleanup if exists from prior test runs
    db = SessionLocal()
    try:
        db.query(CachedEntry).filter(CachedEntry.policy_id == test_policy_id).delete()
        db.query(Policy).filter(Policy.policy_id == test_policy_id).delete()
        db.commit()
    finally:
        db.close()

    create_res = client.post("/api/admin/policies", json={
        "policy_id": test_policy_id,
        "name": "Employee Health, Fitness & Gym Membership Subsidy Policy",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "content": (
            "1. Corporate Gym & Fitness Subsidy\n"
            "Kaveri Tech Solutions encourages physical wellness across our Chennai OMR and Coimbatore campuses. "
            "All permanent employees are entitled to a monthly gym and fitness reimbursement of INR 2,500. "
            "Reimbursement can be claimed against verified fitness center, yoga studio, or sports club receipts.\n\n"
            "2. Annual Health Checkup\n"
            "Employees completing 1 year of continuous service receive a complimentary comprehensive annual executive health checkup at partner hospitals in Chennai and Coimbatore."
        )
    }, headers=admin_headers)
    assert create_res.status_code == 200

    # 4. Verify that Cache is NOT pre-seeded (Starts completely empty for this policy)
    db = SessionLocal()
    try:
        cached_items = db.query(CachedEntry).filter(
            CachedEntry.policy_id == test_policy_id,
            CachedEntry.is_active == True
        ).all()
        assert len(cached_items) == 0, "Cache should start empty when policy is created"
    finally:
        db.close()

    # 5. User submits question for the first time -> CACHE_MISS, answered from policy text
    q_res = client.post("/api/user/query", json={
        "query": "What is the monthly gym and fitness reimbursement limit?"
    }, headers=user_headers)
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["decision"] == "CACHE_MISS"
    assert q_data["is_cached"] is False
    assert "2,500" in q_data["answer"] or "2500" in q_data["answer"] or "INR 2,500" in q_data["answer"]
    assert q_data["policy_id"] == test_policy_id

    # 6. Verify dynamic write-on-miss occurred
    db = SessionLocal()
    try:
        cached_items = db.query(CachedEntry).filter(
            CachedEntry.policy_id == test_policy_id,
            CachedEntry.is_active == True
        ).all()
        assert len(cached_items) == 1, "Question and answered policy text should be cached automatically"
    finally:
        db.close()

    # 7. User submits same question again -> CACHE HIT (< 5ms)!
    q_res_hit = client.post("/api/user/query", json={
        "query": "What is the monthly gym and fitness reimbursement limit?"
    }, headers=user_headers)
    assert q_res_hit.status_code == 200
    q_data_hit = q_res_hit.json()
    assert q_data_hit["decision"] == "HIT"
    assert q_data_hit["is_cached"] is True
    assert "2,500" in q_data_hit["answer"] or "2500" in q_data_hit["answer"]

    # 8. Admin updates the policy (subsidy increased from 2,500 to 3,500)
    update_res = client.put(f"/api/admin/policies/{test_policy_id}", json={
        "name": "Employee Health, Fitness & Gym Membership Subsidy Policy",
        "content": (
            "1. Corporate Gym & Fitness Subsidy\n"
            "Kaveri Tech Solutions encourages physical wellness across our Chennai OMR and Coimbatore campuses. "
            "All permanent employees are entitled to a monthly gym and fitness reimbursement of INR 3,500. "
            "Reimbursement can be claimed against verified fitness center, yoga studio, or sports club receipts.\n\n"
            "2. Annual Health Checkup\n"
            "Employees completing 1 year of continuous service receive a complimentary comprehensive annual executive health checkup at partner hospitals in Chennai and Coimbatore."
        )
    }, headers=admin_headers)
    assert update_res.status_code == 200

    # 9. Verify dependent cache entries were invalidated
    db = SessionLocal()
    try:
        cached_items = db.query(CachedEntry).filter(
            CachedEntry.policy_id == test_policy_id,
            CachedEntry.is_active == True
        ).all()
        assert len(cached_items) == 0, "Updating policy must invalidate old cached entries"
    finally:
        db.close()

    # 10. User queries again: produces CACHE_MISS and returns updated 3,500 answer
    q_res_updated = client.post("/api/user/query", json={
        "query": "What is the monthly gym and fitness reimbursement limit?"
    }, headers=user_headers)
    assert q_res_updated.status_code == 200
    q_data_updated = q_res_updated.json()
    assert q_data_updated["decision"] == "CACHE_MISS"
    assert q_data_updated["is_cached"] is False
    assert "3,500" in q_data_updated["answer"] or "3500" in q_data_updated["answer"]
    assert q_data_updated["policy_id"] == test_policy_id

    # 11. Repeat query on updated policy -> CACHE HIT with 3,500!
    q_res_updated_hit = client.post("/api/user/query", json={
        "query": "What is the monthly gym and fitness reimbursement limit?"
    }, headers=user_headers)
    assert q_res_updated_hit.status_code == 200
    q_data_updated_hit = q_res_updated_hit.json()
    assert q_data_updated_hit["decision"] == "HIT"
    assert q_data_updated_hit["is_cached"] is True
    assert "3,500" in q_data_updated_hit["answer"] or "3500" in q_data_updated_hit["answer"]

    # 12. Cleanup test policy
    db = SessionLocal()
    try:
        db.query(CachedEntry).filter(CachedEntry.policy_id == test_policy_id).delete()
        db.query(Policy).filter(Policy.policy_id == test_policy_id).delete()
        db.commit()
    finally:
        db.close()
