"""
core/config.py — Centralised settings loaded from environment / .env file.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Server ────────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "*"

    # ── Database (Akamai Managed PostgreSQL) ──────────────────────────────────
    DB_USER: str = "akmadmin"
    DB_PASS: str = "CHANGE_ME"
    DB_HOST: str = "localhost"
    DB_PORT: int = 17581
    DB_NAME: str = "defaultdb"
    CA_CERT_PATH: Path = Path("certs/ca-certificate.crt")

    # ── Ollama ────────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TIMEOUT: int = 60
    USE_MOCK_AI: bool = False

    # ── WasmEdge ──────────────────────────────────────────────────────────────
    WASM_PYTHON_PATH: str = "/opt/wasmedge-python/bin/python-3.11.1-wasmedge-aot.wasm"
    WASM_PYTHON_DIR: str = "/opt/wasmedge-python"

    # ── Plugins ───────────────────────────────────────────────────────────────
    PLUGINS_DIR: Path = Path("./plugins/deployed")
    SDK_PATH: Path = Path("./backend/sdk/platform_sdk.py")

    # ── Limits ────────────────────────────────────────────────────────────────
    MAX_EXECUTION_TIME: int = 30
    MAX_PROMPT_LENGTH: int = 4000
    MAX_AI_CALLS_PER_EXECUTION: int = 10

    # ── Models ────────────────────────────────────────────────────────────────
    ALLOWED_MODELS: str = "llama3,llava,mistral"

    @property
    def allowed_models_list(self) -> list[str]:
        return [m.strip() for m in self.ALLOWED_MODELS.split(",") if m.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()