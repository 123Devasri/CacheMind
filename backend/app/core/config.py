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
    
    # Base Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    
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
    FALLBACK_PROVIDER: str = "grok_api" # "grok_api", "grounded_company_policy_engine", "openai"
    
    # Official xAI Grok & Free Groq API Configuration
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "openai/gpt-oss-120b" # Supported: openai/gpt-oss-120b, openai/gpt-oss-20b, grok-2-latest
    XAI_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROK_API_KEY: str = "" # Alias for XAI/Groq API Key
    GROQ_API_KEY: str = "" # Free tier Groq API Key (gsk_...)
    
    # OpenAI Optional Fallback
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Unit Economics & Real Pricing (xAI Grok-2 published rates)
    # $2.00 per 1M prompt tokens ($0.000002/token)
    GROK_INPUT_TOKEN_PRICE_PER_M: float = 2.00
    # $10.00 per 1M completion tokens ($0.000010/token)
    GROK_OUTPUT_TOKEN_PRICE_PER_M: float = 10.00
    # Cache hit compute cost: ~$0.00005 per hit
    CACHE_HIT_UNIT_COST: float = 0.00005
    # Baseline LLM inference cost assumption when no cache used
    DEFAULT_LLM_QUERY_COST: float = 0.030

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
