import json
import subprocess
from pathlib import Path

from PIL import Image

from config import resolve_music_track, settings
from models import RenderSettings
from renderer import create_static_video, render_post_bytes


def test_render_post_creates_expected_dimensions(tmp_path: Path):
    config = RenderSettings(width=540, height=960, font_max=36, font_min=20, watermark_size=20)
    data = settings.sample_image.read_bytes()
    output = render_post_bytes(
        data,
        "Se só eu sei a senha do meu cartão, como a maquininha sabe que eu errei?",
        config,
    )
    image_path = tmp_path / "post.jpg"
    image_path.write_bytes(output)

    with Image.open(image_path) as image:
        assert image.size == (540, 960)
        assert image.mode == "RGB"


def _make_image(tmp_path: Path) -> Path:
    config = RenderSettings(
        width=540,
        height=960,
        font_max=36,
        font_min=20,
        watermark_size=20,
        video_duration=1,
    )
    image_path = tmp_path / "post.jpg"
    image_path.write_bytes(
        render_post_bytes(settings.sample_image.read_bytes(), "Teste de vídeo estático.", config)
    )
    return image_path


def _stream_types(video_path: Path) -> list[str]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return [stream["codec_type"] for stream in payload["streams"]]


def test_static_video_is_created_without_audio(tmp_path: Path):
    image_path = _make_image(tmp_path)
    video_path = tmp_path / "post-sem-musica.mp4"

    create_static_video(image_path, video_path, 1, 540, 960)

    assert video_path.exists()
    assert video_path.stat().st_size > 1000
    assert _stream_types(video_path) == ["video"]


def test_static_video_is_created_with_fixed_music(tmp_path: Path):
    image_path = _make_image(tmp_path)
    video_path = tmp_path / "post-com-musica.mp4"
    _, music_path = resolve_music_track("la_isla_bonita")
    assert music_path is not None

    create_static_video(
        image_path,
        video_path,
        1,
        540,
        960,
        music_path=music_path,
        music_volume=0.20,
    )

    assert video_path.exists()
    assert video_path.stat().st_size > 1000
    assert _stream_types(video_path) == ["video", "audio"]
