import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.entities import CachedEntry, Policy
from app.ml.query_optimizer import optimize_user_query
from app.ml.faiss_index import faiss_service

client = TestClient(app)

def test_syllabus_model_selection_and_inspection():
    # 1. Inspect initial active model
    res = client.get("/api/admin/models/active")
    assert res.status_code == 200
    data = res.json()
    assert "active_model" in data
    assert "available_models" in data
    assert "decision_tree" in data["available_models"]
    assert "logistic_regression" in data["available_models"]
    assert "knn" in data["available_models"]

    # 2. Switch to Decision Tree (ID3 / CART)
    res_dt = client.post("/api/admin/models/select", json={"model_name": "decision_tree"})
    assert res_dt.status_code == 200
    assert res_dt.json()["active_model"] == "decision_tree"

    # 3. Switch to Instance-Based k-NN
    res_knn = client.post("/api/admin/models/select", json={"model_name": "knn"})
    assert res_knn.status_code == 200
    assert res_knn.json()["active_model"] == "knn"

    # 4. Switch to Logistic Regression
    res_lr = client.post("/api/admin/models/select", json={"model_name": "logistic_regression"})
    assert res_lr.status_code == 200
    assert res_lr.json()["active_model"] == "logistic_regression"

    # 5. Invalid model rejection
    res_inv = client.post("/api/admin/models/select", json={"model_name": "transformer_xl_fake"})
    assert res_inv.status_code == 400

    # 6. Switch back to syllabus default: Decision Tree
    client.post("/api/admin/models/select", json={"model_name": "decision_tree"})

def test_prompt_optimization_acronyms_and_naive_bayes_routing():
    # Test WFH acronym expansion + HR domain classification
    opt_wfh = optimize_user_query("What is the WFH policy for Chennai OMR staff?")
    assert "work from home" in opt_wfh["optimized_query"].lower()
    assert opt_wfh["predicted_domain"] == "HR"
    assert opt_wfh["is_pure_greeting"] is False

    # Test PL and CL acronym expansion
    opt_leave = optimize_user_query("Can I take PL or CL next week?")
    assert "privilege leave" in opt_leave["optimized_query"].lower()
    assert opt_leave["predicted_domain"] == "HR"

    # Test IT domain routing
    opt_it = optimize_user_query("How do I configure VPN and install antivirus on my laptop?")
    assert opt_it["predicted_domain"] == "IT"

    # Test greeting optimization
    opt_greet = optimize_user_query("Good morning!")
    assert opt_greet["is_pure_greeting"] is True

def test_cold_start_cache_reset_endpoint():
    # Trigger Cold Start Reset
    res = client.post("/api/admin/cache/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["vector_count"] == 0

    # Verify that FAISS index is indeed at 0 vectors
    assert faiss_service.total_vectors() == 0

    # Restore seed entries so subsequent test suites remain isolated and pass
    from app.services.policy_qa_service import sync_all_policies_to_cache_and_training
    db = SessionLocal()
    try:
        sync_all_policies_to_cache_and_training(db)
    finally:
        db.close()

