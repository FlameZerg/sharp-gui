import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
import zipfile
from shutil import which
from urllib.parse import quote

from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

from backend.config import load_config, save_config
from backend.security.access_control import create_video_play_token
from backend.services.static_files import is_real_path_inside, to_url_path

PHOTO_THUMBNAIL_WIDTH = 480
VIDEO_POSTER_WIDTH = 640
PHOTO_THUMBNAIL_CACHE_SECONDS = 86400
PHOTO_DEFAULT_PAGE_SIZE = 60
PHOTO_MAX_PAGE_SIZE = 120
PHOTO_MAX_CONVERSION_BATCH = 100
PHOTO_MAX_DOWNLOAD_BATCH = 200
PHOTO_MAX_UPLOAD_BATCH = 100
PHOTO_DOWNLOAD_ZIP_TTL_SECONDS = 24 * 60 * 60
MEDIA_TYPE_ALL = "all"
MEDIA_TYPE_IMAGE = "image"
MEDIA_TYPE_VIDEO = "video"

PHOTO_UPLOAD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm"}
VIDEO_MIME_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}

photo_index_lock = threading.Lock()


def build_video_playback_url(video_id, filename):
    safe_filename = quote(filename or f"{video_id}.mp4", safe="")
    return f"/api/video-play/{video_id}/{create_video_play_token(video_id)}/{safe_filename}"


