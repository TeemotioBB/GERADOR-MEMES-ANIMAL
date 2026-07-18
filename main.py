from __future__ import annotations

import json
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import ValidationError

from ai import PhraseGenerationError, generate_phrases, read_default_prompt
from auth import OptionalBasicAuthMiddleware
from config import BASE_DIR, settings
from jobs import cleanup_old_jobs, create_job, get_job, get_zip_path
from models import PhraseRequest, PhraseResponse, RenderSettings
from renderer import render_post_bytes


MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_old_jobs()
    yield


app = FastAPI(title="Cretino Factory", version="1.0.0", lifespan=lifespan)
app.add_middleware(OptionalBasicAuthMiddleware)


async def read_uploaded_image(file: UploadFile | None) -> bytes:
    if file is None or not file.filename:
        return settings.sample_image.read_bytes()
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Envie um arquivo de imagem válido.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="A imagem deve ter no máximo 15 MB.")
    if not data:
        raise HTTPException(status_code=400, detail="A imagem enviada está vazia.")
    return data


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    html = (BASE_DIR / "index.html").read_text(encoding="utf-8")
    api_configured = bool(settings.xai_api_key)
    replacements = {
        "{{ default_prompt }}": read_default_prompt(),
        "{{ default_model }}": settings.xai_model,
        "{{ 'true' if api_configured else 'false' }}": "true" if api_configured else "false",
        "{{ max_batch_size }}": str(settings.max_batch_size),
        "{{ 'ok' if api_configured else 'warn' }}": "ok" if api_configured else "warn",
        "{{ 'API configurada no servidor' if api_configured else 'API ainda não configurada' }}": (
            "API configurada no servidor" if api_configured else "API ainda não configurada"
        ),
    }
    for marker, value in replacements.items():
        html = html.replace(marker, value)
    return HTMLResponse(html)


@app.get("/styles.css")
async def stylesheet():
    return FileResponse(BASE_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
async def javascript():
    return FileResponse(BASE_DIR / "app.js", media_type="application/javascript")


@app.get("/sample-dog.jpg")
async def sample_dog():
    return FileResponse(BASE_DIR / "sample-dog.jpg", media_type="image/jpeg")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/phrases", response_model=PhraseResponse)
def phrases(payload: PhraseRequest):
    try:
        generated, model = generate_phrases(payload)
        return PhraseResponse(phrases=generated, model=model)
    except PhraseGenerationError as exc:
        print(f"[phrase-generation] {exc}", flush=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao gerar frases: {exc.__class__.__name__}: {exc}",
        ) from exc


@app.post("/api/preview")
async def preview(
    phrase: str = Form(...),
    settings_json: str = Form(...),
    image: UploadFile | None = File(default=None),
):
    if not phrase.strip():
        raise HTTPException(status_code=400, detail="Informe uma frase para a prévia.")
    try:
        config = RenderSettings.model_validate_json(settings_json)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc

    image_bytes = await read_uploaded_image(image)
    try:
        rendered = render_post_bytes(image_bytes, phrase.strip(), config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Não foi possível renderizar: {exc}") from exc
    return Response(content=rendered, media_type="image/jpeg")


@app.post("/api/jobs")
async def start_job(
    phrases_json: str = Form(...),
    settings_json: str = Form(...),
    image: UploadFile | None = File(default=None),
):
    try:
        phrases_data = json.loads(phrases_json)
        if not isinstance(phrases_data, list):
            raise ValueError
        phrases = [str(item).strip() for item in phrases_data if str(item).strip()]
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Lista de frases inválida.") from exc

    if not phrases:
        raise HTTPException(status_code=400, detail="Adicione pelo menos uma frase.")
    if len(phrases) > settings.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"O lote pode ter no máximo {settings.max_batch_size} frases nesta instalação.",
        )

    try:
        config = RenderSettings.model_validate_json(settings_json)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc

    image_bytes = await read_uploaded_image(image)
    job_id = create_job(image_bytes, phrases, config)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Lote não encontrado.")
    return job


@app.get("/api/jobs/{job_id}/download")
async def download(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Lote não encontrado.")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail="O lote ainda não está pronto.")
    zip_path = get_zip_path(job_id)
    if not zip_path:
        raise HTTPException(status_code=404, detail="Arquivo ZIP não encontrado.")
    return FileResponse(zip_path, filename="lote_cretino_factory.zip", media_type="application/zip")
