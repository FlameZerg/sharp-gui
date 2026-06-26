import datetime
import json
import os
import re
import shutil
import subprocess
import uuid
from urllib.parse import quote

from PIL import Image

<<<<<<< HEAD
from backend.services.static_files import get_relative_files_path, is_real_path_inside
=======
from backend.config import load_config
from backend.services.static_files import get_relative_files_path
>>>>>>> b0117b4 (update)

ALLOWED_IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".JPG",
    ".JPEG",
    ".PNG",
    ".WEBP",
)
MAX_THUMBNAIL_REPAIRS_PER_REQUEST = 6
THUMBNAIL_CACHE_SECONDS = 86400
DEFAULT_FILE_CACHE_SECONDS = 3600
MODEL_METADATA_SUFFIX = ".meta.json"
VIDEO_THUMBNAIL_WIDTH = 200


def generate_thumbnail(paths, input_path, filename):
    """生成缩略图 (200px 宽度, JPEG 80% 质量)。"""
    try:
        thumb_path = os.path.join(paths.thumbnail_folder, os.path.splitext(filename)[0] + ".jpg")
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            width = 200
            ratio = width / img.width
            height = int(img.height * ratio)
            img_resized = img.resize((width, height), Image.LANCZOS)
            img_resized.save(thumb_path, "JPEG", quality=80)
        return thumb_path
    except Exception as exc:
        print(f"⚠️ Thumbnail generation failed for {filename}: {exc}")
        return None


def get_thumbnail_path(paths, item_id):
    """获取图库条目的缩略图路径。"""
    base_id = os.path.splitext(item_id)[0] if item_id.endswith((".ply", ".spz", ".splat", ".rad")) else item_id
    return os.path.join(paths.thumbnail_folder, base_id + ".jpg")


def get_model_metadata_path(paths, item_id):
    """获取模型图库条目的 sidecar 元数据路径。"""
    return os.path.join(paths.output_folder, item_id + MODEL_METADATA_SUFFIX)


def get_video_uploads_folder(paths):
    """获取拖拽上传视频的持久源文件目录。"""
    return os.path.join(paths.video_reconstruction_folder, "uploads")