def make_photo_album_id(path):
    """根据目录真实路径生成稳定相册 ID。"""
    normalized = os.path.normcase(os.path.realpath(os.path.abspath(os.path.expanduser(path))))
    return hashlib.sha1(normalized.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def normalize_photo_album_roots(config_data=None):
    """读取并规范化照片图库目录配置。"""
    source_config = config_data or load_config()
    raw_roots = source_config.get("photo_gallery_roots", [])
    if not isinstance(raw_roots, list):
        raw_roots = []

    albums = []
    seen_ids = set()
    for raw in raw_roots:
        if isinstance(raw, str):
            raw = {"path": raw}
        if not isinstance(raw, dict):
            continue

        path = raw.get("path")
        if not isinstance(path, str) or not path.strip():
            continue

        absolute_path = os.path.abspath(os.path.expanduser(path.strip()))
        album_id = raw.get("id")
        if not isinstance(album_id, str) or not album_id.strip():
            album_id = make_photo_album_id(absolute_path)
        album_id = "".join(ch for ch in album_id if ch.isalnum() or ch in ("-", "_"))[:64]
        if not album_id or album_id in seen_ids:
            album_id = make_photo_album_id(f"{absolute_path}-{len(seen_ids)}")
        seen_ids.add(album_id)

        default_name = os.path.basename(os.path.normpath(absolute_path)) or absolute_path
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            name = default_name

        albums.append({
            "id": album_id,
            "name": name.strip(),
            "path": absolute_path,
            "recursive": bool(raw.get("recursive", True)),
            "enabled": raw.get("enabled", True) is not False,
        })

    return albums


def find_photo_album(album_id):
    """根据相册 ID 查找配置。"""
    for album in normalize_photo_album_roots():
        if album["id"] == album_id:
            return album
    return None


def load_photo_index(paths):
    """读取照片图库轻量索引。"""
    if not os.path.exists(paths.photo_index_file):
        return {"photos": {}}

    try:
        with open(paths.photo_index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("photos"), dict):
            return migrate_index_data(data)
    except Exception as exc:
        print(f"⚠️ Failed to load photo index: {exc}")

    return {"photos": {}}


def save_photo_index(paths, index_data):
    """保存照片图库轻量索引。"""
    os.makedirs(paths.photo_gallery_cache_folder, exist_ok=True)
    with open(paths.photo_index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)


def make_photo_id(album_id, relative_path):
    """根据相册与相对路径生成不暴露路径的照片 ID。"""
    normalized_relative = to_url_path(relative_path)
    payload = f"{album_id}\0{normalized_relative}"
    return hashlib.sha256(payload.encode("utf-8", "surrogatepass")).hexdigest()[:32]


def get_file_extension(filename):
    return os.path.splitext(filename)[1].lower()


def is_supported_photo(filename):
    """判断文件是否是支持的照片格式。"""
    return get_file_extension(filename) in ALLOWED_IMAGE_EXTENSIONS


def is_supported_video(filename):
    """判断文件是否是支持的视频格式。"""
    return get_file_extension(filename) in ALLOWED_VIDEO_EXTENSIONS


def get_media_type(filename):
    if is_supported_photo(filename):
        return MEDIA_TYPE_IMAGE
    if is_supported_video(filename):
        return MEDIA_TYPE_VIDEO
    return None


def normalize_media_type(value):
    normalized = str(value or "").strip().lower()
    if normalized in {MEDIA_TYPE_IMAGE, "photo", "photos"}:
        return MEDIA_TYPE_IMAGE
    if normalized in {MEDIA_TYPE_VIDEO, "videos"}:
        return MEDIA_TYPE_VIDEO
    return MEDIA_TYPE_ALL


def migrate_index_data(index_data):
    """兼容旧照片索引，为缺失字段补默认媒体类型。"""
    photos = index_data.setdefault("photos", {})
    for meta in photos.values():
        if not isinstance(meta, dict):
            continue
        if "media_type" not in meta:
            meta["media_type"] = MEDIA_TYPE_IMAGE
        if meta.get("media_type") == "photo":
            meta["media_type"] = MEDIA_TYPE_IMAGE
    return index_data


def is_same_source_version(meta, stat):
    return (
        bool(meta)
        and meta.get("mtime") == stat.st_mtime
        and meta.get("size") == stat.st_size
    )


def get_video_mime_type(filename):
    return VIDEO_MIME_TYPES.get(get_file_extension(filename), "video/mp4")


def get_optional_command(name):
    return which(name)


def parse_float(value):
    try:
        parsed = float(value)
        if parsed == parsed and parsed >= 0:
            return parsed
    except (TypeError, ValueError):
        pass
    return None


def parse_int(value):
    try:
        parsed = int(float(value))
        if parsed >= 0:
            return parsed
    except (TypeError, ValueError):
        pass
    return None


def probe_video_metadata(full_path):
    """使用可选 ffprobe 读取视频元数据。"""
    ffprobe = get_optional_command("ffprobe")
    if not ffprobe:
        return {}

    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                full_path,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:
        print(f"⚠️ Video metadata probe failed for {full_path}: {exc}")
        return {}

    if result.returncode != 0:
        return {}

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}

    streams = payload.get("streams") if isinstance(payload, dict) else []
    if not isinstance(streams, list):
        streams = []

    video_stream = next(
        (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"),
        {},
    )
    audio_stream = next(
        (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"),
        {},
    )
    format_data = payload.get("format") if isinstance(payload.get("format"), dict) else {}

    duration = parse_float(video_stream.get("duration")) or parse_float(format_data.get("duration"))
    width = parse_int(video_stream.get("width"))
    height = parse_int(video_stream.get("height"))
    bitrate = parse_int(format_data.get("bit_rate")) or parse_int(video_stream.get("bit_rate"))

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
        "bitrate": bitrate,
    }


def apply_cached_video_metadata(meta, existing_meta, stat):
    if not is_same_source_version(existing_meta, stat):
        return meta

    for key in ("duration", "width", "height", "video_codec", "audio_codec", "bitrate"):
        if existing_meta.get(key) is not None:
            meta[key] = existing_meta.get(key)
    return meta


def update_index_meta(paths, meta):
    with photo_index_lock:
        index_data = load_photo_index(paths)
        index_data.setdefault("photos", {})[meta["id"]] = meta
        save_photo_index(paths, index_data)


def photo_meta_from_path(album, full_path, existing_meta=None):
    """根据文件路径构建媒体索引元数据。"""
    root_path = os.path.realpath(album["path"])
    real_path = os.path.realpath(full_path)
    if not is_real_path_inside(real_path, root_path):
        return None

    try:
        stat = os.stat(real_path)
    except OSError:
        return None

    relative_path = to_url_path(os.path.relpath(real_path, root_path))
    photo_id = make_photo_id(album["id"], relative_path)
    media_type = get_media_type(real_path)
    if not media_type:
        return None

    width = None
    height = None
    if is_same_source_version(existing_meta, stat):
        width = existing_meta.get("width")
        height = existing_meta.get("height")

    meta = {
        "id": photo_id,
        "album_id": album["id"],
        "relative_path": relative_path,
        "name": os.path.basename(real_path),
        "media_type": media_type,
        "mime_type": get_video_mime_type(real_path) if media_type == MEDIA_TYPE_VIDEO else None,
        "mtime": stat.st_mtime,
        "ctime": stat.st_ctime,
        "size": stat.st_size,
        "width": width,
        "height": height,
    }

    if media_type == MEDIA_TYPE_VIDEO:
        meta.update({
            "duration": None,
            "video_codec": None,
            "audio_codec": None,
            "bitrate": None,
        })
        apply_cached_video_metadata(meta, existing_meta, stat)

    return meta


def iter_album_photo_paths(album):
    """遍历相册中的媒体路径。"""
    root_path = album["path"]
    if not os.path.isdir(root_path):
        return

    if album.get("recursive", True):
        for current_root, dirnames, filenames in os.walk(root_path):
            dirnames[:] = [
                dirname for dirname in dirnames
                if dirname not in {".photo-gallery-cache", ".thumbnails", "__pycache__"}
            ]
            for filename in filenames:
                if get_media_type(filename):
                    yield os.path.join(current_root, filename)
    else:
        for filename in os.listdir(root_path):
            full_path = os.path.join(root_path, filename)
            if os.path.isfile(full_path) and get_media_type(filename):
                yield full_path


def scan_photo_album(paths, album):
    """扫描相册并刷新轻量索引。"""
    if not album.get("enabled", True):
        return [], "error", "Album disabled"

    if not os.path.isdir(album["path"]):
        return [], "error", "Album path is not available"

    with photo_index_lock:
        index_data = load_photo_index(paths)
        photos = index_data.setdefault("photos", {})
        previous_by_key = {
            (meta.get("album_id"), meta.get("relative_path")): meta
            for meta in photos.values()
            if isinstance(meta, dict)
        }

        album_photo_ids = set()
        album_photos = []
        try:
            for full_path in iter_album_photo_paths(album):
                root_path = os.path.realpath(album["path"])
                relative_path = to_url_path(os.path.relpath(os.path.realpath(full_path), root_path))
                existing = previous_by_key.get((album["id"], relative_path))
                meta = photo_meta_from_path(album, full_path, existing_meta=existing)
                if not meta:
                    continue
                photos[meta["id"]] = meta
                album_photo_ids.add(meta["id"])
                album_photos.append(meta)
        except Exception as exc:
            save_photo_index(paths, index_data)
            return [], "error", str(exc)

        stale_ids = [
            photo_id for photo_id, meta in photos.items()
            if meta.get("album_id") == album["id"] and photo_id not in album_photo_ids
        ]
        for photo_id in stale_ids:
            photos.pop(photo_id, None)

        save_photo_index(paths, index_data)

    album_photos.sort(key=lambda item: item.get("mtime", 0), reverse=True)
    return album_photos, "idle", None


def get_photo_dimensions(full_path):
    """读取照片尺寸。"""
    try:
        with Image.open(full_path) as img:
            return img.size
    except Exception:
        return None, None


def get_video_metadata_for_response(paths, meta):
    if meta.get("duration") is not None and meta.get("width") and meta.get("height"):
        return meta

    resolved = resolve_media_path(
        paths,
        meta["id"],
        expected_type=MEDIA_TYPE_VIDEO,
        allow_stale=True,
    )
    if not resolved:
        return meta

    _, full_path, current_meta = resolved
    probed = probe_video_metadata(full_path)
    if not probed:
        return meta

    updated = False
    for key in ("duration", "width", "height", "video_codec", "audio_codec", "bitrate"):
        if probed.get(key) is not None and current_meta.get(key) != probed.get(key):
            current_meta[key] = probed.get(key)
            updated = True

    if updated:
        update_index_meta(paths, current_meta)
        return current_meta

    return meta


def get_video_poster_filename(video_id, meta):
    """生成与源视频版本绑定的封面文件名。"""
    version = f"{int(float(meta.get('mtime', 0)) * 1000)}-{int(meta.get('size', 0))}"
    return f"{video_id}-{version}-{VIDEO_POSTER_WIDTH}.jpg"


def ensure_video_poster(paths, video_id):
    """确保视频封面存在；ffmpeg 不可用或抽帧失败时安全返回 None。"""
    resolved = resolve_media_path(
        paths,
        video_id,
        expected_type=MEDIA_TYPE_VIDEO,
    )
    if not resolved:
        return None

    _, full_path, meta = resolved
    poster_filename = get_video_poster_filename(video_id, meta)
    poster_path = os.path.join(paths.video_poster_folder, poster_filename)
    if os.path.exists(poster_path):
        return poster_path

    ffmpeg = get_optional_command("ffmpeg")
    if not ffmpeg:
        return None

    os.makedirs(paths.video_poster_folder, exist_ok=True)
    temp_path = f"{poster_path}.tmp-{uuid.uuid4().hex[:8]}.jpg"
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                "0.5",
                "-i",
                full_path,
                "-frames:v",
                "1",
                "-vf",
                f"scale={VIDEO_POSTER_WIDTH}:-2",
                "-q:v",
                "4",
                "-y",
                temp_path,
            ],
            check=False,
            capture_output=True,
            timeout=12,
        )
        if result.returncode != 0 or not os.path.exists(temp_path):
            return None
        os.replace(temp_path, poster_path)
        return poster_path
    except Exception as exc:
        print(f"⚠️ Video poster generation failed for {video_id}: {exc}")
        return None
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


