import os

from flask import Blueprint, current_app, g, jsonify, request, send_file, send_from_directory

from backend.services import photo_gallery

bp = Blueprint("photo_gallery", __name__)


def get_paths():
    return current_app.config["PATH_CONTEXT"]


@bp.route("/api/photo-albums", methods=["GET", "POST"])
def photo_albums():
    """照片相册列表与新增配置。"""
    paths = get_paths()
    if request.method == "GET":
        albums = [
            photo_gallery.build_photo_album_response(paths, album)
            for album in photo_gallery.normalize_photo_album_roots()
        ]
        return jsonify({"albums": albums, "is_local": g.is_owner})

    if not g.is_owner:
        return jsonify({"error": "Photo albums can only be modified from localhost"}), 403

    payload, status_code = photo_gallery.add_photo_album(paths, request.get_json() or {})
    return jsonify(payload), status_code


@bp.route("/api/photo-albums/<album_id>", methods=["DELETE"])
def delete_photo_album(album_id):
    """移除照片相册配置，不删除原始照片。"""
    if not g.is_owner:
        return jsonify({"error": "Photo albums can only be modified from localhost"}), 403

    payload, status_code = photo_gallery.delete_photo_album(get_paths(), album_id)
    return jsonify(payload), status_code


@bp.route("/api/photo-albums/<album_id>/scan", methods=["POST"])
def scan_photo_album_endpoint(album_id):
    """重新扫描照片相册。"""
    if not g.is_owner:
        return jsonify({"error": "Photo albums can only be rescanned from localhost"}), 403

    paths = get_paths()
    album = photo_gallery.find_photo_album(album_id)
    if not album:
        return jsonify({"error": "Album not found"}), 404

    return jsonify({"success": True, "album": photo_gallery.build_photo_album_response(paths, album)})


@bp.route("/api/photo-albums/<album_id>/photos")
def get_photo_album_photos(album_id):
    """分页获取相册照片。"""
    payload, status_code = photo_gallery.list_album_photos(
        get_paths(),
        album_id,
        request.args.get("sort", "mtime_desc"),
        request.args.get("cursor", "0"),
        request.args.get("limit", str(photo_gallery.PHOTO_DEFAULT_PAGE_SIZE)),
    )
    return jsonify(payload), status_code


@bp.route("/api/photo-thumbnail/<photo_id>")
def get_photo_thumbnail(photo_id):
    """获取照片缩略图。"""
    paths = get_paths()
    thumb_path = photo_gallery.ensure_photo_thumbnail(paths, photo_id)
    if not thumb_path or not os.path.exists(thumb_path):
        return jsonify({"error": "Thumbnail not found"}), 404

    filename = os.path.basename(thumb_path)
    response = send_from_directory(
        paths.photo_thumbnail_folder,
        filename,
        conditional=True,
        max_age=photo_gallery.PHOTO_THUMBNAIL_CACHE_SECONDS,
    )
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    response.cache_control.public = True
    response.cache_control.max_age = photo_gallery.PHOTO_THUMBNAIL_CACHE_SECONDS
    return response


@bp.route("/api/photo-original/<photo_id>")
def get_photo_original(photo_id):
    """获取照片原图，支持 inline 预览和附件下载。"""
    resolved = photo_gallery.resolve_photo_path(get_paths(), photo_id)
    if not resolved:
        return jsonify({"error": "Photo not found"}), 404

    _, full_path, meta = resolved
    download = request.args.get("download", "0").lower() in ("1", "true", "yes")
    return send_from_directory(
        os.path.dirname(full_path),
        os.path.basename(full_path),
        as_attachment=download,
        download_name=meta.get("name") or os.path.basename(full_path),
        conditional=True,
        max_age=3600,
    )


@bp.route("/api/photo-albums/<album_id>/uploads", methods=["POST"])
def upload_photos_to_album(album_id):
    """上传图片到当前照片相册，供局域网设备添加照片。"""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist("file")
    payload, status_code = photo_gallery.upload_photos_to_album(get_paths(), album_id, files)
    return jsonify(payload), status_code


@bp.route("/api/photo-downloads", methods=["POST"])
def download_photos():
    """Download selected original photos as a ZIP archive."""
    data = request.get_json() or {}
    photo_ids = data.get("photo_ids")
    if not isinstance(photo_ids, list) or not photo_ids:
        return jsonify({"error": "photo_ids is required"}), 400

    result, error_payload, status_code = photo_gallery.create_photo_download_zip(get_paths(), photo_ids)
    if error_payload:
        return jsonify(error_payload), status_code

    response = send_file(
        result["zip_path"],
        as_attachment=True,
        download_name=result["download_name"],
        mimetype="application/zip",
        max_age=0,
        conditional=False,
    )
    response.headers["X-Photo-Download-Count"] = str(result["added_count"])
    response.headers["X-Photo-Download-Failed"] = str(len(result["failed"]))

    @response.call_on_close
    def cleanup_zip():
        try:
            os.remove(result["zip_path"])
        except OSError:
            pass

    return response


@bp.route("/api/photo-conversions", methods=["POST"])
def convert_photos_to_models():
    """将照片图库中的照片加入现有 3D 生成队列。"""
    data = request.get_json() or {}
    photo_ids = data.get("photo_ids")
    if not isinstance(photo_ids, list) or not photo_ids:
        return jsonify({"error": "photo_ids is required"}), 400

    task_manager = current_app.config["TASK_MANAGER"]
    payload = photo_gallery.convert_photos_to_models(get_paths(), task_manager, photo_ids)
    return jsonify(payload)
