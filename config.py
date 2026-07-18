from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
    app_username: str = os.getenv("APP_USERNAME", "").strip()
    app_password: str = os.getenv("APP_PASSWORD", "").strip()
    max_batch_size: int = max(1, min(int(os.getenv("MAX_BATCH_SIZE", "50")), 200))
    job_ttl_hours: int = max(1, int(os.getenv("JOB_TTL_HOURS", "24")))
    storage_dir: Path = Path(os.getenv("STORAGE_DIR", "/tmp/cretino-factory"))
    sample_image: Path = BASE_DIR / "sample-dog.jpg"
    default_prompt: Path = BASE_DIR / "default_prompt.txt"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
