from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# SQLite connection args for multi-threaded FastAPI access
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def migrate_sqlite_schema():
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    
    # 1. Ensure all tables are created first
    Base.metadata.create_all(bind=engine)

    table_cols = {
        "query_audit_logs": [
            ("grok_invoked", "BOOLEAN DEFAULT 0"),
            ("prompt_tokens", "INTEGER DEFAULT 0"),
            ("completion_tokens", "INTEGER DEFAULT 0"),
            ("total_tokens", "INTEGER DEFAULT 0"),
            ("estimated_cost_usd", "FLOAT DEFAULT 0.0"),
            ("supporting_evidence_references", "TEXT DEFAULT '[]'"),
            ("validation_status", "VARCHAR DEFAULT 'passed'"),
            ("request_id", "VARCHAR DEFAULT NULL"),
            ("query_category", "VARCHAR DEFAULT 'POLICY'"),
            ("source_section_ids", "TEXT DEFAULT '[]'"),
            ("error_reason", "VARCHAR DEFAULT NULL"),
            ("cache_entry_id", "VARCHAR DEFAULT NULL")
        ],
        "policies": [
            ("content_hash", "VARCHAR DEFAULT NULL"),
            ("parsed_sections", "TEXT DEFAULT '[]'")
        ],
        "policy_versions": [
            ("content_hash", "VARCHAR DEFAULT NULL"),
            ("parsed_sections", "TEXT DEFAULT '[]'")
        ],
        "cached_entries": [
            ("source_section_ids", "TEXT DEFAULT '[]'"),
            ("source_content_hashes", "TEXT DEFAULT '{}'"),
            ("source_citation", "TEXT DEFAULT NULL"),
            ("last_validated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
            ("invalidation_reason", "VARCHAR DEFAULT NULL")
        ]
    }

    with engine.connect() as conn:
        for tbl, cols in table_cols.items():
            try:
                existing = [c[1] for c in conn.execute(text(f"PRAGMA table_info({tbl});")).fetchall()]
                for col_name, col_type in cols:
                    if col_name not in existing:
                        conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_type};"))
                conn.commit()
            except Exception as e:
                print(f"Notice: SQLite migration check on {tbl}: {e}")

# Run column migrations
migrate_sqlite_schema()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
