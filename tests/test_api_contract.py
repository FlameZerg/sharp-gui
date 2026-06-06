import os


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
