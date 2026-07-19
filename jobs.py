from __future__ import annotations

import csv
import json
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import resolve_music_track, settings
from models import RenderSettings
from renderer import create_static_video, render_post_bytes


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="render-job")
_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def _job_dir(job_id: str) -> Path:
    return settings.storage_dir / job_id


def _write_status(job_id: str) -> None:
    path = _job_dir(job_id) / "status.json"
    path.write_text(json.dumps(_jobs[job_id], ensure_ascii=False, indent=2), encoding="utf-8")


def cleanup_old_jobs() -> None:
    cutoff = time.time() - (settings.job_ttl_hours * 3600)
    for child in settings.storage_dir.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                for nested in sorted(child.rglob("*"), key=lambda item: len(item.parts), reverse=True):
                    if nested.is_file() or nested.is_symlink():
                        nested.unlink(missing_ok=True)
                    elif nested.is_dir():
                        nested.rmdir()
                child.rmdir()
        except OSError:
            continue


def create_job(image_bytes: bytes, phrases: list[str], config: RenderSettings) -> str:
    cleanup_old_jobs()
    job_id = uuid.uuid4().hex
    directory = _job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "source.jpg").write_bytes(image_bytes)

    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "total": len(phrases),
            "message": "Na fila",
            "error": None,
            "download_ready": False,
            "created_at": int(time.time()),
        }
        _write_status(job_id)

    _executor.submit(_run_job, job_id, image_bytes, phrases, config)
    return job_id


def _run_job(job_id: str, image_bytes: bytes, phrases: list[str], config: RenderSettings) -> None:
    directory = _job_dir(job_id)
    images_dir = directory / "imagens"
    videos_dir = directory / "videos"
    images_dir.mkdir(exist_ok=True)
    videos_dir.mkdir(exist_ok=True)

    try:
        with _lock:
            _jobs[job_id]["status"] = "processing"
            _jobs[job_id]["message"] = "Gerando arquivos"
            _write_status(job_id)

        music_label, music_path = resolve_music_track(config.music_track)

        manifest: list[dict] = []
        for index, phrase in enumerate(phrases, start=1):
            slug = f"post_{index:03d}"
            image_path = images_dir / f"{slug}.jpg"
            video_path = videos_dir / f"{slug}.mp4"

            image_path.write_bytes(render_post_bytes(image_bytes, phrase, config))
            create_static_video(
                image_path,
                video_path,
                config.video_duration,
                config.width,
                config.height,
                music_path=music_path,
                music_volume=config.music_volume,
            )
            manifest.append(
                {
                    "numero": index,
                    "frase": phrase,
                    "imagem": f"imagens/{image_path.name}",
                    "video": f"videos/{video_path.name}",
                    "duracao_segundos": config.video_duration,
                    "musica": music_label,
                    "volume_musica": round(config.music_volume * 100),
                }
            )

            with _lock:
                _jobs[job_id]["progress"] = index
                _jobs[job_id]["message"] = f"Gerado {index} de {len(phrases)}"
                _write_status(job_id)

        (directory / "manifest.json").write_text(
            json.dumps({"config": config.model_dump(), "posts": manifest}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        with (directory / "frases.csv").open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=["numero", "frase", "imagem", "video", "musica", "volume_musica"],
            )
            writer.writeheader()
            for item in manifest:
                writer.writerow({key: item[key] for key in writer.fieldnames})

        zip_path = directory / "lote_cretino_factory.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for file_path in images_dir.glob("*.jpg"):
                archive.write(file_path, file_path.relative_to(directory))
            for file_path in videos_dir.glob("*.mp4"):
                archive.write(file_path, file_path.relative_to(directory))
            archive.write(directory / "manifest.json", "manifest.json")
            archive.write(directory / "frases.csv", "frases.csv")

        with _lock:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["progress"] = len(phrases)
            _jobs[job_id]["message"] = "Lote pronto"
            _jobs[job_id]["download_ready"] = True
            _write_status(job_id)
    except Exception as exc:
        with _lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["message"] = "Falha ao gerar o lote"
            _jobs[job_id]["error"] = str(exc)
            _write_status(job_id)


def get_job(job_id: str) -> dict | None:
    with _lock:
        if job_id in _jobs:
            return dict(_jobs[job_id])

    status_path = _job_dir(job_id) / "status.json"
    if status_path.exists():
        try:
            return json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def get_zip_path(job_id: str) -> Path | None:
    path = _job_dir(job_id) / "lote_cretino_factory.zip"
    return path if path.exists() else None
