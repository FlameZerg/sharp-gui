import os

from flask import Blueprint, abort, render_template, send_from_directory

from backend import runtime

bp = Blueprint("frontend", __name__)

REACT_ROOT_STATIC_FILES = {
    "favicon.ico",
    "favicon.svg",
    "favicon-96x96.png",
    "apple-touch-icon.png",
    "site.webmanifest",
    "web-app-manifest-192x192.png",
    "web-app-manifest-512x512.png",
    "logo.png",
}


@bp.route("/")
def index():
    """根据模式返回前端页面。"""
    if runtime.FRONTEND_MODE == "legacy":
        return render_template("index.html")

    react_index = os.path.join(runtime.REACT_BUILD_DIR, "index.html")
    if os.path.exists(react_index):
        return send_from_directory(runtime.REACT_BUILD_DIR, "index.html")

    return render_template("index.html")


@bp.route("/assets/<path:filename>")
def react_assets(filename):
    """服务 React 静态资源。"""
    return send_from_directory(
        os.path.join(runtime.REACT_BUILD_DIR, "assets"),
        filename,
        max_age=31536000,
    )


@bp.route("/<path:filename>")
def react_root_static(filename):
    """服务 React 根目录静态文件。"""
    if filename in REACT_ROOT_STATIC_FILES:
        return send_from_directory(runtime.REACT_BUILD_DIR, filename)
    abort(404)