def resolve_media_path(paths, media_id, expected_type=None, allow_stale=False):
    """根据媒体 ID 解析真实路径，并验证仍在配置目录内。"""
    with photo_index_lock:
        index_data = load_photo_index(paths)
        meta = index_data.get("photos", {}).get(media_id)

    if not isinstance(meta, dict):
        return None
    media_type = meta.get("media_type") or MEDIA_TYPE_IMAGE
    if expected_type and media_type != expected_type:
        return None

    album = find_photo_album(meta.get("album_id"))
    if not album:
        return None

    root_path = os.path.realpath(album["path"])
    relative_path = str(meta.get("relative_path", "")).replace("/", os.sep)
    full_path = os.path.realpath(os.path.join(root_path, relative_path))
    if not is_real_path_inside(full_path, root_path) or not os.path.isfile(full_path):
        return None

    try:
        stat = os.stat(full_path)
    except OSError:
        return None

    current_meta = dict(meta)
    current_meta["mtime"] = stat.st_mtime
    current_meta["ctime"] = stat.st_ctime
    current_meta["size"] = stat.st_size
    current_meta["name"] = os.path.basename(full_path)
    current_meta["media_type"] = media_type

    if not allow_stale and (
        meta.get("mtime") != stat.st_mtime or meta.get("size") != stat.st_size
    ):
        current_meta["width"] = None
        current_meta["height"] = None
        if media_type == MEDIA_TYPE_VIDEO:
            current_meta["duration"] = None
            current_meta["video_codec"] = None
            current_meta["audio_codec"] = None
            current_meta["bitrate"] = None
        with photo_index_lock:
            index_data = load_photo_index(paths)
            index_data.setdefault("photos", {})[media_id] = current_meta
            save_photo_index(paths, index_data)

    return album, full_path, current_meta


