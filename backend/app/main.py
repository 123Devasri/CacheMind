import sys
from pathlib import Path

# Add backend directory to sys.path so running 'python app/main.py' or 'python -m app.main' works seamlessly
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router
from app.db.session import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Governed Semantic Cache with FAISS, Logistic Regression, Isotonic Probability Calibration, and Deterministic Policy Validation.",
    version="1.0.0"
)

# CORS setup for React development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Governed Semantic Cache API is running.",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }

if __name__ == "__main__":
    import uvicorn
    # Use app instance directly so python app/main.py works from any directory without ModuleNotFoundError
    uvicorn.run(app, host="127.0.0.1", port=8000)
