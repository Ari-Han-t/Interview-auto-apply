from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Interview AutoApply"
    DATABASE_URL: str = "sqlite:///./autoapply.db"
    SECRET_KEY: str = "supersecretkey_please_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GROQ_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
