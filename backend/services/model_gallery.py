import datetime
import os

from PIL import Image

from backend.services.static_files import get_relative_files_path

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
    return os.path.join(paths.thumbnail_folder, item_id + ".jpg")


def find_original_image(paths, item_id):
    """根据条目 ID 查找原图文件名和路径。"""
    for ext in ALLOWED_IMAGE_EXTENSIONS:
        filename = item_id + ext
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


def get_file_version(path):
    """获取文件版本号（基于修改时间）。"""
    return int(os.path.getmtime(path) * 1000)


def get_file_timestamp(path):
    """获取 ISO 格式的文件修改时间。"""
    return datetime.datetime.fromtimestamp(
        os.path.getmtime(path),
        tz=datetime.timezone.utc,
    ).isoformat()


def build_gallery_item(paths, ply_filename, repair_missing_thumbnail=False):
    """构建单个图库条目的响应数据。"""
    name_without_ext = os.path.splitext(ply_filename)[0]
    ply_path = os.path.join(paths.output_folder, ply_filename)

    if not os.path.exists(ply_path):
        return None

    ply_size = os.path.getsize(ply_path)
    file_timestamps = [os.path.getmtime(ply_path)]

    spz_filename = name_without_ext + ".spz"
    spz_path = os.path.join(paths.output_folder, spz_filename)
    spz_url = None
    spz_size = None
    if os.path.exists(spz_path):
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
        thumb_path = ensure_thumbnail_for_item(paths, name_without_ext, allow_generation=True)

    thumb_url = None
    thumb_version = None
    if thumb_path and os.path.exists(thumb_path):
        thumb_url = f"/api/thumbnail/{name_without_ext}"
        thumb_version = get_file_version(thumb_path)
        file_timestamps.append(os.path.getmtime(thumb_path))

    latest_timestamp = max(file_timestamps)

    return {
        "id": name_without_ext,
        "name": name_without_ext,
        "model_url": f"/files/{get_relative_files_path(ply_path, paths)}",
        "spz_url": spz_url,
        "image_url": image_url,
        "thumb_url": thumb_url,
        "thumb_version": thumb_version,
        "size": ply_size,
        "spz_size": spz_size,
        "created_at": get_file_timestamp(ply_path),
        "updated_at": datetime.datetime.fromtimestamp(
            latest_timestamp,
            tz=datetime.timezone.utc,
        ).isoformat(),
    }


def list_gallery_items(paths):
    """获取图库列表。"""
    items = []
    if os.path.exists(paths.output_folder):
        files = [f for f in os.listdir(paths.output_folder) if f.endswith(".ply")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(paths.output_folder, x)), reverse=True)
        remaining_thumbnail_repairs = MAX_THUMBNAIL_REPAIRS_PER_REQUEST

        for ply_filename in files:
            item_id = os.path.splitext(ply_filename)[0]
            thumb_missing = not os.path.exists(get_thumbnail_path(paths, item_id))
            repair_thumbnail = thumb_missing and remaining_thumbnail_repairs > 0
            gallery_item = build_gallery_item(
                paths,
                ply_filename,
                repair_missing_thumbnail=repair_thumbnail,
            )
            if gallery_item:
                items.append(gallery_item)
            if repair_thumbnail:
                remaining_thumbnail_repairs -= 1
    return items


def delete_gallery_item(paths, item_id):
    """删除图库项目，包括原图、PLY、SPZ 模型和缩略图。"""
    ply_path = os.path.join(paths.output_folder, item_id + ".ply")
    if os.path.exists(ply_path):
        os.remove(ply_path)

    spz_path = os.path.join(paths.output_folder, item_id + ".spz")
    if os.path.exists(spz_path):
        os.remove(spz_path)

    thumb_path = os.path.join(paths.thumbnail_folder, item_id + ".jpg")
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    for ext in [".jpg", ".jpeg", ".png", ".webp", ".JPG", ".PNG"]:
        img_path = os.path.join(paths.input_folder, item_id + ext)
        if os.path.exists(img_path):
            os.remove(img_path)


def find_original_image_filename(paths, item_id):
    filename, _ = find_original_image(paths, item_id)
    return filename


def resolve_download_model(paths, item_id, fmt):
    """返回应下载的模型文件名，优先 SPZ，回退 PLY。"""
    if fmt == "spz":
        spz_path = os.path.join(paths.output_folder, item_id + ".spz")
        if os.path.exists(spz_path):
            return item_id + ".spz"

    ply_path = os.path.join(paths.output_folder, item_id + ".ply")
    if not os.path.exists(ply_path):
        return None
    return item_id + ".ply"
