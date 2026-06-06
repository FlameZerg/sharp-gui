import os

from flask import Blueprint, abort, current_app, send_from_directory

from backend.services.static_files import resolve_files_route_path

bp = Blueprint("files", __name__)


@bp.route("/files/<path:filename>")
def serve_files(filename):
    paths = current_app.config["PATH_CONTEXT"]
    resolved_path, basename, cache_timeout = resolve_files_route_path(paths, filename)
    if not resolved_path:
        abort(404)

    return send_from_directory(
        os.path.dirname(resolved_path),
        basename,
        conditional=True,
        max_age=cache_timeout,
    )