def read_model_metadata(paths, item_id):
    """读取模型图库条目的 sidecar 元数据。"""
    metadata_path = get_model_metadata_path(paths, item_id)
    try:
        with open(metadata_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_model_metadata(paths, item_id, metadata):
    """写入模型图库条目的 sidecar 元数据。"""
    os.makedirs(paths.output_folder, exist_ok=True)
    metadata_path = get_model_metadata_path(paths, item_id)
    payload = {
        **(metadata if isinstance(metadata, dict) else {}),
        "id": item_id,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    temp_path = f"{metadata_path}.tmp-{uuid.uuid4().hex[:8]}"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(temp_path, metadata_path)
    return metadata_path


def resolve_gallery_source_video(paths, item_id):
    """解析图库条目的源视频，仅允许照片图库视频或受控上传缓存。"""
    metadata = read_model_metadata(paths, item_id)
    if metadata.get("source_media_type") != "video":
        return None

    source_media_id = metadata.get("source_media_id")
    if isinstance(source_media_id, str) and source_media_id:
        from backend.services import photo_gallery

        resolved = photo_gallery.resolve_media_path(
            paths,
            source_media_id,
            expected_type=photo_gallery.MEDIA_TYPE_VIDEO,
            allow_stale=True,
        )
        if resolved:
            _, full_path, meta = resolved
            return {
                "path": full_path,
                "name": meta.get("name") or os.path.basename(full_path),
                "mime_type": meta.get("mime_type") or photo_gallery.get_video_mime_type(full_path),
            }

    source_video_path = metadata.get("source_video_path")
    if not isinstance(source_video_path, str) or not source_video_path:
        return None

    upload_root = os.path.realpath(get_video_uploads_folder(paths))
    real_path = os.path.realpath(source_video_path)
    if not is_real_path_inside(real_path, upload_root) or not os.path.isfile(real_path):
        return None

    from backend.services import photo_gallery

    return {
        "path": real_path,
        "name": metadata.get("source_name") or os.path.basename(real_path),
        "mime_type": metadata.get("source_mime_type") or photo_gallery.get_video_mime_type(real_path),
    }


def normalize_stem_for_match(value):
    """Normalize a media/model stem for conservative legacy video backfill."""
    stem = os.path.splitext(os.path.basename(str(value or "")))[0]
    stem = re.sub(r"\s+", "_", stem).strip("._ ").lower()
    return stem


def legacy_video_match_stems(item_id):
    """Return possible source video stems for old generated model names.

    NOTE: This only serves early video reconstruction outputs whose filenames
    still carried explicit quality/cleanup suffixes (produced before the
    "default to source video stem" naming policy landed). New outputs use the
    source video stem directly, so no suffix stripping is needed for them; this
    backfill is intentionally conservative and only runs when a model has no
    sidecar metadata and matches exactly one same-name gallery video.
    """
    stem = normalize_stem_for_match(item_id)
    stems = {stem}
    without_collision_suffix = re.sub(r"-\d+$", "", stem)
    if without_collision_suffix:
        stems.add(without_collision_suffix)
    legacy_suffixes = (
        "_high180_focused",
        "_preview_final_clean_focused",
        "_preview_clean_focused",
        "_preview_focused",
        "_focused",
    )
    for suffix in legacy_suffixes:
        if stem.endswith(suffix):
            stems.add(stem[: -len(suffix)])
    return {candidate for candidate in stems if candidate}


def find_unique_gallery_video_for_model(paths, item_id):
    """Find a unique same-name gallery video for legacy outputs missing sidecar metadata."""
    from backend.services import photo_gallery

    target_stems = legacy_video_match_stems(item_id)
    if not target_stems:
        return None

    matched_meta = []
    for meta in photo_gallery.load_photo_index(paths).get("photos", {}).values():
        if not isinstance(meta, dict) or meta.get("media_type") != photo_gallery.MEDIA_TYPE_VIDEO:
            continue
        name = meta.get("name") or meta.get("relative_path") or meta.get("id")
        if normalize_stem_for_match(name) in target_stems:
            matched_meta.append(meta)

    resolved_by_path = {}
    for meta in matched_meta:
        resolved = photo_gallery.resolve_media_path(
            paths,
            meta["id"],
            expected_type=photo_gallery.MEDIA_TYPE_VIDEO,
            allow_stale=True,
        )
        if not resolved:
            continue
        _, full_path, resolved_meta = resolved
        resolved_by_path[os.path.realpath(full_path)] = (full_path, resolved_meta)

    if len(resolved_by_path) != 1:
        return None

    return next(iter(resolved_by_path.values()))


def backfill_legacy_video_metadata(paths, item_id):
    """Create video sidecar metadata for old video reconstruction outputs when it is safe."""
    if read_model_metadata(paths, item_id):
        return {}

    original_filename, original_path = find_original_image(paths, item_id)
    if original_filename and original_path:
        return {}

    match = find_unique_gallery_video_for_model(paths, item_id)
    if not match:
        return {}

    from backend.services import photo_gallery

    full_path, meta = match
    metadata = {
        "source_media_type": "video",
        "source_media_id": meta.get("id"),
        "source_name": meta.get("name") or os.path.basename(full_path),
        "source_video_path": full_path,
        "source_mime_type": meta.get("mime_type") or photo_gallery.get_video_mime_type(full_path),
        "generator": "video_3dgs",
        "recovered_from": "gallery-video-stem",
    }
    try:
        write_model_metadata(paths, item_id, metadata)
        generate_video_thumbnail(paths, full_path, item_id)
        return metadata
    except Exception as exc:
        print(f"⚠️ Failed to backfill video metadata for {item_id}: {exc}")
        return {}


def find_original_image(paths, item_id):
    """根据条目 ID 查找原图文件名和路径。"""
    base_id = os.path.splitext(item_id)[0] if item_id.endswith((".ply", ".spz", ".splat", ".rad")) else item_id
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        filename = base_id + ext
        img_path = os.path.join(paths.input_folder, filename)
        if os.path.exists(img_path):
            return filename, img_path
    return None, None


def ensure_thumbnail_for_item(paths, item_id, allow_generation=False):
    """确保图库条目存在可用缩略图。"""
    thumb_path = get_thumbnail_path(paths, item_id)
    if os.path.exists(thumb_path):
        return thumb_path

    if not allow_generation:
        return None

    original_filename, original_path = find_original_image(paths, item_id)
    if not original_filename or not original_path:
        return None

    return generate_thumbnail(paths, original_path, original_filename)


def generate_video_thumbnail(paths, source_video_path, item_id):
    """从源视频抽一帧生成模型缩略图。"""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not os.path.isfile(source_video_path):
        return None

    os.makedirs(paths.thumbnail_folder, exist_ok=True)
    thumb_path = get_thumbnail_path(paths, item_id)
    temp_path = f"{thumb_path}.tmp-{uuid.uuid4().hex[:8]}.jpg"
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
                source_video_path,
                "-frames:v",
                "1",
                "-vf",
                f"scale={VIDEO_THUMBNAIL_WIDTH}:-2",
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
        os.replace(temp_path, thumb_path)
        return thumb_path
    except Exception as exc:
        print(f"⚠️ Video thumbnail generation failed for {item_id}: {exc}")
        return None
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


def get_file_version(path):
    """获取文件版本号（基于修改时间）。"""
    return int(os.path.getmtime(path) * 1000)


def get_file_timestamp(path):
    """获取 ISO 格式的文件修改时间。"""
    return datetime.datetime.fromtimestamp(
        os.path.getmtime(path),
        tz=datetime.timezone.utc,
    ).isoformat()


def build_gallery_item(paths, model_filename, repair_missing_thumbnail=False):
    """构建单个图库条目的响应数据。"""
    name_without_ext = os.path.splitext(model_filename)[0]
    ext = os.path.splitext(model_filename)[1].lower()

    if ext == ".ply":
        ply_path = os.path.join(paths.output_folder, model_filename)
        spz_path = os.path.join(paths.output_folder, name_without_ext + ".spz")
        primary_path = ply_path
    elif ext == ".spz":
        spz_path = os.path.join(paths.output_folder, model_filename)
        ply_path = os.path.join(paths.output_folder, name_without_ext + ".ply")
        primary_path = spz_path
    elif ext in (".splat", ".rad"):
        primary_path = os.path.join(paths.output_folder, model_filename)
        spz_path = os.path.join(paths.output_folder, name_without_ext + ".spz")
        ply_path = os.path.join(paths.output_folder, name_without_ext + ".ply")
    else:
        return None

<<<<<<< HEAD
    ply_size = os.path.getsize(ply_path)
    file_timestamps = [os.path.getmtime(ply_path)]
    metadata = read_model_metadata(paths, name_without_ext)
    if not metadata and repair_missing_thumbnail:
        metadata = backfill_legacy_video_metadata(paths, name_without_ext)
    metadata_path = get_model_metadata_path(paths, name_without_ext)
    if os.path.exists(metadata_path):
        file_timestamps.append(os.path.getmtime(metadata_path))
=======
    if not os.path.exists(primary_path):
        return None

    primary_size = os.path.getsize(primary_path)
    file_timestamps = [os.path.getmtime(primary_path)]
>>>>>>> b0117b4 (update)

    spz_url = None
    spz_size = None
    # 仅在当前项本身为 spz 格式时设置 spz_url，避免 ply 项加载/下载时混淆
    if ext == ".spz" and os.path.exists(spz_path):
        spz_url = f"/files/{get_relative_files_path(spz_path, paths)}"
        spz_size = os.path.getsize(spz_path)
        file_timestamps.append(os.path.getmtime(spz_path))

    original_filename, original_path = find_original_image(paths, name_without_ext)
    image_url = None
    if original_filename and original_path:
        image_url = f"/api/original/{name_without_ext}"
        file_timestamps.append(os.path.getmtime(original_path))

    thumb_path = get_thumbnail_path(paths, name_without_ext)
    if not os.path.exists(thumb_path) and repair_missing_thumbnail:
        if metadata.get("source_media_type") == "video":
            source_video = resolve_gallery_source_video(paths, name_without_ext)
            if source_video:
                thumb_path = generate_video_thumbnail(paths, source_video["path"], name_without_ext)
        else:
            thumb_path = ensure_thumbnail_for_item(paths, name_without_ext, allow_generation=True)

    thumb_url = None
    thumb_version = None
    if thumb_path and os.path.exists(thumb_path):
        thumb_url = f"/api/thumbnail/{name_without_ext}"
        thumb_version = get_file_version(thumb_path)
        file_timestamps.append(os.path.getmtime(thumb_path))

    latest_timestamp = max(file_timestamps)

<<<<<<< HEAD
    item = {
        "id": name_without_ext,
        "name": name_without_ext,
        "model_url": f"/files/{get_relative_files_path(ply_path, paths)}",
=======
    return {
        "id": model_filename, # 用包含扩展名的 model_filename 作为唯一 ID 避免去重和 key 冲突
        "name": model_filename, # 让用户在前端卡片中能清晰看到后缀
        "model_url": f"/files/{get_relative_files_path(primary_path, paths)}",
>>>>>>> b0117b4 (update)
        "spz_url": spz_url,
        "image_url": image_url,
        "thumb_url": thumb_url,
        "thumb_version": thumb_version,
        "size": primary_size,
        "spz_size": spz_size,
        "created_at": get_file_timestamp(primary_path),
        "updated_at": datetime.datetime.fromtimestamp(
            latest_timestamp,
            tz=datetime.timezone.utc,
        ).isoformat(),
    }

    if metadata.get("source_media_type") == "video":
        item.update({
            "source_media_type": "video",
            "source_media_id": metadata.get("source_media_id"),
            "source_name": metadata.get("source_name"),
            "source_video_url": f"/api/gallery/{quote(name_without_ext, safe='')}/source-video",
        })

    return item


def list_gallery_items(paths):
    """获取图库列表。"""
    items = []
<<<<<<< HEAD
    if os.path.exists(paths.output_folder):
        files = [f for f in os.listdir(paths.output_folder) if f.endswith(".ply")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(paths.output_folder, x)), reverse=True)
        remaining_asset_repairs = MAX_THUMBNAIL_REPAIRS_PER_REQUEST

        for ply_filename in files:
            item_id = os.path.splitext(ply_filename)[0]
            thumb_missing = not os.path.exists(get_thumbnail_path(paths, item_id))
            metadata_missing = not os.path.exists(get_model_metadata_path(paths, item_id))
            repair_assets = (thumb_missing or metadata_missing) and remaining_asset_repairs > 0
            gallery_item = build_gallery_item(
                paths,
                ply_filename,
                repair_missing_thumbnail=repair_assets,
            )
            if gallery_item:
                items.append(gallery_item)
            if repair_assets:
                remaining_asset_repairs -= 1
=======
    if not os.path.exists(paths.output_folder):
        return items

    # 保留所有独立的 .ply 和 .spz 模型，不进行同名去重合并
    files = []
    for f in os.listdir(paths.output_folder):
        ext_lower = os.path.splitext(f)[1].lower()
        if ext_lower in (".ply", ".spz", ".splat", ".rad"):
            files.append(f)

    files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(paths.output_folder, x)), reverse=True)
    remaining_thumbnail_repairs = MAX_THUMBNAIL_REPAIRS_PER_REQUEST

    for model_filename in files:
        item_id = os.path.splitext(model_filename)[0]
        thumb_missing = not os.path.exists(get_thumbnail_path(paths, item_id))
        repair_thumbnail = thumb_missing and remaining_thumbnail_repairs > 0
        gallery_item = build_gallery_item(
            paths,
            model_filename,
            repair_missing_thumbnail=repair_thumbnail,
        )
        if gallery_item:
            items.append(gallery_item)
        if repair_thumbnail:
            remaining_thumbnail_repairs -= 1
