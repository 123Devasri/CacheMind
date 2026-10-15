import os
import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
from app.db.session import SessionLocal, engine, Base
from app.models.entities import (
    Policy, PolicyVersion, CachedEntry, QueryAuditLog, Conversation,
    UserFeedback, UserFavorite, User
)
from app.core.security import hash_password
from app.ml.faiss_index import faiss_service
from app.services.rag_service import rag_service

def reset_to_clean_slate():
    """
    Completely wipes:
    - All Policies & Policy Versions (0 policies)
    - All Runtime Cache Entries (0 entries)
    - All Query Audit Logs (0 logs)
    - All Conversations, Favorites, and Feedback
    - Resets FAISS index to 0 vectors
    - Preserves default system accounts: admin (Admin@123) and user (User@123)
    """
    print("=" * 60)
    print("CacheMind: Initializing Clean Slate Database Reset")
    print("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Clear Cached Entries
        c_count = db.query(CachedEntry).delete()
        print(f"Cleared {c_count} cached entries from SQLite.")

        # 2. Clear Policies and Policy Versions
        pv_count = db.query(PolicyVersion).delete()
        p_count = db.query(Policy).delete()
        print(f"Cleared {p_count} policies and {pv_count} policy versions.")

        # 3. Clear Query Audit Logs, Conversations, Feedback, Favorites
        log_count = db.query(QueryAuditLog).delete()
        conv_count = db.query(Conversation).delete()
        fb_count = db.query(UserFeedback).delete()
        fav_count = db.query(UserFavorite).delete()
        print(f"Cleared {log_count} audit logs, {conv_count} conversations, {fb_count} feedbacks, {fav_count} favorites.")

        # 4. Remove any transient user accounts, preserving admin and user
        db.query(User).filter(~User.username.in_(["admin", "user"])).delete(synchronize_session=False)

        # 5. Ensure default admin exists
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
            print("Created default admin user: admin / Admin@123")
        else:
            admin.hashed_password = hash_password("Admin@123")
            admin.is_active = True
            admin.role = "ADMIN"

        # 6. Ensure default standard user exists
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
            print("Created default standard user: user / User@123")
        else:
            user.hashed_password = hash_password("User@123")
            user.is_active = True
            user.role = "USER"

        db.commit()

        # 7. Reset FAISS index to exactly 0 vectors and persist to disk
        empty_emb = np.zeros((0, 384), dtype=np.float32)
        faiss_service.rebuild_index([], empty_emb)
        rag_service.invalidate_chunk_cache()
        print(f"FAISS index rebuilt with {faiss_service.total_vectors()} vectors.")

        # 8. Verify clean slate state
        pol_cnt = db.query(Policy).count()
        cache_cnt = db.query(CachedEntry).count()
        audit_cnt = db.query(QueryAuditLog).count()
        faiss_cnt = faiss_service.total_vectors()
        users = [u.username for u in db.query(User).all()]

        print("\n--- Final Verification ---")
        print(f"Total Policies in DB: {pol_cnt}")
        print(f"Total Cached Entries in DB: {cache_cnt}")
        print(f"Total FAISS Index Vectors: {faiss_cnt}")
        print(f"Total Query Audit Logs: {audit_cnt}")
        print(f"Active Users: {users}")
        print("Clean slate reset completed successfully! CacheMind is ready for fresh policy feeding via the UI.\n")
    finally:
        db.close()

if __name__ == "__main__":
    reset_to_clean_slate()
