from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR


def _reasoning_effort() -> str:
    value = os.getenv("XAI_REASONING_EFFORT", "medium").strip().lower()
    return value if value in {"low", "medium", "high"} else "medium"


@dataclass(frozen=True)
class Settings:
    # Grok / xAI
    xai_api_key: str = os.getenv("XAI_API_KEY", "").strip()
    xai_model: str = os.getenv("XAI_MODEL", "grok-4.5").strip() or "grok-4.5"
    xai_base_url: str = (
        os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").strip().rstrip("/")
        or "https://api.x.ai/v1"
    )
    xai_reasoning_effort: str = _reasoning_effort()

    # Proteção e limites do sistema
    app_username: str = os.getenv("APP_USERNAME", "").strip()
    app_password: str = os.getenv("APP_PASSWORD", "").strip()
    max_batch_size: int = max(1, min(int(os.getenv("MAX_BATCH_SIZE", "50")), 200))
    job_ttl_hours: int = max(1, int(os.getenv("JOB_TTL_HOURS", "24")))
    storage_dir: Path = Path(os.getenv("STORAGE_DIR", "/tmp/cretino-factory"))

    # Arquivos locais — todos ficam na raiz do repositório
    sample_image: Path = BASE_DIR / "sample-dog.jpg"
    default_prompt: Path = BASE_DIR / "default_prompt.txt"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