>>>>>>> b0117b4 (update)
    return items


def delete_gallery_item(paths, item_id):
<<<<<<< HEAD
    """删除图库项目，包括原图、PLY、SPZ 模型和缩略图。"""
    metadata = read_model_metadata(paths, item_id)

    ply_path = os.path.join(paths.output_folder, item_id + ".ply")
    if os.path.exists(ply_path):
        os.remove(ply_path)

    spz_path = os.path.join(paths.output_folder, item_id + ".spz")
    if os.path.exists(spz_path):
        os.remove(spz_path)

    thumb_path = os.path.join(paths.thumbnail_folder, item_id + ".jpg")
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    for ext in ALLOWED_IMAGE_EXTENSIONS:
        img_path = os.path.join(paths.input_folder, item_id + ext)
        if os.path.exists(img_path):
            os.remove(img_path)
=======
    """删除图库项目，支持根据后缀精确删除，只有在所有格式都删除后才清除缩略图和原图。"""
    base_id = os.path.splitext(item_id)[0] if item_id.endswith((".ply", ".spz", ".splat", ".rad")) else item_id
    
    # 1. 精确删除模型
    if item_id.endswith(".ply"):
        ply_path = os.path.join(paths.output_folder, item_id)
        if os.path.exists(ply_path):
            os.remove(ply_path)
    elif item_id.endswith(".spz"):
        spz_path = os.path.join(paths.output_folder, item_id)
        if os.path.exists(spz_path):
            os.remove(spz_path)
    elif item_id.endswith((".splat", ".rad")):
        file_path = os.path.join(paths.output_folder, item_id)
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        # 无后缀情况，视为全部删除
        for ext in (".ply", ".spz", ".splat", ".rad"):
            file_path = os.path.join(paths.output_folder, item_id + ext)
            if os.path.exists(file_path):
                os.remove(file_path)

    # 2. 判断是否没有其他同名模型存在了，是则清除原图和缩略图
    other_exts = [".spz", ".ply", ".splat", ".rad"]
    current_ext = os.path.splitext(item_id)[1].lower() if "." in item_id else ""
    has_other = False
    for ext in other_exts:
        if ext != current_ext:
            if os.path.exists(os.path.join(paths.output_folder, base_id + ext)):
                has_other = True
                break
    
    if not has_other:
        thumb_path = os.path.join(paths.thumbnail_folder, base_id + ".jpg")
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".JPG", ".PNG"]:
            img_path = os.path.join(paths.input_folder, base_id + ext)
            if os.path.exists(img_path):
                os.remove(img_path)
