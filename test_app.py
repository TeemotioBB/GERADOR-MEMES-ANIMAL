from fastapi.testclient import TestClient

from main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_home_loads():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Cretino Factory" in response.text
        assert "La Isla Bonita" in response.text
        assert 'value="la_isla_bonita" selected' in response.text


def test_individual_video_download():
    import json
    from config import settings

    render_settings = {
        "width": 540,
        "height": 960,
        "video_duration": 1,
        "watermark": "@teste",
    }
    with TestClient(app) as client:
        with settings.sample_image.open("rb") as image_file:
            response = client.post(
                "/api/render-video",
                data={
                    "phrase": "Uma frase de teste.",
                    "phrase_index": "3",
                    "settings_json": json.dumps(render_settings),
                },
                files={"image": ("sample.jpg", image_file, "image/jpeg")},
            )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")
    assert 'post_003.mp4' in response.headers["content-disposition"]
    assert len(response.content) > 1000
