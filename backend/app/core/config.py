import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Root directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Governed Semantic Cache"
    API_V1_STR: str = "/api"
    ENV: str = "development"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'cache_governance.db'}"
    
    # ML Models & Paths
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    
    MODELS_DIR: Path = ARTIFACTS_DIR / "models"
    INDEXES_DIR: Path = ARTIFACTS_DIR / "indexes"
    EVALUATIONS_DIR: Path = ARTIFACTS_DIR / "evaluations"
    SYNTHETIC_DATA_DIR: Path = DATA_DIR / "synthetic_policies"
    DATASETS_DIR: Path = DATA_DIR / "datasets"
    
    # Governance Defaults
    DEFAULT_CACHE_THRESHOLD: float = 0.50
    DEFAULT_MIN_COSINE_SIM: float = 0.65
    DEFAULT_TOP_K: int = 5
    TARGET_FHR: float = 0.01  # 1% False-Hit Rate Target
    CONFIDENCE_LEVEL: float = 0.95
    CACHE_EXPIRY_DAYS: int = 90
    
    # Fallback & Grounding Providers
    FALLBACK_PROVIDER: str = "grounded_company_policy_engine"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GROK_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure directories exist
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
settings.INDEXES_DIR.mkdir(parents=True, exist_ok=True)
settings.EVALUATIONS_DIR.mkdir(parents=True, exist_ok=True)
settings.SYNTHETIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.DATASETS_DIR.mkdir(parents=True, exist_ok=True)
