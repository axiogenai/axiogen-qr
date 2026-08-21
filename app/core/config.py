from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Axiogen QR"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    ENVIRONMENT: str = "production"
    ENABLE_DOCS: bool = True  # Can be disabled in production via ENABLE_DOCS=false
    
    # Server & Domain
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    PUBLIC_URL: str = "https://api.axiogen.in"
    REDIRECT_BASE_URL: str = "https://api.axiogen.in/r"
    MEDIA_BASE_URL: str = "https://api.axiogen.in/m"
    MAX_UPLOAD_SIZE_MB: int = 25
    
    # Security
    SECRET_KEY: str = "axiogen_qr_super_secret_production_key_2026_jwt_token"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database (PostgreSQL) - with SQLite local development fallback
    DATABASE_URL: str = "sqlite+aiosqlite:///./axiogen_qr.db"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "axiogen_qr"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Storage
    STORAGE_TYPE: str = "local"  # 'local' or 's3'
    UPLOAD_DIR: str = "./uploads"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://voice.axiogen.in",
        "https://api.axiogen.in",
        "https://qr.axiogen.in",
        "https://dashboard.axiogen.in"
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