>>>>>>> b0117b4 (update)

    delete_uploaded_source_video(paths, metadata)

    metadata_path = get_model_metadata_path(paths, item_id)
    if os.path.exists(metadata_path):
        os.remove(metadata_path)


def delete_uploaded_source_video(paths, metadata):
    """删除拖拽上传视频的源文件缓存，不触碰照片图库原视频。"""
    if not isinstance(metadata, dict) or metadata.get("source_media_id"):
        return

    source_video_path = metadata.get("source_video_path")
    if not isinstance(source_video_path, str) or not source_video_path:
        return

    upload_root = os.path.realpath(get_video_uploads_folder(paths))
    real_path = os.path.realpath(source_video_path)
    if not is_real_path_inside(real_path, upload_root):
        return

    try:
        if os.path.isfile(real_path):
            os.remove(real_path)
        parent = os.path.dirname(real_path)
        if is_real_path_inside(parent, upload_root) and not os.listdir(parent):
            os.rmdir(parent)
    except OSError:
        pass


def find_original_image_filename(paths, item_id):
    filename, _ = find_original_image(paths, item_id)
    return filename


def resolve_download_model(paths, item_id, fmt):
    """返回应下载的模型文件名，支持精确匹配文件名，退回则优先 SPZ，回退 PLY。"""
    # 如果 item_id 本身就是个带后缀的完整存在的文件，直接返回它
    full_path = os.path.join(paths.output_folder, item_id)
    if os.path.exists(full_path):
        return item_id

    # 否则退回到 base name 判断
    base_id = os.path.splitext(item_id)[0] if item_id.endswith((".ply", ".spz")) else item_id
    if fmt == "spz":
        spz_path = os.path.join(paths.output_folder, base_id + ".spz")
        if os.path.exists(spz_path):
            return base_id + ".spz"

    ply_path = os.path.join(paths.output_folder, base_id + ".ply")
    if not os.path.exists(ply_path):
        return None
    return base_id + ".ply"
