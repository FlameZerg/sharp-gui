from backend.services.static_files import get_relative_files_path


def test_model_file_under_allowed_root_is_served(client, app):
    paths = app.config["PATH_CONTEXT"]
    model_path = paths.output_folder + "/model.ply"
    with open(model_path, "wb") as f:
        f.write(b"ply-data")

    response = client.get(f"/files/{get_relative_files_path(model_path, paths)}")
    assert response.status_code == 200
    assert response.data == b"ply-data"


def test_sensitive_files_are_not_served(client):
    response = client.get("/files/config.json")
    assert response.status_code == 404


def test_path_traversal_is_not_served(client):
    response = client.get("/files/%2e%2e/config.json")
    assert response.status_code == 404