def resolve_photo_path(paths, photo_id, allow_stale=False):
    """根据照片 ID 解析真实路径，并验证仍在配置目录内。"""
    return resolve_media_path(
        paths,
        photo_id,
        expected_type=MEDIA_TYPE_IMAGE,
        allow_stale=allow_stale,
    )


def build_photo_item(paths, meta):
    """构建媒体条目响应。"""
    media_type = meta.get("media_type") or MEDIA_TYPE_IMAGE
    width = meta.get("width")
    height = meta.get("height")
    if media_type == MEDIA_TYPE_IMAGE and (not width or not height):
        resolved = resolve_photo_path(paths, meta["id"], allow_stale=True)
        if resolved:
            _, full_path, current_meta = resolved
            width, height = get_photo_dimensions(full_path)
            if width and height:
                current_meta["width"] = width
                current_meta["height"] = height
                with photo_index_lock:
                    index_data = load_photo_index(paths)
                    index_data.setdefault("photos", {})[meta["id"]] = current_meta
                    save_photo_index(paths, index_data)
                meta = current_meta
    elif media_type == MEDIA_TYPE_VIDEO:
        meta = get_video_metadata_for_response(paths, meta)
        width = meta.get("width")
        height = meta.get("height")

    updated_at = None
    if meta.get("mtime"):
        updated_at = datetime.datetime.fromtimestamp(
            meta["mtime"],
            tz=datetime.timezone.utc,
        ).isoformat()
    created_at = None
    if meta.get("ctime"):
        created_at = datetime.datetime.fromtimestamp(
            meta["ctime"],
            tz=datetime.timezone.utc,
        ).isoformat()

    item = {
        "id": meta["id"],
        "album_id": meta["album_id"],
        "name": meta.get("name") or meta["id"],
        "media_type": media_type,
        "width": width,
        "height": height,
        "size": meta.get("size"),
        "created_at": created_at,
        "updated_at": updated_at,
    }

    if media_type == MEDIA_TYPE_VIDEO:
        item.update({
            "thumb_url": f"/api/video-poster/{meta['id']}",
            "poster_url": f"/api/video-poster/{meta['id']}",
            "preview_url": f"/api/video-original/{meta['id']}",
            "playback_url": build_video_playback_url(meta["id"], meta.get("name")),
            "download_url": f"/api/video-original/{meta['id']}?download=1",
            "duration": meta.get("duration"),
            "mime_type": meta.get("mime_type") or get_video_mime_type(meta.get("name", "")),
            "video_codec": meta.get("video_codec"),
            "audio_codec": meta.get("audio_codec"),
            "bitrate": meta.get("bitrate"),
        })
    else:
        item.update({
            "thumb_url": f"/api/photo-thumbnail/{meta['id']}",
            "full_url": f"/api/photo-original/{meta['id']}",
            "preview_url": f"/api/photo-original/{meta['id']}",
            "download_url": f"/api/photo-original/{meta['id']}?download=1",
        })

    return item


