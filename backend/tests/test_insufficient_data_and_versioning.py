import pytest
import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.entities import Policy, PolicyVersion, CachedEntry, QueryAuditLog, InsufficientDataQuestion, User
from app.core.security import create_access_token
from app.ml.cache_pipeline import cache_pipeline
from app.services.rag_service import rag_service

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_headers(client):
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        token = create_access_token({"sub": admin.id, "username": admin.username, "role": "ADMIN"})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

@pytest.fixture
def user_headers(client):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "user").first()
        token = create_access_token({"sub": user.id, "username": user.username, "role": "USER"})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

@pytest.fixture(autouse=True)
def clean_gaps():
    db = SessionLocal()
    try:
        db.query(InsufficientDataQuestion).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(InsufficientDataQuestion).delete()
        db.commit()
    finally:
        db.close()


def test_unanswered_question_recorded_in_insufficient_data(client, user_headers):
    """
    Genuine policy question without evidence in uploaded documents must:
    1. Return INSUFFICIENT_EVIDENCE
    2. Be recorded in the InsufficientDataQuestion table with PENDING status
    """
    db = SessionLocal()
    try:
        missing_query = "What is the company stock option vesting policy for directors in Germany?"
        res = client.post(
            "/api/user/query",
            json={"query": missing_query},
            headers=user_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "INSUFFICIENT_EVIDENCE"
        assert not data["is_cached"]

        gap = db.query(InsufficientDataQuestion).filter(
            InsufficientDataQuestion.query_text == missing_query
        ).first()
        assert gap is not None
        assert gap.status == "PENDING"
        assert gap.retrieval_status == "INSUFFICIENT_EVIDENCE"
        assert gap.occurrence_count == 1
    finally:
        db.close()


def test_repeated_unanswered_question_increments_occurrence_count(client, user_headers):
    """
    Asking the same unanswered question multiple times should:
    1. Increment occurrence_count instead of creating duplicate records
    2. Update last_asked_at
    """
    db = SessionLocal()
    try:
        repeated_query = "Can employees adopt pets in the corporate housing in London?"
        res1 = client.post("/api/user/query", json={"query": repeated_query}, headers=user_headers)
        assert res1.status_code == 200

        gap1 = db.query(InsufficientDataQuestion).filter(
            InsufficientDataQuestion.query_text == repeated_query
        ).first()
        assert gap1 is not None
        initial_count = gap1.occurrence_count

        res2 = client.post("/api/user/query", json={"query": repeated_query}, headers=user_headers)
        assert res2.status_code == 200

        db.refresh(gap1)
        assert gap1.occurrence_count == initial_count + 1

        # Must not have duplicated rows
        total_gaps = db.query(InsufficientDataQuestion).filter(
            InsufficientDataQuestion.query_text == repeated_query
        ).count()
        assert total_gaps == 1
    finally:
        db.close()


def test_greeting_and_empty_not_recorded_in_insufficient_data(client, user_headers):
    """
    Greetings and empty queries must NEVER be recorded as policy evidence gaps.
    """
    db = SessionLocal()
    try:
        before_count = db.query(InsufficientDataQuestion).count()

        # Send greeting
        res_greet = client.post("/api/user/query", json={"query": "Hello, good morning!"}, headers=user_headers)
        assert res_greet.status_code == 200
        assert res_greet.json()["decision"] == "GREETING"

        after_count = db.query(InsufficientDataQuestion).count()
        assert after_count == before_count
    finally:
        db.close()


def test_admin_insufficient_data_api_and_notes(client, admin_headers):
    """
    Admin should be able to:
    1. List insufficient data questions with status counts
    2. Filter by status (PENDING, REVIEWED, RESOLVED)
    3. Update status and add notes via PATCH
    """
    db = SessionLocal()
    try:
        # Create a test gap
        gap = InsufficientDataQuestion(
            query_text="What is the bereavement leave duration for grandparents?",
            normalized_query="what is the bereavement leave duration for grandparents?",
            policy_scope="HR",
            retrieval_status="INSUFFICIENT_EVIDENCE",
            reason="No bereavement leave section found.",
            status="PENDING",
            occurrence_count=1
        )
        db.add(gap)
        db.commit()
        db.refresh(gap)

        # GET /api/admin/insufficient-data-questions
        res = client.get("/api/admin/insufficient-data-questions?status=PENDING", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert data["pending_count"] >= 1
        found = any(item["id"] == gap.id for item in data["items"])
        assert found

        # PATCH /api/admin/insufficient-data-questions/{id}
        patch_res = client.patch(
            f"/api/admin/insufficient-data-questions/{gap.id}",
            json={"status": "REVIEWED", "admin_notes": "Sent to HR policy committee."},
            headers=admin_headers
        )
        assert patch_res.status_code == 200
        patched_data = patch_res.json()
        assert patched_data["status"] == "REVIEWED"
        assert patched_data["admin_notes"] == "Sent to HR policy committee."

        db.refresh(gap)
        assert gap.status == "REVIEWED"
        assert gap.admin_notes == "Sent to HR policy committee."
    finally:
        db.close()


def test_policy_upload_auto_resolves_pending_questions(client, admin_headers):
    """
    When an updated or new policy document is uploaded providing evidence
    for a previously unanswered question, re-evaluation marks the question as RESOLVED.
    """
    db = SessionLocal()
    try:
        gap = InsufficientDataQuestion(
            query_text="How many days of paternity leave are provided?",
            normalized_query="how many days of paternity leave are provided?",
            policy_scope="HR",
            retrieval_status="INSUFFICIENT_EVIDENCE",
            reason="Paternity leave not documented.",
            status="PENDING",
            occurrence_count=1
        )
        db.add(gap)
        db.commit()
        db.refresh(gap)

        # Upload a policy covering paternity leave
        pol_content = (
            "# Section 1: Paternity Leave\n"
            "Eligible male employees are entitled to 10 working days of fully paid Paternity Leave "
            "to be availed within 6 months of the child's birth."
        )
        pol_id = "TN-HR-PATERNITY-99"
        create_res = client.post(
            "/api/admin/policies",
            json={
                "policy_id": pol_id,
                "name": "Paternity Leave Policy",
                "domain": "HR",
                "jurisdiction": "INDIA",
                "employee_category": "ALL",
                "content": pol_content,
                "status": "active"
            },
            headers=admin_headers
        )
        assert create_res.status_code == 200

        # Trigger re-evaluation
        reval_res = client.post("/api/admin/insufficient-data-questions/re-evaluate", headers=admin_headers)
        assert reval_res.status_code == 200

        db.refresh(gap)
        assert gap.status == "RESOLVED"
        assert gap.resolved_by_policy_id == pol_id
        assert gap.resolved_at is not None
    finally:
        db.close()


def test_granular_policy_invalidation_preserves_untouched_sections(client, admin_headers):
    """
    Granular invalidation:
    When updating Clause 1 of a policy:
    - CachedEntry dependent on Clause 1 MUST be invalidated
    - CachedEntry dependent on Clause 2 MUST remain active
    """
    db = SessionLocal()
    try:
        pol_id = "TN-TEST-GRANULAR-01"
        initial_content = (
            "# Section 1: Business Travel\n"
            "Employees receive a domestic daily travel allowance of INR 2000 per day.\n\n"
            "# Section 2: Mobile Reimbursement\n"
            "Employees are eligible for monthly mobile reimbursement up to INR 1500."
        )

        create_res = client.post(
            "/api/admin/policies",
            json={
                "policy_id": pol_id,
                "name": "Granular Travel & Mobile Policy",
                "domain": "HR",
                "jurisdiction": "INDIA",
                "employee_category": "ALL",
                "content": initial_content,
                "status": "active"
            },
            headers=admin_headers
        )
        assert create_res.status_code == 200

        # Create two cache entries simulating granular dependency
        entry_sec1 = CachedEntry(
            question="What is the domestic daily travel allowance?",
            normalized_question="what is the domestic daily travel allowance?",
            answer="The allowance is INR 2000 per day.",
            policy_id=pol_id,
            policy_version="1.0",
            domain="HR",
            source_section_ids=[f"{pol_id}-sec-01"],
            source_content_hashes={f"{pol_id}-sec-01": "initial_hash_1"},
            is_active=True,
            is_verified=True
        )
        entry_sec2 = CachedEntry(
            question="What is the monthly mobile reimbursement amount?",
            normalized_question="what is the monthly mobile reimbursement amount?",
            answer="Up to INR 1500 per month.",
            policy_id=pol_id,
            policy_version="1.0",
            domain="HR",
            source_section_ids=[f"{pol_id}-sec-02"],
            source_content_hashes={f"{pol_id}-sec-02": "initial_hash_2"},
            is_active=True,
            is_verified=True
        )
        db.add_all([entry_sec1, entry_sec2])
        db.commit()
        db.refresh(entry_sec1)
        db.refresh(entry_sec2)

        # Now update ONLY Section 1 (travel allowance changed to 3500)
        updated_content = (
            "# Section 1: Business Travel\n"
            "Employees receive a domestic daily travel allowance of INR 3500 per day.\n\n"
            "# Section 2: Mobile Reimbursement\n"
            "Employees are eligible for monthly mobile reimbursement up to INR 1500."
        )
        # To make sure sec-02 content hash matches, let's grab sec-02's real hash
        from app.services.rag_service import parse_policy_sections
        secs = parse_policy_sections(updated_content, pol_id)
        sec2_hash = next(s["content_hash"] for s in secs if s["heading"] == "Section 2: Mobile Reimbursement")
        # update entry_sec2's stored hash to match the initial & new Section 2
        entry_sec2.source_content_hashes = {f"{pol_id}-sec-02": sec2_hash}
        db.commit()

        update_res = client.put(
            f"/api/admin/policies/{pol_id}",
            json={"content": updated_content},
            headers=admin_headers
        )
        assert update_res.status_code == 200

        db.refresh(entry_sec1)
        db.refresh(entry_sec2)

        # Section 1 entry must be invalidated
        assert not entry_sec1.is_active
        assert entry_sec1.invalidation_reason is not None

        # Section 2 entry MUST remain active
        assert entry_sec2.is_active
    finally:
        db.close()


def test_policy_rename_preserves_active_cache_entries(client, admin_headers):
    """
    Renaming a policy's display name without changing content MUST NOT invalidate any cache entries.
    """
    db = SessionLocal()
    try:
        pol_id = "TN-TEST-RENAME-01"
        content = "# Section 1: Core Hours\nCore working hours are 10 AM to 5 PM IST."
        create_res = client.post(
            "/api/admin/policies",
            json={
                "policy_id": pol_id,
                "name": "Original Policy Title",
                "domain": "HR",
                "content": content,
                "status": "active"
            },
            headers=admin_headers
        )
        assert create_res.status_code == 200

        entry = CachedEntry(
            question="What are core working hours?",
            normalized_question="what are core working hours?",
            answer="10 AM to 5 PM IST.",
            policy_id=pol_id,
            policy_version="1.0",
            domain="HR",
            source_section_ids=[f"{pol_id}-sec-01"],
            source_content_hashes={},
            is_active=True,
            is_verified=True
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        # Update display name ONLY
        rename_res = client.put(
            f"/api/admin/policies/{pol_id}",
            json={"name": "Updated Renamed Policy Title"},
            headers=admin_headers
        )
        assert rename_res.status_code == 200

        db.refresh(entry)
        assert entry.is_active
        assert "Updated Renamed Policy Title" in (entry.source_citation or "")
    finally:
        db.close()


def test_historical_analytics_preserved_when_cache_entries_deleted(client, admin_headers):
    """
    Historical Policy Cache Hit Rate and Historical Hits come strictly from QueryAuditLog.
    Deleting or invalidating CachedEntry records must NEVER reduce historical hits or hit rate.
    """
    db = SessionLocal()
    try:
        # Create 2 query audit logs representing policy inquiries (1 HIT, 1 MISS)
        log1 = QueryAuditLog(
            query_text="What are leave days?",
            query_category="POLICY",
            decision="HIT",
            returned_answer="18 days PL.",
            is_cached_result=True,
            lookup_latency_ms=1.2,
            total_latency_ms=1.2
        )
        log2 = QueryAuditLog(
            query_text="What is the sabbatical policy?",
            query_category="POLICY",
            decision="CACHE_MISS",
            returned_answer="No sabbatical policy found.",
            is_cached_result=False,
            lookup_latency_ms=2.0,
            total_latency_ms=500.0
        )
        # And 1 cache entry
        entry = CachedEntry(
            question="What are leave days?",
            normalized_question="what are leave days?",
            answer="18 days PL.",
            policy_id="TN-HR-LEAVE-01",
            policy_version="1.0",
            domain="HR",
            is_active=True,
            is_verified=True
        )
        db.add_all([log1, log2, entry])
        db.commit()

        # Check summary before deleting cache entry
        res1 = client.get("/api/dashboard/summary")
        assert res1.status_code == 200
        sum1 = res1.json()
        initial_hist_hits = sum1["total_historical_cache_hits"]
        initial_hit_rate = sum1["historical_cache_hit_rate"]

        # Now delete or invalidate all cached entries
        db.query(CachedEntry).delete()
        db.commit()

        # Check summary after deleting cache entry
        res2 = client.get("/api/dashboard/summary")
        assert res2.status_code == 200
        sum2 = res2.json()

        # Historical hits and rate MUST be preserved from QueryAuditLog!
        assert sum2["total_historical_cache_hits"] == initial_hist_hits
        assert sum2["historical_cache_hit_rate"] == initial_hit_rate
        # Only active cache entries count changes
        assert sum2["current_active_cache_entries"] == 0
    finally:
        db.close()
