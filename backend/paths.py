import os
from dataclasses import dataclass

from backend import runtime


@dataclass(frozen=True)
class PathContext:
    workspace_folder: str
    input_folder: str
    output_folder: str
    thumbnail_folder: str
    photo_gallery_cache_folder: str
    photo_thumbnail_folder: str
    video_poster_folder: str
    photo_index_file: str

    @property
    def allowed_file_serve_roots(self):
        return (self.output_folder, self.thumbnail_folder)


def build_path_context(config_data):
    workspace_folder = config_data.get("workspace_folder", runtime.DEFAULT_WORKSPACE_FOLDER)
    input_folder = os.path.join(workspace_folder, "inputs")
    output_folder = os.path.join(workspace_folder, "outputs")
    thumbnail_folder = os.path.join(input_folder, ".thumbnails")
    photo_gallery_cache_folder = os.path.join(workspace_folder, ".photo-gallery-cache")
    photo_thumbnail_folder = os.path.join(photo_gallery_cache_folder, "thumbnails")
    video_poster_folder = os.path.join(photo_gallery_cache_folder, "video-posters")
    photo_index_file = os.path.join(photo_gallery_cache_folder, "index.json")

    return PathContext(
        workspace_folder=workspace_folder,
        input_folder=input_folder,
        output_folder=output_folder,
        thumbnail_folder=thumbnail_folder,
        photo_gallery_cache_folder=photo_gallery_cache_folder,
        photo_thumbnail_folder=photo_thumbnail_folder,
        video_poster_folder=video_poster_folder,
        photo_index_file=photo_index_file,
    )


def ensure_runtime_directories(paths):
    os.makedirs(paths.input_folder, exist_ok=True)
    os.makedirs(paths.output_folder, exist_ok=True)
    os.makedirs(paths.thumbnail_folder, exist_ok=True)
    os.makedirs(paths.photo_thumbnail_folder, exist_ok=True)
    os.makedirs(paths.video_poster_folder, exist_ok=True)


def install_path_config(app, paths):
    app.config["PATH_CONTEXT"] = paths
    app.config["WORKSPACE_FOLDER"] = paths.workspace_folder
    app.config["INPUT_FOLDER"] = paths.input_folder
    app.config["OUTPUT_FOLDER"] = paths.output_folder
    app.config["THUMBNAIL_FOLDER"] = paths.thumbnail_folder
    app.config["PHOTO_GALLERY_CACHE_FOLDER"] = paths.photo_gallery_cache_folder
    app.config["PHOTO_THUMBNAIL_FOLDER"] = paths.photo_thumbnail_folder
    app.config["VIDEO_POSTER_FOLDER"] = paths.video_poster_folder
