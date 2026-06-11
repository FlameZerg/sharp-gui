from flask import Blueprint, current_app, jsonify, request

from backend.config import get_video_reconstruction_config
from backend.services import video_reconstruction

bp = Blueprint("video_reconstruction", __name__)


@bp.route("/api/video-reconstructions", methods=["POST"])
def create_video_reconstruction():
    """从本地视频创建 3DGS 重建任务。"""
    request_data, error_payload, status_code = video_reconstruction.validate_create_request(
        request.get_json(silent=True) or {},
    )
    if error_payload:
        return jsonify(error_payload), status_code

    paths = current_app.config["PATH_CONTEXT"]
    task_payload, build_error, build_status = video_reconstruction.build_video_task(paths, request_data)
    if build_error:
        return jsonify(build_error), build_status

    task_manager = current_app.config["TASK_MANAGER"]
    task = task_manager.enqueue_video_reconstruction(task_payload)
    return jsonify({
        "success": True,
        "task": task,
    })


@bp.route("/api/video-reconstructions/status")
def video_reconstruction_status():
    """返回视频重建默认配置和本机依赖诊断。"""
    return jsonify({
        "config": get_video_reconstruction_config(),
        "dependencies": video_reconstruction.check_dependencies(),
    })
