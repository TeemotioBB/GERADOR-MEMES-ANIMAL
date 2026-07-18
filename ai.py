from __future__ import annotations

import json
import re
from pathlib import Path

from config import settings
from models import PhraseRequest


class PhraseGenerationError(RuntimeError):
    pass


def read_default_prompt() -> str:
    return Path(settings.default_prompt).read_text(encoding="utf-8")


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(cleaned[start : end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError as exc:
            raise PhraseGenerationError("A IA retornou um JSON inválido.") from exc

    raise PhraseGenerationError("A IA não retornou o objeto JSON esperado.")


def _clean_phrase(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    phrase = re.sub(r"\s+", " ", value).strip(" \t\r\n\"'•-")
    if len(phrase) < 8 or len(phrase) > 300:
        return None
    return phrase


def generate_phrases(payload: PhraseRequest) -> tuple[list[str], str]:
    api_key = payload.api_key.strip() or settings.openai_api_key
    if not api_key:
        raise PhraseGenerationError(
            "Configure OPENAI_API_KEY no Railway ou informe uma chave temporária no formulário."
        )

    model = payload.model.strip() or settings.openai_model
    base_prompt = payload.prompt.strip() or read_default_prompt()
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise PhraseGenerationError("O pacote openai não está instalado no servidor.") from exc

    client = OpenAI(api_key=api_key, timeout=90.0, max_retries=2)

    collected: list[str] = []
    seen: set[str] = set()
    remaining = payload.count
    attempts = 0
    max_attempts = max(3, ((payload.count + 24) // 25) + 3)

    while remaining > 0:
        attempts += 1
        if attempts > max_attempts:
            raise PhraseGenerationError(
                f"A IA retornou somente {len(collected)} de {payload.count} frases válidas. Tente novamente."
            )
        batch_size = min(remaining, 25)
        user_input = f"""
Gere exatamente {batch_size} frases.
Tema principal: {payload.theme}
Tom: {payload.tone}
Intensidade: {payload.intensity}

Exemplos de referência de estilo, sem copiar literalmente:
{payload.examples.strip() or '(nenhum exemplo adicional)'}

Já geradas neste lote e que não podem ser repetidas:
{json.dumps(collected[-30:], ensure_ascii=False)}
""".strip()

        try:
            response = client.responses.create(
                model=model,
                instructions=base_prompt,
                input=user_input,
                store=False,
            )
        except Exception as exc:  # SDK expõe diferentes subclasses entre versões
            raise PhraseGenerationError(f"Erro ao chamar a API de IA: {exc}") from exc

        data = _extract_json(response.output_text or "")
        raw_phrases = data.get("phrases", [])
        if not isinstance(raw_phrases, list):
            raise PhraseGenerationError("O campo 'phrases' retornado pela IA não é uma lista.")

        before = len(collected)
        for item in raw_phrases:
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
            raise PhraseGenerationError("A IA não retornou frases aproveitáveis. Tente ajustar o prompt.")

        remaining = payload.count - len(collected)

    return collected[: payload.count], model