def get_photo_thumbnail_filename(photo_id, meta):
    """生成与源文件版本绑定的缩略图文件名。"""
    version = f"{int(float(meta.get('mtime', 0)) * 1000)}-{int(meta.get('size', 0))}"
    return f"{photo_id}-{version}-{PHOTO_THUMBNAIL_WIDTH}.jpg"


def ensure_photo_thumbnail(paths, photo_id):
    """确保照片缩略图存在。"""
    resolved = resolve_photo_path(paths, photo_id)
    if not resolved:
        return None

    _, full_path, meta = resolved
    thumb_filename = get_photo_thumbnail_filename(photo_id, meta)
    thumb_path = os.path.join(paths.photo_thumbnail_folder, thumb_filename)
    if os.path.exists(thumb_path):
        return thumb_path

    try:
        os.makedirs(paths.photo_thumbnail_folder, exist_ok=True)
        with Image.open(full_path) as img:
            img = ImageOps.exif_transpose(img)
            meta["width"], meta["height"] = img.size
            img.thumbnail((PHOTO_THUMBNAIL_WIDTH, PHOTO_THUMBNAIL_WIDTH * 3), Image.LANCZOS)
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.getchannel("A"))
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            img.save(thumb_path, "JPEG", quality=82, optimize=True)

        with photo_index_lock:
            index_data = load_photo_index(paths)
            index_data.setdefault("photos", {})[photo_id] = meta
            save_photo_index(paths, index_data)
        return thumb_path
    except Exception as exc:
        print(f"⚠️ Photo thumbnail generation failed for {photo_id}: {exc}")
        return None


def build_photo_album_response(paths, album):
    """构建相册响应数据。"""
    media_items, scan_status, error = scan_photo_album(paths, album)
    cover = media_items[0] if media_items else None
    image_count = sum(1 for item in media_items if item.get("media_type") == MEDIA_TYPE_IMAGE)
    video_count = sum(1 for item in media_items if item.get("media_type") == MEDIA_TYPE_VIDEO)
    updated_at = None
    if media_items:
        updated_at = datetime.datetime.fromtimestamp(
            max(item.get("mtime", 0) for item in media_items),
            tz=datetime.timezone.utc,
        ).isoformat()
    cover_thumb_url = None
    if cover:
        if cover.get("media_type") == MEDIA_TYPE_VIDEO:
            cover_thumb_url = f"/api/video-poster/{cover['id']}"
        else:
            cover_thumb_url = f"/api/photo-thumbnail/{cover['id']}"

    return {
        "id": album["id"],
        "name": album["name"],
        "cover_thumb_url": cover_thumb_url,
        "photo_count": image_count if scan_status != "error" else None,
        "media_count": len(media_items) if scan_status != "error" else None,
        "video_count": video_count if scan_status != "error" else None,
        "recursive": album.get("recursive", True),
        "enabled": album.get("enabled", True),
        "scan_status": scan_status,
        "updated_at": updated_at,
        "error": error,
    }


