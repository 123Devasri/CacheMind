import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_user_registration_and_login():
    # Register a new unique user
    username = "test_employee_42"
    email = "test_employee_42@cachemind.internal"
    reg_res = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": "Password123!",
        "full_name": "Test Employee",
        "department": "Engineering"
    })
    # If already exists from prior run, status may be 400 or 200
    if reg_res.status_code == 200:
        data = reg_res.json()
        assert "access_token" in data
        assert data["user"]["role"] == "USER"
    
    # Login with the credentials
    login_res = client.post("/api/auth/login", json={
        "username": username,
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["role"] == "USER"

def test_admin_login():
    # Default seeded admin
    res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "Admin@123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "ADMIN"
    assert "access_token" in data

def test_rbac_user_cannot_access_admin_endpoints():
    # Login as user
    user_res = client.post("/api/auth/login", json={
        "username": "user",
        "password": "User@123"
    })
    assert user_res.status_code == 200
    user_token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    # Attempt to list users -> 403 Forbidden
    res = client.get("/api/admin/users", headers=headers)
    assert res.status_code == 403

    # Attempt to trigger model training -> 403 Forbidden
    res = client.post("/api/admin/models/train", headers=headers)
    assert res.status_code == 403

def test_rbac_admin_can_access_admin_endpoints():
    admin_res = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "Admin@123"
    })
    assert admin_res.status_code == 200
    admin_token = admin_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin listing all users
    res = client.get("/api/admin/users", headers=headers)
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 2

    # Admin inspecting model registry
    res = client.get("/api/admin/models/registry", headers=headers)
    assert res.status_code == 200

def test_user_query_and_history_isolation():
    user_res = client.post("/api/auth/login", json={
        "username": "user",
        "password": "User@123"
    })
    user_token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    # Submit query as user (first time seeds dynamic cache on cold start, second hits cache)
    client.post("/api/user/query", json={
        "query": "How many days of annual leave do permanent employees get in Tamil Nadu?"
    }, headers=headers)
    query_res = client.post("/api/user/query", json={
        "query": "How many days of annual leave do permanent employees get in Tamil Nadu?"
    }, headers=headers)
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert q_data["is_cached"] is True
    assert "18 days" in q_data["answer"]
    assert "policy_version" in q_data

    # Check personal history
    hist_res = client.get("/api/user/history", headers=headers)
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert len(hist) >= 1
    assert any("annual leave" in h["query_text"].lower() for h in hist)

    # Check personal analytics
    analytics_res = client.get("/api/user/analytics", headers=headers)
    assert analytics_res.status_code == 200
    a_data = analytics_res.json()
    assert a_data["total_queries"] >= 1

def test_user_feedback_and_favorites():
    user_res = client.post("/api/auth/login", json={
        "username": "user",
        "password": "User@123"
    })
    user_token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    # Submit feedback
    fb_res = client.post("/api/user/feedback", json={
        "query_text": "What is the hybrid work policy?",
        "answer_text": "Up to 2 days per week WFH.",
        "rating": "helpful",
        "comment": "Very clear and direct."
    }, headers=headers)
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["rating"] == "helpful"

    # Add favorite
    fav_res = client.post("/api/user/favorites", json={
        "query_text": "What is the hybrid work policy?",
        "answer": "Up to 2 days per week WFH.",
        "policy_id": "TN-HR-WFH-02",
        "policy_version": "1.0",
        "is_cached": True
    }, headers=headers)
    assert fav_res.status_code == 200
    fav_id = fav_res.json()["id"]

    # List favorites
    favs_list = client.get("/api/user/favorites", headers=headers)
    assert favs_list.status_code == 200
    assert len(favs_list.json()) >= 1

    # Remove favorite
    del_fav = client.delete(f"/api/user/favorites/{fav_id}", headers=headers)
    assert del_fav.status_code == 200
