import pytest
import numpy as np
from app.db.session import SessionLocal
from app.models.entities import Policy, PolicyVersion, CachedEntry, QueryAuditLog, User
from app.core.security import hash_password
from app.ml.faiss_index import faiss_service
from app.services.rag_service import rag_service

TEST_POLICIES = [
    {
        "policy_id": "TN-HR-LEAVE-01",
        "name": "Tamil Nadu Shops & Commercial Establishments Act Leave & Holiday Policy",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "ALL",
        "current_version": "1.0",
        "status": "active",
        "content": (
            "Under the Tamil Nadu Shops and Establishments Act, full-time permanent employees of Kaveri Tech Solutions "
            "receive 18 days of Privilege/Annual Leave (PL), 12 days of Casual Leave (CL), and 12 days of Sick Leave (SL) per calendar year. "
            "Medical certificates from a registered practitioner are mandatory for sick leave exceeding 2 consecutive days. "
            "The company observes 10 mandatory Tamil Nadu state and national holidays annually, including Pongal (Thai Pongal, Thiruvalluvar Day, Uzhavar Thirunal), "
            "Tamil New Year, May Day, Independence Day, Gandhi Jayanthi, Ayudha Pooja, and Deepavali. "
            "Eligible female employees receive 26 weeks of fully paid Maternity Leave. "
            "Independent contractors and third-party vendor personnel are governed by their respective vendor contracts and do not accrue corporate paid leave."
        )
    },
    {
        "policy_id": "TN-HR-HEALTH-05",
        "name": "Group Mediclaim Insurance & Employee Wellness Policy",
        "domain": "HR",
        "jurisdiction": "INDIA",
        "employee_category": "FULL_TIME",
        "current_version": "1.0",
        "status": "active",
        "content": (
            "Full-time permanent staff are covered under a Group Health Insurance (GMC) floater policy with a sum insured of INR 5,00,000 "
            "covering the employee, spouse, and up to 2 dependent children. Cashless hospitalization is supported across major network hospitals "
            "in Tamil Nadu including Apollo Hospitals Chennai, MIOT International, Kauvery Hospital Chennai, KG Hospital Coimbatore, and Ganga Hospital. "
            "Employees are also entitled to an annual comprehensive health checkup at partnered diagnostic clinics in Chennai and Coimbatore at zero out-of-pocket cost."
        )
    }
]

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Session fixture that ensures standard test policies and test users exist during tests,
    and cleanly resets test artifacts after the session completes.
    """
    db = SessionLocal()
    try:
        # Ensure default test users exist
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@cachemind.internal",
                hashed_password=hash_password("Admin@123"),
                role="ADMIN",
                full_name="Enterprise Administrator",
                department="IT Governance",
                is_active=True
            )
            db.add(admin)

        user = db.query(User).filter(User.username == "user").first()
        if not user:
            user = User(
                username="user",
                email="user@cachemind.internal",
                hashed_password=hash_password("User@123"),
                role="USER",
                full_name="Enterprise Employee",
                department="Engineering",
                is_active=True
            )
            db.add(user)

        # Seed test policies needed by tests
        for p_data in TEST_POLICIES:
            existing = db.query(Policy).filter(Policy.policy_id == p_data["policy_id"]).first()
            if not existing:
                pol = Policy(**p_data)
                db.add(pol)
                ver = PolicyVersion(
                    policy_id=pol.policy_id,
                    version=pol.current_version,
                    change_summary="Test policy setup",
                    content=pol.content,
                    is_active=True
                )
                db.add(ver)

        db.commit()
        rag_service.invalidate_chunk_cache()
    finally:
        db.close()

    yield

    # Clean up test database after all tests complete so production database starts empty
    db = SessionLocal()
    try:
        db.query(CachedEntry).delete()
        db.query(PolicyVersion).delete()
        db.query(Policy).delete()
        db.query(QueryAuditLog).delete()
        # Remove any extra test users created during test runs (preserve admin and user)
        db.query(User).filter(~User.username.in_(["admin", "user"])).delete(synchronize_session=False)
        db.commit()

        # Reset FAISS index to 0 vectors
        empty_emb = np.zeros((0, 384), dtype=np.float32)
        faiss_service.rebuild_index([], empty_emb)
        rag_service.invalidate_chunk_cache()
    finally:
        db.close()
