import json

from werkzeug.security import generate_password_hash

from backend.app_factory import create_app
from tests.conftest import make_png_bytes, write_config


def make_access_config(**overrides):
    data = {
        "enabled": False,
        "password_hash": "",
        "session_secret": "test-secret",
        "session_days": 30,
        "allow_localhost_bypass": True,
        "allow_remote_generation": False,
        "session_version": 1,
        "lan_bind_enabled": True,
    }
    data.update(overrides)
    return data


def remote_post(client, path, **kwargs):
    return client.post(
        path,
        base_url="http://192.168.1.2",
        environ_overrides={"REMOTE_ADDR": "192.168.1.50"},
        **kwargs,
    )


def test_owner_only_rejects_remote_when_gate_disabled(client):
    response = remote_post(client, "/api/settings", json={"model_format": "ply"})
    assert response.status_code == 403
    assert response.get_json()["code"] == "OWNER_REQUIRED"


def test_forwarded_headers_do_not_grant_owner(client):
    response = remote_post(
        client,
        "/api/settings",
        json={"model_format": "ply"},
        headers={
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "Forwarded": "for=127.0.0.1",
        },
    )
    assert response.status_code == 403
    assert response.get_json()["code"] == "OWNER_REQUIRED"


def test_remote_generate_requires_explicit_gate_setting(config_file, workspace):
    config = {
        "workspace_folder": str(workspace),
        "access_control": make_access_config(
            enabled=True,
            password_hash=generate_password_hash("password123"),
            allow_remote_generation=False,
        ),
        "photo_gallery_roots": [],
    }
    write_config(config_file, config)
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        login = remote_post(client, "/api/auth/login", json={"password": "password123"})
        assert login.status_code == 200
        response = remote_post(client, "/api/generate")
        assert response.status_code == 403
        assert response.get_json()["code"] == "OWNER_REQUIRED"


def test_remote_photo_upload_gate_disabled_is_owner_only(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    config = {
        "workspace_folder": str(workspace),
        "access_control": make_access_config(enabled=False),
        "photo_gallery_roots": [{"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True}],
    }
    write_config(config_file, config)
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = remote_post(
            client,
            "/api/photo-albums/album1/uploads",
            data={"file": (make_png_bytes(), "remote.png")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 403
        assert response.get_json()["code"] == "OWNER_REQUIRED"


def test_remote_photo_upload_gate_enabled_accepts_unlocked_client(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    config = {
        "workspace_folder": str(workspace),
        "access_control": make_access_config(
            enabled=True,
            password_hash=generate_password_hash("password123"),
        ),
        "photo_gallery_roots": [{"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True}],
    }
    write_config(config_file, config)
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        login = remote_post(client, "/api/auth/login", json={"password": "password123"})
        assert login.status_code == 200
        response = remote_post(
            client,
            "/api/photo-albums/album1/uploads",
            data={"file": (make_png_bytes(), "remote.png")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["uploaded"] == 1
        assert (album_dir / "remote.png").exists()
