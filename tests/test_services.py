from io import BytesIO

from werkzeug.datastructures import FileStorage

from backend.config import coerce_bool, coerce_int, normalize_access_control_config
from backend.paths import build_path_context
from backend.services.photo_gallery import (
    make_photo_id,
    make_unique_photo_upload_filename,
    photo_meta_from_path,
    resolve_photo_path,
    save_photo_index,
    upload_photos_to_album,
)
from backend.services.static_files import is_real_path_inside
from backend.services.task_queue import TaskManager
from tests.conftest import write_config


def test_photo_upload_filename_sanitizes_and_rejects_unsupported(tmp_path):
    target = tmp_path / "album"
    target.mkdir()
    (target / "my_photo.jpg").write_bytes(b"existing")

    filename = make_unique_photo_upload_filename("../my photo.jpg", str(target))
    assert filename.startswith("my_photo-")
    assert filename.endswith(".jpg")
    assert make_unique_photo_upload_filename("note.txt", str(target)) is None


def test_config_normalize_coerces_access_control_values():
    config = {
        "access_control": {
            "enabled": "yes",
            "session_days": "999",
            "allow_localhost_bypass": "off",
            "allow_remote_generation": "true",
            "session_version": "0",
            "lan_bind_enabled": "no",
        }
    }

    access_config, changed = normalize_access_control_config(config)

    assert access_config["enabled"] is True
    assert access_config["session_days"] == 365
    assert access_config["allow_localhost_bypass"] is False
    assert access_config["allow_remote_generation"] is True
    assert access_config["session_version"] == 1
    assert access_config["lan_bind_enabled"] is False
    assert access_config["session_secret"]
    assert changed is True
    assert coerce_bool("on") is True
    assert coerce_int("bad", 7, 1, 10) == 7


def test_real_path_inside_handles_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    inside = root / "file.txt"
    outside = tmp_path / "outside.txt"

    assert is_real_path_inside(str(inside), str(root)) is True
    assert is_real_path_inside(str(outside), str(root)) is False


def test_photo_id_resolves_through_index_and_album_root(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    photo_path = album_dir / "image.jpg"
    photo_path.write_bytes(b"fake")
    write_config(
        config_file,
        {
            "workspace_folder": str(workspace),
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
    paths = build_path_context({"workspace_folder": str(workspace)})
    meta = photo_meta_from_path({"id": "album1", "path": str(album_dir)}, str(photo_path))
    save_photo_index(paths, {"photos": {meta["id"]: meta}})

    resolved = resolve_photo_path(paths, meta["id"])

    assert make_photo_id("album1", "image.jpg") == meta["id"]
    assert resolved is not None
    assert resolved[1] == str(photo_path.resolve())


def test_invalid_uploaded_photo_is_cleaned_up(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    write_config(
        config_file,
        {
            "workspace_folder": str(workspace),
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
    paths = build_path_context({"workspace_folder": str(workspace)})
    storage = FileStorage(stream=BytesIO(b"not an image"), filename="bad.jpg")

    payload, status_code = upload_photos_to_album(paths, "album1", [storage])

    assert status_code == 400
    assert payload["success"] is False
    assert not any(album_dir.iterdir())


def test_task_manager_enqueue_and_cancel_without_worker(workspace):
    paths = build_path_context({"workspace_folder": str(workspace)})
    task_manager = TaskManager(paths=paths)
    input_path = workspace / "inputs" / "photo.jpg"
    input_path.parent.mkdir()
    input_path.write_bytes(b"fake")

    task = task_manager.enqueue_file(str(input_path), "photo.jpg")
    payload, status_code = task_manager.cancel_task(task["id"])
    tasks, has_active = task_manager.list_tasks()

    assert status_code == 200
    assert payload["success"] is True
    assert tasks[0]["status"] == "cancelled"
    assert has_active is False
