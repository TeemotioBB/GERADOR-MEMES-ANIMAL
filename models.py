from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PhraseRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=100)
    theme: str = Field(default="relacionamento, rotina, dinheiro e situações cotidianas", max_length=500)
    tone: str = Field(default="humor debochado, absurdo e compartilhável", max_length=500)
    intensity: Literal["leve", "médio", "pesado"] = "médio"
    examples: str = Field(default="", max_length=12_000)
    prompt: str = Field(default="", max_length=20_000)
    model: str = Field(default="", max_length=100)
    api_key: str = Field(default="", max_length=300)


class PhraseResponse(BaseModel):
    phrases: list[str]
    model: str


class RenderSettings(BaseModel):
    width: int = Field(default=1080, ge=540, le=2160)
    height: int = Field(default=1920, ge=675, le=3840)
    fit_mode: Literal["cover", "contain", "stretch"] = "cover"
    text_top_pct: float = Field(default=13.5, ge=0, le=85)
    text_height_pct: float = Field(default=31.0, ge=8, le=80)
    text_margin_pct: float = Field(default=9.0, ge=2, le=35)
    font_max: int = Field(default=66, ge=20, le=180)
    font_min: int = Field(default=38, ge=14, le=160)
    line_spacing: float = Field(default=1.22, ge=0.9, le=2.0)
    text_color: str = Field(default="#000000", pattern=r"^#[0-9a-fA-F]{6}$")
    watermark: str = Field(default="@minhapagina", max_length=80)
    watermark_x_pct: float = Field(default=7.5, ge=0, le=90)
    watermark_y_pct: float = Field(default=84.0, ge=0, le=96)
    watermark_size: int = Field(default=34, ge=14, le=100)
    watermark_color: str = Field(default="#111111", pattern=r"^#[0-9a-fA-F]{6}$")
    video_duration: float = Field(default=8.0, ge=1.0, le=60.0)
    jpeg_quality: int = Field(default=95, ge=70, le=100)

    # O navegador envia somente um identificador; o servidor resolve o arquivo fixo.
    music_track: str = Field(default="none", min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    music_volume: float = Field(default=0.20, ge=0.0, le=1.0)

    @field_validator("font_min")
    @classmethod
    def min_not_over_max(cls, value: int, info):
        max_value = info.data.get("font_max")
        if max_value is not None and value > max_value:
            raise ValueError("font_min não pode ser maior que font_max")
        return value