def add_photo_album(paths, data):
    path = data.get("path")
    if not isinstance(path, str) or not path.strip():
        return {"error": "Photo album path is required"}, 400

    absolute_path = os.path.abspath(os.path.expanduser(path.strip()))
    if not os.path.isdir(absolute_path):
        return {"error": "Photo album path is not available"}, 400

    current_config = load_config()
    albums = normalize_photo_album_roots(current_config)
    album_id = make_photo_album_id(absolute_path)
    existing = next((album for album in albums if album["id"] == album_id), None)
    if existing:
        return {"success": True, "album": build_photo_album_response(paths, existing), "duplicate": True}, 200

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        name = os.path.basename(os.path.normpath(absolute_path)) or absolute_path

    recursive = data.get("recursive", True) is not False
    new_album = {
        "id": album_id,
        "name": name.strip(),
        "path": absolute_path,
        "recursive": recursive,
        "enabled": True,
    }

    current_config["photo_gallery_roots"] = [
        {
            "id": album["id"],
            "name": album["name"],
            "path": album["path"],
            "recursive": album["recursive"],
            "enabled": album["enabled"],
        }
        for album in albums
    ] + [new_album]
    save_config(current_config)

    return {"success": True, "album": build_photo_album_response(paths, new_album)}, 200


def delete_photo_album(paths, album_id):
    current_config = load_config()
    albums = normalize_photo_album_roots(current_config)
    next_albums = [album for album in albums if album["id"] != album_id]
    if len(next_albums) == len(albums):
        return {"error": "Album not found"}, 404

    current_config["photo_gallery_roots"] = next_albums
    save_config(current_config)

    with photo_index_lock:
        index_data = load_photo_index(paths)
        photos = index_data.setdefault("photos", {})
        stale_items = [
            (photo_id, meta.get("media_type") or MEDIA_TYPE_IMAGE)
            for photo_id, meta in photos.items()
            if isinstance(meta, dict) and meta.get("album_id") == album_id
        ]
        stale_ids = [photo_id for photo_id, _media_type in stale_items]
        for photo_id in stale_ids:
            photos.pop(photo_id, None)
        save_photo_index(paths, index_data)

    cleanup_album_media_cache(paths, stale_items)
    return {"success": True}, 200


def cleanup_album_media_cache(paths, media_items):
    """删除相册移除后不再可达的图片缩略图和视频封面缓存。"""
    for media_id, media_type in media_items:
        if media_type == MEDIA_TYPE_VIDEO:
            remove_cache_files_for_media(paths.video_poster_folder, media_id)
        else:
            remove_cache_files_for_media(paths.photo_thumbnail_folder, media_id)


def remove_cache_files_for_media(cache_folder, media_id):
    if not os.path.isdir(cache_folder):
        return

    prefix = f"{media_id}-"
    try:
        filenames = os.listdir(cache_folder)
    except OSError:
        return

    for filename in filenames:
        if not filename.startswith(prefix):
            continue
        cache_path = os.path.join(cache_folder, filename)
        try:
            if os.path.isfile(cache_path):
                os.remove(cache_path)
        except OSError:
            pass


def get_media_counts(media_items):
    image_count = sum(1 for item in media_items if item.get("media_type") == MEDIA_TYPE_IMAGE)
    video_count = sum(1 for item in media_items if item.get("media_type") == MEDIA_TYPE_VIDEO)
    return {
        "all": len(media_items),
        "image": image_count,
        "photo": image_count,
        "video": video_count,
    }


