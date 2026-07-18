from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from config import settings
from models import PhraseRequest


class PhraseGenerationError(RuntimeError):
    pass


class PhraseBatch(BaseModel):
    phrases: list[str] = Field(
        min_length=1,
        max_length=10,
        description="Lista de frases em português brasileiro",
    )


def read_default_prompt() -> str:
    return Path(settings.default_prompt).read_text(encoding="utf-8")


def _clean_phrase(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    phrase = re.sub(r"\s+", " ", value).strip(" \t\r\n\"'•-")
    if len(phrase) < 8 or len(phrase) > 300:
        return None
    return phrase


def _find_refusal(value: Any) -> str | None:
    """Procura uma recusa no objeto retornado pelo SDK sem depender da versão."""
    if isinstance(value, dict):
        refusal = value.get("refusal")
        if isinstance(refusal, str) and refusal.strip():
            return refusal.strip()
        for child in value.values():
            found = _find_refusal(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_refusal(child)
            if found:
                return found
    return None


def generate_phrases(payload: PhraseRequest) -> tuple[list[str], str]:
    api_key = payload.api_key.strip() or settings.xai_api_key
    if not api_key:
        raise PhraseGenerationError(
            "Configure XAI_API_KEY no Railway ou informe uma chave temporária da xAI no formulário."
        )

    model = payload.model.strip() or settings.xai_model
    base_prompt = payload.prompt.strip() or read_default_prompt()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise PhraseGenerationError(
            "O pacote openai não está instalado no servidor. Ele é usado como cliente compatível da xAI."
        ) from exc

    client = OpenAI(
        api_key=api_key,
        base_url=settings.xai_base_url,
        timeout=httpx.Timeout(300.0, connect=30.0),
        max_retries=2,
    )

    collected: list[str] = []
    seen: set[str] = set()
    remaining = payload.count
    attempts = 0
    max_attempts = max(4, ((payload.count + 9) // 10) + 3)

    while remaining > 0:
        attempts += 1
        if attempts > max_attempts:
            raise PhraseGenerationError(
                f"O Grok retornou somente {len(collected)} de {payload.count} frases válidas. Tente novamente."
            )

        # Lotes de até 10 deixam a saída estruturada mais confiável e variada.
        batch_size = min(remaining, 10)
        user_input = f"""
Crie exatamente {batch_size} frases inéditas.

Tema escolhido no painel: {payload.theme}
Tom escolhido no painel: {payload.tone}
Intensidade: {payload.intensity}

Referências de estilo fornecidas pelo usuário. Aprenda somente o ritmo, o tipo de humor e o nível de ousadia. Não copie e não faça paráfrases próximas:
{payload.examples.strip() or '(nenhuma referência adicional)'}

Frases já aprovadas neste lote e que não podem ser repetidas nem reaproveitadas:
{json.dumps(collected[-30:], ensure_ascii=False)}

Obedeça ao prompt do sistema e devolva exatamente {batch_size} strings no campo phrases.
""".strip()

        try:
            # A xAI documenta o uso de responses.parse com Pydantic e o endpoint OpenAI-compatible.
            response = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": base_prompt},
                    {"role": "user", "content": user_input},
                ],
                text_format=PhraseBatch,
                reasoning={"effort": settings.xai_reasoning_effort},
                store=False,
                max_output_tokens=2000,
            )
        except Exception as exc:  # subclasses variam conforme a versão do SDK
            message = str(exc).strip() or exc.__class__.__name__
            print(
                f"[phrase-generation] xAI/Grok error ({exc.__class__.__name__}): {message}",
                flush=True,
            )
            raise PhraseGenerationError(f"Erro ao chamar o Grok: {message}") from exc

        parsed = response.output_parsed
        if parsed is None:
            dumped = response.model_dump() if hasattr(response, "model_dump") else {}
            refusal = _find_refusal(dumped)
            if refusal:
                raise PhraseGenerationError(
                    "O Grok recusou este pedido. Ajuste o prompt e tente novamente. Detalhe: " + refusal
                )
            raw = (getattr(response, "output_text", "") or "").strip()
            print(f"[phrase-generation] Empty parsed output. Raw: {raw[:800]}", flush=True)
            raise PhraseGenerationError(
                "A xAI respondeu, mas não entregou a estrutura esperada. Confira o modelo informado."
            )

        before = len(collected)
        for item in parsed.phrases:
            phrase = _clean_phrase(item)
            if not phrase:
                continue
            key = phrase.casefold()
            if key in seen:
                continue
            seen.add(key)
            collected.append(phrase)
            if len(collected) >= payload.count:
                break

        if len(collected) == before:
            raise PhraseGenerationError(
                "O Grok respondeu, mas nenhuma frase passou pela validação. Reduza as restrições do prompt."
            )

        remaining = payload.count - len(collected)

    return collected[: payload.count], model
