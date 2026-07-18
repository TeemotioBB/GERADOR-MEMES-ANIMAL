from pathlib import Path

from PIL import Image

from config import settings
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


def test_static_video_is_created(tmp_path: Path):
    config = RenderSettings(
        width=540,
        height=960,
        font_max=36,
        font_min=20,
        watermark_size=20,
        video_duration=1,
    )
    image_path = tmp_path / "post.jpg"
    image_path.write_bytes(render_post_bytes(settings.sample_image.read_bytes(), "Teste de vídeo estático.", config))
    video_path = tmp_path / "post.mp4"

    create_static_video(image_path, video_path, 1, 540, 960)
    assert video_path.exists()
    assert video_path.stat().st_size > 1000