def list_album_photos(paths, album_id, sort, cursor_value, limit_value, media_type_value=MEDIA_TYPE_ALL):
    album = find_photo_album(album_id)
    if not album:
        return {"error": "Album not found"}, 404

    media_items, scan_status, error = scan_photo_album(paths, album)
    media_counts = get_media_counts(media_items)
    if scan_status == "error":
        return {
            "items": [],
            "next_cursor": None,
            "total": 0,
            "media_counts": media_counts,
            "scan_status": scan_status,
            "error": error,
        }, 200

    requested_media_type = normalize_media_type(media_type_value)
    if requested_media_type != MEDIA_TYPE_ALL:
        media_items = [
            item for item in media_items
            if item.get("media_type") == requested_media_type
        ]

    if sort == "mtime_asc":
        media_items.sort(key=lambda item: item.get("mtime", 0))
    elif sort == "ctime_desc":
        media_items.sort(key=lambda item: item.get("ctime", item.get("mtime", 0)), reverse=True)
    elif sort == "ctime_asc":
        media_items.sort(key=lambda item: item.get("ctime", item.get("mtime", 0)))
    elif sort == "name_asc":
        media_items.sort(key=lambda item: item.get("name", "").lower())
    elif sort == "name_desc":
        media_items.sort(key=lambda item: item.get("name", "").lower(), reverse=True)
    elif sort == "size_desc":
        media_items.sort(key=lambda item: item.get("size", 0), reverse=True)
    elif sort == "size_asc":
        media_items.sort(key=lambda item: item.get("size", 0))
    else:
        media_items.sort(key=lambda item: item.get("mtime", 0), reverse=True)

    try:
        cursor = max(0, int(cursor_value))
    except ValueError:
        cursor = 0

    try:
        limit = int(limit_value)
    except ValueError:
        limit = PHOTO_DEFAULT_PAGE_SIZE
    limit = max(1, min(limit, PHOTO_MAX_PAGE_SIZE))

    page = media_items[cursor:cursor + limit]
    next_cursor = cursor + limit if cursor + limit < len(media_items) else None

    return {
        "items": [build_photo_item(paths, meta) for meta in page],
        "next_cursor": str(next_cursor) if next_cursor is not None else None,
        "total": len(media_items),
        "media_counts": media_counts,
        "scan_status": scan_status,
        "error": error,
    }, 200


def make_unique_photo_upload_filename(filename, target_folder):
    """为上传到照片图库的文件生成安全且不冲突的文件名。"""
    safe_name = secure_filename(filename)
    name, ext = os.path.splitext(safe_name)
    if not ext:
        _, ext = os.path.splitext(filename)

    ext = ext.lower()
    if ext not in PHOTO_UPLOAD_EXTENSIONS:
        return None

    if not name:
        name = "photo"

    candidate = f"{name}{ext}"
    candidate_path = os.path.join(target_folder, candidate)
    if not os.path.exists(candidate_path):
        return candidate

    suffix = uuid.uuid4().hex[:8]
    return f"{name}-{suffix}{ext}"


def is_valid_uploaded_photo(path):
    """验证上传文件是否为 Pillow 可识别的图片。"""
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


def upload_photos_to_album(paths, album_id, files):
    """上传图片到当前照片相册。"""
    album = find_photo_album(album_id)
    if not album:
        return {"error": "Album not found"}, 404
    if not album.get("enabled", True):
        return {"error": "Album is disabled"}, 400

    album_root = os.path.realpath(os.path.abspath(album["path"]))
    if not os.path.isdir(album_root):
        return {"error": "Album folder is unavailable"}, 400

    if not files or files[0].filename == "":
        return {"error": "No selected file"}, 400

    uploaded = 0
    failed = []

    for uploaded_file in files[:PHOTO_MAX_UPLOAD_BATCH]:
        original_name = uploaded_file.filename or "photo"
        filename = make_unique_photo_upload_filename(original_name, album_root)
        if not filename:
            failed.append({"name": original_name, "error": "Unsupported image format"})
            continue

        target_path = os.path.realpath(os.path.join(album_root, filename))
        if not is_real_path_inside(target_path, album_root):
            failed.append({"name": original_name, "error": "Unsafe upload path"})
            continue

        try:
            uploaded_file.save(target_path)
            if not is_valid_uploaded_photo(target_path):
                try:
                    os.remove(target_path)
                except OSError:
                    pass
                failed.append({"name": original_name, "error": "Invalid image file"})
                continue

            uploaded += 1
        except Exception as exc:
            try:
                if os.path.exists(target_path):
                    os.remove(target_path)
            except OSError:
                pass
            failed.append({"name": original_name, "error": str(exc)})

    if uploaded == 0:
        return {
            "success": False,
            "uploaded": uploaded,
            "failed": failed,
            "error": "No valid photos uploaded",
        }, 400

    scan_photo_album(paths, album)
    return {
        "success": True,
        "uploaded": uploaded,
        "failed": failed,
        "album": build_photo_album_response(paths, album),
    }, 200


def make_unique_input_filename(paths, filename):
    """为照片转 3D 生成唯一输入文件名。"""
    safe_name = secure_filename(filename)
    name, ext = os.path.splitext(safe_name)
    if not ext:
        _, ext = os.path.splitext(filename)
    if not name:
        name = "photo"
    if not ext:
        ext = ".jpg"

    candidate = f"{name}{ext}"
    candidate_path = os.path.join(paths.input_folder, candidate)
    if not os.path.exists(candidate_path):
        return candidate

    suffix = uuid.uuid4().hex[:8]
    return f"{name}-{suffix}{ext}"


