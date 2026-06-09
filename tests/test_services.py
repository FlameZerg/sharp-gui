import os
import zipfile
from io import BytesIO

from werkzeug.datastructures import FileStorage

from backend.config import coerce_bool, coerce_int, normalize_access_control_config
from backend.paths import build_path_context
from backend.services.photo_gallery import (
    MEDIA_TYPE_IMAGE,
    MEDIA_TYPE_VIDEO,
    build_photo_item,
    clear_photo_gallery_cache,
    convert_photos_to_models,
    create_photo_download_zip,
    cleanup_expired_photo_download_zips,
    delete_photo_album,
    ensure_video_poster,
    get_photo_thumbnail_filename,
    get_photo_gallery_cache_stats,
    get_video_poster_filename,
    list_album_photos,
    list_photo_album_responses,
    load_album_index,
    load_photo_index,
    make_photo_id,
    make_unique_photo_upload_filename,
    photo_meta_from_path,
    resolve_media_path,
    resolve_photo_path,
    save_photo_index,
    scan_photo_album,
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


def test_media_scan_lists_images_and_videos_with_type_filter(config_file, workspace, monkeypatch):
    album_dir = workspace / "album"
    album_dir.mkdir()
    image_path = album_dir / "image.jpg"
    video_path = album_dir / "clip.MP4"
    note_path = album_dir / "note.txt"
    image_path.write_bytes(b"fake-image")
    video_path.write_bytes(b"fake-video")
    note_path.write_bytes(b"ignore-me")
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
    monkeypatch.setattr("backend.services.photo_gallery.probe_video_metadata", lambda _path: {})
    paths = build_path_context({"workspace_folder": str(workspace)})

    media_items, status, error = scan_photo_album(paths, {"id": "album1", "path": str(album_dir), "enabled": True})
    payload_all, _ = list_album_photos(paths, "album1", "name_asc", "0", "20", "all")
    payload_photos, _ = list_album_photos(paths, "album1", "name_asc", "0", "20", "photo")
    payload_videos, _ = list_album_photos(paths, "album1", "name_asc", "0", "20", "video")

    assert status == "idle"
    assert error is None
    assert {item["media_type"] for item in media_items} == {MEDIA_TYPE_IMAGE, MEDIA_TYPE_VIDEO}
    assert payload_all["total"] == 2
    assert payload_all["media_counts"] == {"all": 2, "image": 1, "photo": 1, "video": 1}
    assert payload_photos["total"] == 1
    assert payload_photos["items"][0]["media_type"] == MEDIA_TYPE_IMAGE
    assert payload_videos["total"] == 1
    assert payload_videos["items"][0]["media_type"] == MEDIA_TYPE_VIDEO
    assert payload_videos["items"][0]["playback_url"].startswith("/api/video-play/")
    assert payload_videos["items"][0]["playback_url"].endswith("/clip.MP4")
    assert "note.txt" not in {item["name"] for item in media_items}


def test_legacy_photo_index_entries_are_migrated_to_image_type(workspace):
    paths = build_path_context({"workspace_folder": str(workspace)})
    save_photo_index(paths, {"photos": {"legacy": {"id": "legacy", "name": "old.jpg"}}})

    index_data = load_photo_index(paths)

    assert index_data["photos"]["legacy"]["media_type"] == MEDIA_TYPE_IMAGE


def test_video_path_resolver_rejects_album_root_escape(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    outside_path = workspace / "outside.mp4"
    outside_path.write_bytes(b"outside")
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
    media_id = make_photo_id("album1", "../outside.mp4")
    save_photo_index(paths, {
        "photos": {
            media_id: {
                "id": media_id,
                "album_id": "album1",
                "relative_path": "../outside.mp4",
                "name": "outside.mp4",
                "media_type": MEDIA_TYPE_VIDEO,
                "mtime": outside_path.stat().st_mtime,
                "size": outside_path.stat().st_size,
            },
        },
    })

    assert resolve_media_path(paths, media_id, expected_type=MEDIA_TYPE_VIDEO) is None


def test_video_metadata_and_poster_degrade_without_optional_tools(config_file, workspace, monkeypatch):
    album_dir = workspace / "album"
    album_dir.mkdir()
    video_path = album_dir / "clip.webm"
    video_path.write_bytes(b"fake-video")
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
    monkeypatch.setattr("backend.services.photo_gallery.get_optional_command", lambda _name: None)
    paths = build_path_context({"workspace_folder": str(workspace)})
    meta = photo_meta_from_path({"id": "album1", "path": str(album_dir)}, str(video_path))
    save_photo_index(paths, {"photos": {meta["id"]: meta}})

    item = build_photo_item(paths, meta)

    assert item["media_type"] == MEDIA_TYPE_VIDEO
    assert item["duration"] is None
    assert item["poster_url"].startswith("/api/video-poster/")
    assert ensure_video_poster(paths, meta["id"]) is None


def test_cached_video_poster_is_reused_without_ffmpeg(config_file, workspace, monkeypatch):
    album_dir = workspace / "album"
    album_dir.mkdir()
    video_path = album_dir / "clip.mp4"
    video_path.write_bytes(b"fake-video")
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
    monkeypatch.setattr("backend.services.photo_gallery.get_optional_command", lambda _name: None)
    paths = build_path_context({"workspace_folder": str(workspace)})
    meta = photo_meta_from_path({"id": "album1", "path": str(album_dir)}, str(video_path))
    save_photo_index(paths, {"photos": {meta["id"]: meta}})
    os.makedirs(paths.video_poster_folder, exist_ok=True)
    poster_path = os.path.join(paths.video_poster_folder, get_video_poster_filename(meta["id"], meta))
    with open(poster_path, "wb") as f:
        f.write(b"cached-poster")

    assert ensure_video_poster(paths, meta["id"]) == poster_path


def test_delete_photo_album_cleans_album_media_cache(config_file, workspace):
    album_dir = workspace / "album"
    other_album_dir = workspace / "other-album"
    album_dir.mkdir()
    other_album_dir.mkdir()
    image_path = album_dir / "image.jpg"
    video_path = album_dir / "clip.mp4"
    other_image_path = other_album_dir / "other.jpg"
    image_path.write_bytes(b"fake-image")
    video_path.write_bytes(b"fake-video")
    other_image_path.write_bytes(b"other-image")
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
            "photo_gallery_roots": [
                {"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True},
                {"id": "album2", "name": "Other", "path": str(other_album_dir), "enabled": True},
            ],
        },
    )
    paths = build_path_context({"workspace_folder": str(workspace)})
    image_meta = photo_meta_from_path({"id": "album1", "path": str(album_dir)}, str(image_path))
    video_meta = photo_meta_from_path({"id": "album1", "path": str(album_dir)}, str(video_path))
    other_meta = photo_meta_from_path({"id": "album2", "path": str(other_album_dir)}, str(other_image_path))
    save_photo_index(paths, {"photos": {
        image_meta["id"]: image_meta,
        video_meta["id"]: video_meta,
        other_meta["id"]: other_meta,
    }})
    os.makedirs(paths.photo_thumbnail_folder, exist_ok=True)
    os.makedirs(paths.video_poster_folder, exist_ok=True)
    image_thumb_path = os.path.join(paths.photo_thumbnail_folder, get_photo_thumbnail_filename(image_meta["id"], image_meta))
    video_poster_path = os.path.join(paths.video_poster_folder, get_video_poster_filename(video_meta["id"], video_meta))
    other_thumb_path = os.path.join(paths.photo_thumbnail_folder, get_photo_thumbnail_filename(other_meta["id"], other_meta))
    stale_variant_path = os.path.join(paths.photo_thumbnail_folder, f"{image_meta['id']}-old-version-480.jpg")
    for path in (image_thumb_path, video_poster_path, other_thumb_path, stale_variant_path):
        with open(path, "wb") as f:
            f.write(b"cache")

    payload, status_code = delete_photo_album(paths, "album1")

    assert status_code == 200
    assert payload == {"success": True}
    index_data = load_photo_index(paths)
    assert image_meta["id"] not in index_data["photos"]
    assert video_meta["id"] not in index_data["photos"]
    assert other_meta["id"] in index_data["photos"]
    assert not os.path.exists(image_thumb_path)
    assert not os.path.exists(video_poster_path)
    assert not os.path.exists(stale_variant_path)
    assert os.path.exists(other_thumb_path)


def test_media_download_zip_can_include_videos(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    video_path = album_dir / "clip.mp4"
    video_path.write_bytes(b"fake-video")
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
    meta = photo_meta_from_path({"id": "album1", "path": str(album_dir)}, str(video_path))
    save_photo_index(paths, {"photos": {meta["id"]: meta}})

    result, error_payload, status_code = create_photo_download_zip(paths, [meta["id"]])

    assert status_code == 200
    assert error_payload is None
    assert result["added_count"] == 1
    with zipfile.ZipFile(result["zip_path"]) as archive:
        assert archive.namelist() == ["clip.mp4"]


def test_cleanup_expired_photo_download_zips_only_removes_old_temp_archives(workspace):
    paths = build_path_context({"workspace_folder": str(workspace)})
    os.makedirs(paths.photo_gallery_cache_folder, exist_ok=True)
    old_zip = os.path.join(paths.photo_gallery_cache_folder, "photo-gallery-old.zip")
    fresh_zip = os.path.join(paths.photo_gallery_cache_folder, "photo-gallery-fresh.zip")
    other_zip = os.path.join(paths.photo_gallery_cache_folder, "other.zip")
    for path in (old_zip, fresh_zip, other_zip):
        with open(path, "wb") as f:
            f.write(b"zip")
    old_mtime = 1_700_000_000
    os.utime(old_zip, (old_mtime, old_mtime))

    cleanup_expired_photo_download_zips(paths, max_age_seconds=1)

    assert not os.path.exists(old_zip)
    assert os.path.exists(fresh_zip)
    assert os.path.exists(other_zip)


def test_video_ids_are_not_accepted_for_photo_conversion(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    video_path = album_dir / "clip.mp4"
    video_path.write_bytes(b"fake-video")
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
    meta = photo_meta_from_path({"id": "album1", "path": str(album_dir)}, str(video_path))
    save_photo_index(paths, {"photos": {meta["id"]: meta}})
    task_manager = TaskManager(paths=paths)

    payload = convert_photos_to_models(paths, task_manager, [meta["id"]])

    assert payload["success"] is False
    assert payload["failed"] == [{"id": meta["id"], "error": "Only photos can be converted to 3D"}]


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


def test_album_list_and_pagination_use_cache_without_rescan(config_file, workspace, monkeypatch):
    album_dir = workspace / "album"
    album_dir.mkdir()
    photo_path = album_dir / "image.jpg"
    photo_path.write_bytes(b"fake-image")
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
    scan_photo_album(paths, {"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True})

    def fail_scan(*_args, **_kwargs):
        raise AssertionError("ordinary reads must not rescan albums")

    monkeypatch.setattr("backend.services.photo_gallery.scan_photo_album", fail_scan)
    payload, status_code = list_album_photos(paths, "album1", "mtime_desc", "0", "20", "all")

    assert status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "image.jpg"
    assert payload["scan_status"] == "idle"


def test_album_pagination_snapshot_is_stable_during_rescan(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    for index in range(3):
        (album_dir / f"image-{index}.jpg").write_bytes(f"fake-{index}".encode())
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
    scan_photo_album(paths, {"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True})

    first_page, _ = list_album_photos(paths, "album1", "name_asc", "0", "2", "all")
    snapshot = first_page["snapshot"]
    (album_dir / "image-9.jpg").write_bytes(b"new")
    scan_photo_album(paths, {"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True})

    stable_second_page, _ = list_album_photos(paths, "album1", "name_asc", "2", "2", "all", snapshot)
    fresh_first_page, _ = list_album_photos(paths, "album1", "name_asc", "0", "10", "all")

    assert [item["name"] for item in stable_second_page["items"]] == ["image-2.jpg"]
    assert "image-9.jpg" in [item["name"] for item in fresh_first_page["items"]]


def test_large_warm_album_browsing_does_not_walk_directory(config_file, workspace, monkeypatch):
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
    photos = {}
    for index in range(1000):
        relative_path = f"image-{index:04d}.jpg"
        media_id = make_photo_id("album1", relative_path)
        photos[media_id] = {
            "id": media_id,
            "album_id": "album1",
            "relative_path": relative_path,
            "name": relative_path,
            "media_type": MEDIA_TYPE_IMAGE,
            "mtime": float(index),
            "ctime": float(index),
            "size": index + 1,
            "width": None,
            "height": None,
        }
    save_photo_index(paths, {"photos": photos})

    def fail_walk(_path):
        raise AssertionError("warm index browsing must not call os.walk")

    monkeypatch.setattr("backend.services.photo_gallery.os.walk", fail_walk)

    first_page, _ = list_album_photos(paths, "album1", "mtime_desc", "0", "60", "all")
    sorted_page, _ = list_album_photos(paths, "album1", "size_asc", "120", "60", "all")
    filtered_page, _ = list_album_photos(paths, "album1", "name_asc", "0", "60", "photo")

    assert first_page["total"] == 1000
    assert first_page["items"][0]["name"] == "image-0999.jpg"
    assert sorted_page["items"][0]["name"] == "image-0120.jpg"
    assert filtered_page["media_counts"]["image"] == 1000


def test_first_scan_reuses_legacy_index_metadata_without_ffprobe(config_file, workspace, monkeypatch):
    album_dir = workspace / "album"
    album_dir.mkdir()
    video_path = album_dir / "clip.mp4"
    video_path.write_bytes(b"fake-video")
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
    stat = video_path.stat()
    legacy_id = "legacy-video-id"
    save_photo_index(paths, {
        "photos": {
            legacy_id: {
                "id": legacy_id,
                "album_id": "album1",
                "relative_path": "clip.mp4",
                "name": "clip.mp4",
                "media_type": MEDIA_TYPE_VIDEO,
                "mtime": stat.st_mtime,
                "ctime": stat.st_ctime,
                "size": stat.st_size,
                "width": 1920,
                "height": 1080,
                "duration": 12.5,
                "video_codec": "h264",
                "audio_codec": "aac",
                "bitrate": 6000000,
            },
        },
    })
    os.remove(getattr(paths, "photo_album_index_folder") + "/album1.json")

    def fail_probe(_path):
        raise AssertionError("unchanged legacy video metadata should avoid ffprobe")

    monkeypatch.setattr("backend.services.photo_gallery.probe_video_metadata", fail_probe)
    media_items, status, error = scan_photo_album(paths, {"id": "album1", "name": "Album", "path": str(album_dir), "enabled": True})
    index_data = load_album_index(paths, "album1")

    assert status == "idle"
    assert error is None
    assert len(media_items) == 1
    assert media_items[0]["id"] == make_photo_id("album1", "clip.mp4")
    assert media_items[0]["duration"] == 12.5
    assert media_items[0]["width"] == 1920
    assert index_data["media"][media_items[0]["id"]]["video_codec"] == "h264"
    assert not os.path.exists(paths.photo_index_file)
    assert os.path.exists(f"{paths.photo_index_file}.bak")


def test_scan_after_legacy_archive_does_not_rebuild_global_index(config_file, workspace, monkeypatch):
    album_one_dir = workspace / "album-one"
    album_two_dir = workspace / "album-two"
    album_one_dir.mkdir()
    album_two_dir.mkdir()
    album_one_photo = album_one_dir / "image.jpg"
    album_two_photo = album_two_dir / "fresh.jpg"
    album_one_photo.write_bytes(b"old")
    album_two_photo.write_bytes(b"new")
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
            "photo_gallery_roots": [
                {"id": "album1", "name": "Album One", "path": str(album_one_dir), "enabled": True},
                {"id": "album2", "name": "Album Two", "path": str(album_two_dir), "enabled": True},
            ],
        },
    )
    paths = build_path_context({"workspace_folder": str(workspace)})
    album_one_meta = photo_meta_from_path({"id": "album1", "path": str(album_one_dir)}, str(album_one_photo))
    save_photo_index(paths, {"photos": {album_one_meta["id"]: album_one_meta}})
    os.replace(paths.photo_index_file, f"{paths.photo_index_file}.bak")

    def fail_load_index(_paths):
        raise AssertionError("scan after legacy archive must not rebuild a global index")

    monkeypatch.setattr("backend.services.photo_gallery.load_photo_index", fail_load_index)
    media_items, status, error = scan_photo_album(
        paths,
        {"id": "album2", "name": "Album Two", "path": str(album_two_dir), "enabled": True},
    )

    assert status == "idle"
    assert error is None
    assert [item["id"] for item in media_items] == [make_photo_id("album2", "fresh.jpg")]
    assert os.path.exists(f"{paths.photo_index_file}.bak")
    assert not os.path.exists(paths.photo_index_file)


def test_album_list_migrates_once_and_avoids_legacy_rebuild(config_file, workspace, monkeypatch):
    album_dir = workspace / "album"
    album_dir.mkdir()
    photo_path = album_dir / "image.jpg"
    photo_path.write_bytes(b"fake-image")
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

    # 模拟升级前的 workspace：仅保留旧全局 index.json，移除镜像出的每相册索引与 catalog
    stat = photo_path.stat()
    save_photo_index(paths, {
        "photos": {
            "legacy-image-id": {
                "id": "legacy-image-id",
                "album_id": "album1",
                "relative_path": "image.jpg",
                "name": "image.jpg",
                "media_type": MEDIA_TYPE_IMAGE,
                "mtime": stat.st_mtime,
                "ctime": stat.st_ctime,
                "size": stat.st_size,
                "width": 800,
                "height": 600,
            },
        },
    })
    os.remove(f"{paths.photo_album_index_folder}/album1.json")
    if os.path.exists(paths.photo_catalog_file):
        os.remove(paths.photo_catalog_file)

    # 首次列表触发一次性迁移：折算 catalog 并归档旧索引
    albums = list_photo_album_responses(paths)
    assert len(albums) == 1
    assert albums[0]["media_count"] == 1
    assert albums[0]["scan_status"] == "stale"
    assert not os.path.exists(paths.photo_index_file)
    assert os.path.exists(f"{paths.photo_index_file}.bak")

    # 迁移后再次请求列表不得回退去重建式读取旧索引（避免 O(N^2) 读放大）
    def fail_load_index(_paths):
        raise AssertionError("list must not rebuild from legacy index after migration")

    monkeypatch.setattr("backend.services.photo_gallery.load_photo_index", fail_load_index)
    albums_again = list_photo_album_responses(paths)
    assert len(albums_again) == 1
    assert albums_again[0]["scan_status"] == "stale"


def test_photo_gallery_cache_stats_and_clear_do_not_delete_originals(config_file, workspace):
    album_dir = workspace / "album"
    album_dir.mkdir()
    photo_path = album_dir / "image.jpg"
    photo_path.write_bytes(b"original")
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
    os.makedirs(paths.photo_thumbnail_folder, exist_ok=True)
    thumb_path = os.path.join(paths.photo_thumbnail_folder, get_photo_thumbnail_filename(meta["id"], meta))
    with open(thumb_path, "wb") as f:
        f.write(b"thumb")

    stats = get_photo_gallery_cache_stats(paths)
    payload, status_code = clear_photo_gallery_cache(paths, "generated")

    assert stats["total"]["files"] >= 2
    assert status_code == 200
    assert payload["success"] is True
    assert payload["removed"]["files"] >= 2
    assert photo_path.exists()
    assert list(album_dir.iterdir()) == [photo_path]


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
