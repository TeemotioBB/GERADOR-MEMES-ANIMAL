from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from models import RenderSettings


FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
]


def font_path() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Nenhuma fonte serif compatível foi encontrada no servidor.")


def parse_hex_color(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def prepare_background(source: Image.Image, width: int, height: int, fit_mode: str) -> Image.Image:
    source = ImageOps.exif_transpose(source).convert("RGB")
    if fit_mode == "stretch":
        return source.resize((width, height), Image.Resampling.LANCZOS)
    if fit_mode == "contain":
        contained = ImageOps.contain(source, (width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height), contained.getpixel((0, 0)))
        x = (width - contained.width) // 2
        y = (height - contained.height) // 2
        canvas.paste(contained, (x, y))
        return canvas
    return ImageOps.fit(source, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    if not paragraphs:
        return [""]

    lines: list[str] = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        words = paragraph.split()
        current = ""
        for word in words:
            test = word if not current else f"{current} {word}"
            if _text_width(draw, test, font) <= max_width:
                current = test
                continue

            if current:
                lines.append(current)
                current = word
            else:
                # Palavra excepcionalmente longa: quebra por caracteres.
                chunk = ""
                for char in word:
                    test_chunk = chunk + char
                    if chunk and _text_width(draw, test_chunk, font) > max_width:
                        lines.append(chunk)
                        chunk = char
                    else:
                        chunk = test_chunk
                current = chunk
        if current:
            lines.append(current)
        if paragraph_index < len(paragraphs) - 1:
            lines.append("")
    return lines


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    font_max: int,
    font_min: int,
    line_spacing: float,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    chosen_path = str(font_path())
    for size in range(font_max, font_min - 1, -1):
        font = ImageFont.truetype(chosen_path, size=size)
        lines = wrap_text(draw, text, font, max_width)
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        natural_height = bbox[3] - bbox[1]
        line_height = max(1, round(natural_height * line_spacing))
        total_height = line_height * len(lines)
        widest = max((_text_width(draw, line, font) for line in lines), default=0)
        if widest <= max_width and total_height <= max_height:
            return font, lines, line_height

    font = ImageFont.truetype(chosen_path, size=font_min)
    lines = wrap_text(draw, text, font, max_width)
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_height = max(1, round((bbox[3] - bbox[1]) * line_spacing))
    return font, lines, line_height


def render_post(image_bytes: bytes, phrase: str, config: RenderSettings) -> Image.Image:
    with Image.open(io.BytesIO(image_bytes)) as source:
        canvas = prepare_background(source, config.width, config.height, config.fit_mode)

    draw = ImageDraw.Draw(canvas)
    margin = round(config.width * config.text_margin_pct / 100)
    box_x = margin
    box_y = round(config.height * config.text_top_pct / 100)
    box_width = config.width - (margin * 2)
    box_height = round(config.height * config.text_height_pct / 100)

    font, lines, line_height = fit_text(
        draw,
        phrase,
        box_width,
        box_height,
        config.font_max,
        config.font_min,
        config.line_spacing,
    )
    total_height = line_height * len(lines)
    y = box_y + max(0, (box_height - total_height) // 2)
    color = parse_hex_color(config.text_color)

    for line in lines:
        if line:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = box_x + (box_width - line_width) / 2
            draw.text((x, y), line, fill=color, font=font)
        y += line_height

    watermark = config.watermark.strip()
    if watermark:
        wm_font = ImageFont.truetype(str(font_path()), size=config.watermark_size)
        wm_x = round(config.width * config.watermark_x_pct / 100)
        wm_y = round(config.height * config.watermark_y_pct / 100)
        draw.text((wm_x, wm_y), watermark, fill=parse_hex_color(config.watermark_color), font=wm_font)

    return canvas


def render_post_bytes(image_bytes: bytes, phrase: str, config: RenderSettings) -> bytes:
    image = render_post(image_bytes, phrase, config)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=config.jpeg_quality, optimize=True, subsampling=0)
    return output.getvalue()


def create_static_video(
    image_path: Path,
    video_path: Path,
    duration: float,
    width: int,
    height: int,
    music_path: Path | None = None,
    music_volume: float = 0.20,
) -> None:
    """Cria um MP4 estático e, quando escolhida, mistura a música fixa do projeto."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg não foi encontrado no servidor.")
    if music_path is not None and not music_path.is_file():
        raise FileNotFoundError(f"Arquivo de música não encontrado: {music_path.name}")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
    ]

    if music_path is not None:
        # Repete a faixa caso o usuário escolha uma duração maior que a música.
        command.extend(["-stream_loop", "-1", "-i", str(music_path)])

    command.extend(
        [
            "-t",
            f"{duration:.3f}",
            "-r",
            "30",
            "-vf",
            f"scale={width}:{height}:flags=lanczos,format=yuv420p",
            "-map",
            "0:v:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
        ]
    )

    if music_path is not None:
        safe_volume = max(0.0, min(float(music_volume), 1.0))
        fade_duration = min(0.35, max(0.10, duration / 4))
        fade_out_start = max(0.0, duration - fade_duration)
        audio_filter = (
            f"volume={safe_volume:.3f},"
            f"afade=t=in:st=0:d={fade_duration:.3f},"
            f"afade=t=out:st={fade_out_start:.3f}:d={fade_duration:.3f}"
        )
        command.extend(
            [
                "-map",
                "1:a:0",
                "-af",
                audio_filter,
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "44100",
            ]
        )
    else:
        command.append("-an")

    command.extend(["-movflags", "+faststart", str(video_path)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=max(120, int(duration * 20)),
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg falhou: {result.stderr.strip()}")
