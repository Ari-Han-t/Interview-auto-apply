import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from backend/ or project root
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))

load_dotenv(os.path.join(backend_dir, ".env"))
load_dotenv(os.path.join(root_dir, ".env"))

default_db_path = os.path.join(backend_dir, "autoapply.db").replace("\\", "/")

class Settings(BaseSettings):
    PROJECT_NAME: str = "Interview AutoApply"
    DATABASE_URL: str = f"sqlite:///{default_db_path}"
    SECRET_KEY: str = "supersecretkey_please_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Local demo mode only. When enabled, protected routes use the first active
    # user if no valid login cookie is present.
    AUTH_DISABLED: bool = False
    CORS_ORIGINS: str = ""
    ALLOWED_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1|.*\.onrender\.com|.*\.railway\.app|.*\.vercel\.app)(:\d+)?$"

    # --- LLM routing -------------------------------------------------------
    # Primary provider used by get_llm(): openrouter | openai | groq | gemini
    # | anthropic (claude) | azure
    LLM_PROVIDER: str = "openrouter"
    # Comma-separated fallback chain, tried in order when the primary fails.
    LLM_FALLBACK_PROVIDERS: str = "groq,openai,gemini,anthropic"

    # --- API keys (comma-separated lists enable key rotation) --------------
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""  # alias for GEMINI_API_KEY
    ANTHROPIC_API_KEY: str = ""  # Claude
    CLAUDE_API_KEY: str = ""  # alias for ANTHROPIC_API_KEY
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""  # e.g. https://my-resource.openai.azure.com
    AZURE_OPENAI_DEPLOYMENT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    # --- Models ------------------------------------------------------------
    OPENROUTER_MODEL: str = "openai/gpt-oss-120b"
    OPENROUTER_PROVIDER: str = "Groq"  # OpenRouter routing preference
    OPENAI_MODEL: str = "gpt-4o-mini"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL: str = "gemini-3.8-flash"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    AZURE_OPENAI_MODEL: str = ""  # defaults to AZURE_OPENAI_DEPLOYMENT
    RESUME_FALLBACK_MODEL: str = "openai/gpt-oss-120b"

    class Config:
        env_file = [os.path.join(backend_dir, ".env"), os.path.join(root_dir, ".env"), ".env"]
        extra = "ignore"

settings = Settings()
