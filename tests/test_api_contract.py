import os

from tests.conftest import write_config


def test_core_read_apis_return_expected_shapes(client, app):
    auth = client.get("/api/auth/status")
    assert auth.status_code == 200
    auth_payload = auth.get_json()
    assert auth_payload["authenticated"] is True
    assert auth_payload["is_owner"] is True

    paths = app.config["PATH_CONTEXT"]
    model_path = os.path.join(paths.output_folder, "demo.ply")
    with open(model_path, "wb") as f:
        f.write(b"fake-ply")

    gallery = client.get("/api/gallery")
    assert gallery.status_code == 200
    gallery_payload = gallery.get_json()
    assert gallery_payload[0]["id"] == "demo"
    assert gallery_payload[0]["model_url"].startswith("/files/")

    download = client.get("/api/download/demo?format=ply")
    assert download.status_code == 200
    assert download.data == b"fake-ply"

    albums = client.get("/api/photo-albums")
    assert albums.status_code == 200
    assert albums.get_json()["albums"] == []

    tasks = client.get("/api/tasks")
    assert tasks.status_code == 200
    assert tasks.get_json() == {"tasks": [], "has_active": False}

    settings = client.get("/api/settings")
    assert settings.status_code == 200
    settings_payload = settings.get_json()
    assert settings_payload["model_format"] == "spz"
    assert settings_payload["workspace_folder"] == paths.workspace_folder


def test_export_missing_model_returns_json_error(client):
    response = client.get("/api/export/missing")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Model not found"}


def test_photo_album_media_api_lists_videos_and_supports_range(client, app, config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    video_path = album_dir / "小米办公Pro20260212-180739.mp4"
    video_path.write_bytes(b"0123456789")
    write_config(
        config_file,
        {
            "workspace_folder": str(workspace),
            "model_format": "spz",
            "access_control": {
                "enabled": False,
                "password_hash": "",
                "session_secret": "test-secret",
                "session_days": 30,
                "allow_localhost_bypass": True,
                "allow_remote_generation": False,
                "session_version": 1,
                "lan_bind_enabled": True,
            },
            "photo_gallery_roots": [{"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True}],
        },
    )

    albums = client.get("/api/photo-albums")
    assert albums.status_code == 200
    album_payload = albums.get_json()["albums"][0]
    assert album_payload["scan_status"] in {"needs_index", "idle"}

    scan = client.post("/api/photo-albums/album1/scan")
    assert scan.status_code == 200
    assert scan.get_json()["success"] is True

    albums = client.get("/api/photo-albums")
    assert albums.status_code == 200
    album_payload = albums.get_json()["albums"][0]
    assert album_payload["media_count"] == 1
    assert album_payload["video_count"] == 1
    assert album_payload["photo_count"] == 0
    assert album_payload["cover_thumb_url"].startswith("/api/video-poster/")

    list_response = client.get("/api/photo-albums/album1/photos?type=video")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert payload["total"] == 1
    assert payload["media_counts"] == {"all": 1, "image": 0, "photo": 0, "video": 1}
    item = payload["items"][0]
    assert item["media_type"] == "video"
    assert item["name"] == "小米办公Pro20260212-180739.mp4"
    assert item["poster_url"].startswith("/api/video-poster/")
    assert item["playback_url"].startswith("/api/video-play/")
    assert item["playback_url"].endswith("%E5%B0%8F%E7%B1%B3%E5%8A%9E%E5%85%ACPro20260212-180739.mp4")
    assert item["download_url"].endswith("?download=1")

    poster = client.get(item["poster_url"])
    assert poster.status_code == 404
    assert poster.get_json() == {"error": "Video poster not available"}

    range_response = client.get(item["playback_url"], headers={"Range": "bytes=0-3"})
    assert range_response.status_code == 206
    assert range_response.data == b"0123"
    assert range_response.headers["Content-Type"].startswith("video/mp4")

    download = client.get(item["download_url"])
    assert download.status_code == 200
    assert "attachment" in download.headers["Content-Disposition"]
