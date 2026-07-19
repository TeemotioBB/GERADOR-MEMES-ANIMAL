from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR


@dataclass(frozen=True)
class MusicTrack:
    label: str
    path: Path


# Músicas fixas disponíveis no sistema.
# Para adicionar outra depois, coloque o MP3 na pasta music/ e registre aqui.
MUSIC_TRACKS: dict[str, MusicTrack] = {
    "la_isla_bonita": MusicTrack(
        label="La Isla Bonita — Madonna",
        path=BASE_DIR / "music" / "la-isla-bonita.mp3",
    ),
}


def _reasoning_effort() -> str:
    value = os.getenv("XAI_REASONING_EFFORT", "medium").strip().lower()
    return value if value in {"low", "medium", "high"} else "medium"


def _default_music_track() -> str:
    value = os.getenv("DEFAULT_MUSIC_TRACK", "la_isla_bonita").strip()
    return value if value in MUSIC_TRACKS else "none"


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

    # Música padrão da interface. "none" gera o vídeo sem áudio.
    default_music_track: str = _default_music_track()

    # Arquivos locais — todos ficam na raiz do repositório
    sample_image: Path = BASE_DIR / "sample-dog.jpg"
    default_prompt: Path = BASE_DIR / "default_prompt.txt"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)


def resolve_music_track(track_id: str) -> tuple[str, Path | None]:
    """Transforma o identificador seguro da tela em nome e caminho do MP3."""
    normalized = (track_id or "none").strip()
    if normalized == "none":
        return "Sem música", None

    track = MUSIC_TRACKS.get(normalized)
    if track is None:
        raise ValueError("A música selecionada não existe.")
    if not track.path.is_file():
        raise FileNotFoundError(f'O arquivo da música "{track.label}" não foi encontrado no projeto.')
    return track.label, track.path
