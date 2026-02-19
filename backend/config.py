"""
config.py — Application settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ALLOWED_MODELS = os.getenv("ALLOWED_MODELS", "mistral:latest,llama3.2:latest,gemma2:2b,qwen2.5:1.5b").split(",")

# ── Database (Akamai PostgreSQL) ──────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "17581"))
DB_NAME = os.getenv("DB_NAME", "defaultdb")
DB_USER = os.getenv("DB_USER", "avnadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SSL_CERT = Path(os.getenv("DB_SSL_CERT", "./certs/ca-certificate.crt"))

# ── Sandbox / Bridge ─────────────────────────────────────────────────────────
SDK_PATH = Path(os.getenv("SDK_PATH", "./sdk/platform_sdk.py"))
MAX_EXECUTION_TIME = int(os.getenv("MAX_EXECUTION_TIME", "120"))
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "4000"))
MAX_AI_CALLS = int(os.getenv("MAX_AI_CALLS_PER_EXECUTION", "10"))

# ── WasmEdge ─────────────────────────────────────────────────────────────────
USE_WASMEDGE = os.getenv("USE_WASMEDGE", "false").lower() == "true"
WASM_PYTHON_PATH = os.getenv("WASM_PYTHON_PATH", "")  # path to python-wasmedge.wasm
WASM_PYTHON_DIR = os.getenv("WASM_PYTHON_DIR", "")     # dir containing usr/local/lib (stdlib)