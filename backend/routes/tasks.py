from flask import Blueprint, current_app, jsonify

bp = Blueprint("tasks", __name__)


@bp.route("/api/tasks")
def get_tasks():
    """获取所有任务状态，支持智能轮询。"""
    task_manager = current_app.config["TASK_MANAGER"]
    tasks, has_active = task_manager.list_tasks()
    return jsonify({
        "tasks": tasks,
        "has_active": has_active,
    })


@bp.route("/api/task/<task_id>/cancel", methods=["POST"])
def cancel_task(task_id):
    """取消队列中的任务。"""
    task_manager = current_app.config["TASK_MANAGER"]
    payload, status_code = task_manager.cancel_task(task_id)
    return jsonify(payload), status_code
