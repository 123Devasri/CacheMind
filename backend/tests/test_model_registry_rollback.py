import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_admin_headers():
    res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "Admin@123"
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_model_registry_and_rollback():
    headers = get_admin_headers()

    # 1. Inspect registry
    reg_res = client.get("/api/admin/models/registry", headers=headers)
    assert reg_res.status_code == 200
    versions = reg_res.json()
    assert len(versions) >= 1
    initial_version = versions[0]["version_tag"]
    assert versions[0]["is_active"] is True

    # 2. Rollback to the initial version
    rollback_res = client.post("/api/admin/models/rollback", json={
        "target_version_tag": initial_version
    }, headers=headers)
    assert rollback_res.status_code == 200
    r_data = rollback_res.json()
    assert r_data["status"] == "success"
    assert r_data["active_version"] == initial_version
    assert r_data["classifier_fitted"] is True

def test_policy_document_preview_and_versioning():
    headers = get_admin_headers()

    # 1. Preview raw policy text before publishing
    sample_policy = (
        "Under the Annual Expense Reimbursement Policy, employees traveling across Tamil Nadu "
        "can claim up to INR 2,000 per day for inter-city travel meals. "
        "All receipts must be submitted within 15 calendar days of trip completion."
    )
    preview_res = client.post("/api/admin/policies/preview", data={
        "raw_text": sample_policy,
        "domain": "FINANCE",
        "jurisdiction": "INDIA",
        "employee_category": "ALL"
    }, headers=headers)
    assert preview_res.status_code == 200
    p_data = preview_res.json()
    assert p_data["detected_domain"] == "FINANCE"
    assert len(p_data["clauses"]) >= 1

    # 2. Invalidate cache for obsolete policies
    inv_res = client.post("/api/admin/policies/invalidate-cache", headers=headers)
    assert inv_res.status_code == 200
    assert "invalidated_entries_count" in inv_res.json()

def test_synthetic_data_generation():
    headers = get_admin_headers()

    # Generate synthetic candidate pairs for admin review
    syn_res = client.post("/api/admin/datasets/generate-synthetic", json={
        "policy_id": "TN-HR-LEAVE-01",
        "num_pairs_per_clause": 2
    }, headers=headers)
    assert syn_res.status_code == 200
    candidates = syn_res.json()
    assert len(candidates) >= 1
    # Check that hard negatives exist
    types = [c["pair_type"] for c in candidates]
    assert "positive" in types or "negative_numeric" in types