def make_unique_archive_name(filename, used_names):
    """Create a safe unique filename for files inside the downloaded ZIP."""
    safe_name = str(filename or "photo").replace("\\", "_").replace("/", "_").replace("\0", "").strip()
    if not safe_name:
        safe_name = "photo"

    stem, ext = os.path.splitext(safe_name)
    if not stem:
        stem = "photo"

    candidate = f"{stem}{ext}"
    counter = 2
    while candidate.casefold() in used_names:
        candidate = f"{stem} ({counter}){ext}"
        counter += 1

    used_names.add(candidate.casefold())
    return candidate


def cleanup_expired_photo_download_zips(paths, max_age_seconds=PHOTO_DOWNLOAD_ZIP_TTL_SECONDS):
    """清理中断下载或异常退出遗留的临时图库 ZIP。"""
    cache_folder = paths.photo_gallery_cache_folder
    if not os.path.isdir(cache_folder):
        return

    now = datetime.datetime.now().timestamp()
    try:
        filenames = os.listdir(cache_folder)
    except OSError:
        return

    for filename in filenames:
        if not filename.startswith("photo-gallery-") or not filename.endswith(".zip"):
            continue

        zip_path = os.path.join(cache_folder, filename)
        try:
            stat = os.stat(zip_path)
        except OSError:
            continue

        if now - stat.st_mtime < max_age_seconds:
            continue

        try:
            if os.path.isfile(zip_path):
                os.remove(zip_path)
        except OSError:
            pass


def create_photo_download_zip(paths, photo_ids):
    photo_ids = [str(photo_id) for photo_id in photo_ids[:PHOTO_MAX_DOWNLOAD_BATCH]]
    os.makedirs(paths.photo_gallery_cache_folder, exist_ok=True)
    cleanup_expired_photo_download_zips(paths)
    fd, zip_path = tempfile.mkstemp(
        prefix="photo-gallery-",
        suffix=".zip",
        dir=paths.photo_gallery_cache_folder,
    )
    os.close(fd)

    added_count = 0
    failed = []
    used_names = set()

    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for photo_id in photo_ids:
                resolved = resolve_media_path(paths, photo_id)
                if not resolved:
                    failed.append({"id": photo_id, "error": "Media not found"})
                    continue

                _, full_path, meta = resolved
                archive_name = make_unique_archive_name(meta.get("name") or os.path.basename(full_path), used_names)
                archive.write(full_path, archive_name)
                added_count += 1

        if added_count == 0:
            try:
                os.remove(zip_path)
            except OSError:
                pass
            return None, {"error": "No downloadable media found", "failed": failed}, 404

        download_name = f"sharp-gui-media-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        return {
            "zip_path": zip_path,
            "download_name": download_name,
            "added_count": added_count,
            "failed": failed,
        }, None, 200
    except Exception as exc:
        try:
            os.remove(zip_path)
        except OSError:
            pass
        return None, {"error": str(exc)}, 500


def convert_photos_to_models(paths, task_manager, photo_ids):
    photo_ids = [str(photo_id) for photo_id in photo_ids[:PHOTO_MAX_CONVERSION_BATCH]]
    created_tasks = []
    failed = []

    for photo_id in photo_ids:
        resolved = resolve_photo_path(paths, photo_id)
        if not resolved:
            media_resolved = resolve_media_path(paths, photo_id, allow_stale=True)
            if media_resolved and media_resolved[2].get("media_type") == MEDIA_TYPE_VIDEO:
                failed.append({"id": photo_id, "error": "Only photos can be converted to 3D"})
            else:
                failed.append({"id": photo_id, "error": "Photo not found"})
            continue

        _, full_path, meta = resolved
        filename = make_unique_input_filename(paths, meta.get("name") or os.path.basename(full_path))
        input_path = os.path.join(paths.input_folder, filename)

        try:
            shutil.copy2(full_path, input_path)
            task_info = task_manager.enqueue_file(input_path, filename)
            created_tasks.append(task_info)
            print(f"📥 Photo conversion task added: {filename} (ID: {task_info['id']})")
        except Exception as exc:
            failed.append({"id": photo_id, "error": str(exc)})

    return {
        "success": len(created_tasks) > 0,
        "tasks": created_tasks,
        "failed": failed,
    }
