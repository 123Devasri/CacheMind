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
    cols = [
        ("grok_invoked", "BOOLEAN DEFAULT 0"),
        ("prompt_tokens", "INTEGER DEFAULT 0"),
        ("completion_tokens", "INTEGER DEFAULT 0"),
        ("total_tokens", "INTEGER DEFAULT 0"),
        ("estimated_cost_usd", "FLOAT DEFAULT 0.0"),
        ("supporting_evidence_references", "TEXT DEFAULT '[]'"),
        ("validation_status", "VARCHAR DEFAULT 'passed'")
    ]
    with engine.connect() as conn:
        try:
            existing = [c[1] for c in conn.execute(text("PRAGMA table_info(query_audit_logs);")).fetchall()]
            for col_name, col_type in cols:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE query_audit_logs ADD COLUMN {col_name} {col_type};"))
            conn.commit()
        except Exception as e:
            print(f"Notice: SQLite migration check: {e}")

# Run column migrations
migrate_sqlite_schema()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
