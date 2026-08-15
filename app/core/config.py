import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    OPENAI_API_KEY: str = "mock-key-for-hr-ai-copilot"
    GOOGLE_CLIENT_ID: str = "mock-client-id"
    GOOGLE_CLIENT_SECRET: str = "mock-client-secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    GOOGLE_SHEET_ID: str = "mock-sheet-id"
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: str = "credentials.json"
    GMAIL_SENDER_EMAIL: str = "hr@company.com"
    GMAIL_APP_PASSWORD: str = "mock-app-password"
    DATABASE_URL: str = "sqlite:///./hr_copilot.db"
    
    JWT_SECRET: str = "super_secret_jwt_key_for_signing_tokens_12345"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    MCP_SERVER_URL: str = "http://localhost:8001"
    
    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
        extra = "ignore"

settings = Settings()
