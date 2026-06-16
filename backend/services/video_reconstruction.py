import os
import copy
import re
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from shutil import which

from werkzeug.utils import secure_filename

from backend import runtime
from backend.config import get_video_reconstruction_config
from backend.services import model_gallery, photo_gallery
from backend.services.static_files import is_real_path_inside

TASK_KIND_VIDEO_3DGS = "video_3dgs"

VALID_RECONSTRUCTION_MODES = {"auto", "object", "environment"}
VALID_RECONSTRUCTION_QUALITIES = {"preview", "high", "extreme"}
VALID_RECONSTRUCTION_ENGINES = {"auto", "stable", "experimental"}
VALID_VRAM_BUDGETS = {"auto", "8gb", "12gb", "16gb", "24gb"}

ERROR_DEPENDENCY_MISSING = "video_reconstruction_dependency_missing"
ERROR_DEPENDENCIES_CHECKING = "video_reconstruction_dependencies_checking"
ERROR_STABLE_UNAVAILABLE = "video_reconstruction_stable_unavailable"
ERROR_EXPERIMENTAL_UNAVAILABLE = "video_reconstruction_experimental_unavailable"
ERROR_INVALID_REQUEST = "video_reconstruction_invalid_request"
ERROR_SOURCE_UNAVAILABLE = "video_reconstruction_source_unavailable"
ERROR_CANCELLED = "video_reconstruction_cancelled"
ERROR_OOM = "video_reconstruction_oom"
ERROR_OUTPUT_MISSING = "video_reconstruction_output_missing"
ERROR_SPZ_FAILED = "video_reconstruction_spz_failed"
ERROR_UNSUPPORTED_VIDEO = "video_reconstruction_unsupported_video"

QUALITY_PROFILES = {
    "preview": {
        "frame_count": 90,
        "max_resolution": 1280,
        "max_num_iterations": 7000,
        "num_downscales": 3,
        "downscale_factor": 4,
        "matching_method": "sequential",
        "train_cameras_sampling_strategy": "fps",
        "camera_optimizer_mode": "off",
        "num_random": 50000,
        "densify_grad_thresh": 0.0008,
        "cull_alpha_thresh": 0.1,
        "use_scale_regularization": False,
        "use_bilateral_grid": False,
        "cache_images": "gpu",
        "progress_weight": 0.18,
    },
    "high": {
        "frame_count": 180,
        "max_resolution": 1920,
        "max_num_iterations": 30000,
        "num_downscales": 2,
        "downscale_factor": 2,
        "matching_method": "sequential",
        "train_cameras_sampling_strategy": "fps",
        "camera_optimizer_mode": "SO3xR3",
        "num_random": 80000,
        "densify_grad_thresh": 0.00055,
        "cull_alpha_thresh": 0.04,
        "use_scale_regularization": True,
        "use_bilateral_grid": True,
        "cache_images": "gpu",
        "progress_weight": 0.45,
    },
    "extreme": {
        "frame_count": 360,
        "max_resolution": 2160,
        "max_num_iterations": 50000,
        "num_downscales": 1,
        "downscale_factor": 1,
        "matching_method": "sequential",
        "train_cameras_sampling_strategy": "fps",
        "camera_optimizer_mode": "SO3xR3",
        "num_random": 120000,
        "densify_grad_thresh": 0.0004,
        "cull_alpha_thresh": 0.02,
        "use_scale_regularization": True,
        "use_bilateral_grid": True,
        "cache_images": "cpu",
        "progress_weight": 0.72,
    },
}

FOCUSED_CLEANUP_PROFILE = {
    "position_quantiles": (5.0, 95.0),
    "alpha_min": 0.12,
    "scale_quantile": 98.5,
    "min_keep_ratio": 0.25,
    "min_vertices": 1000,
}

VRAM_PROFILE_LIMITS = {
    "auto": {
        "frame_scale": 1.0,
        "iteration_scale": 1.0,
        "max_resolution_cap": 1600,
    },
    "8gb": {
        "frame_scale": 0.72,
        "iteration_scale": 0.75,
        "max_resolution_cap": 1280,
    },
    "12gb": {
        "frame_scale": 1.0,
        "iteration_scale": 1.0,
        "max_resolution_cap": 1920,
    },
    "16gb": {
        "frame_scale": 1.18,
        "iteration_scale": 1.1,
        "max_resolution_cap": 1920,
    },
    "24gb": {
        "frame_scale": 1.35,
        "iteration_scale": 1.2,
        "max_resolution_cap": 2160,
    },
}

STAGE_PROGRESS = {
    "video_prepare": 3,
    "video_extract_frames": 12,
    "video_foreground": 22,
    "video_geometry": 34,
    "video_optimize": 58,
    "video_export": 86,
    "video_compress_spz": 94,
    "video_done": 100,
}

OOM_PATTERNS = (
    "cuda out of memory",
    "outofmemoryerror",
    "cublas_status_alloc_failed",
    "cudnn_status_alloc_failed",
    "hip out of memory",
    "memoryerror",
)

_DEPENDENCY_STATUS_LOCK = threading.Lock()
_DEPENDENCY_STATUS_CACHE = None
_DEPENDENCY_STATUS_CHECKED_AT = None
_DEPENDENCY_STATUS_REFRESHING = False


def ensure_local_video_reconstruction_path():
    root = Path(__file__).resolve().parents[2]
    local_env = root / ".video-reconstruction-env"
    candidates = [
        local_env / "Scripts",
        local_env / "colmap" / "bin",
    ]
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    normalized = {os.path.normcase(os.path.abspath(part)) for part in path_parts if part}
    additions = []

    for candidate in candidates:
        if candidate.exists():
            candidate_text = str(candidate)
            key = os.path.normcase(os.path.abspath(candidate_text))
            if key not in normalized:
                additions.append(candidate_text)
                normalized.add(key)

    if additions:
        os.environ["PATH"] = os.pathsep.join([*path_parts, *additions])


def find_existing_path(candidates):
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def find_cuda_home():
    configured = os.environ.get("CUDA_HOME") or os.environ.get("CUDA_PATH")
    candidates = [
        configured,
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8",
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9",
    ]
    return find_existing_path(candidates)


def find_vcvars64():
    candidates = [
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
        r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
        r"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat",
        r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
    ]
    return find_existing_path(candidates)


def read_vcvars_environment():
    vcvars = find_vcvars64()
    if not vcvars:
        return {}

    script_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".cmd",
            delete=False,
            encoding="utf-8",
            newline="\r\n",
        ) as script:
            script.write("@echo off\n")
            script.write(f'call "{vcvars}" >nul\n')
            script.write("set\n")
            script_path = script.name

        result = subprocess.run(
            ["cmd.exe", "/d", "/c", script_path],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except Exception:
        return {}
    finally:
        if script_path:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    if result.returncode != 0:
        return {}

    env = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    return env


def build_video_process_env():
    ensure_local_video_reconstruction_path()

    process_env = os.environ.copy()
    vc_env = read_vcvars_environment()
    if vc_env:
        process_env.update(vc_env)
        for path_key in ("PATH", "Path", "path"):
            if vc_env.get(path_key):
                process_env["PATH"] = vc_env[path_key]
                break

    path_parts = []
    local_env = Path(__file__).resolve().parents[2] / ".video-reconstruction-env"
    for candidate in (
        local_env / "Scripts",
        local_env / "colmap" / "bin",
    ):
        if candidate.exists():
            path_parts.append(str(candidate))

    cuda_home = find_cuda_home()
    if cuda_home:
        process_env["CUDA_HOME"] = cuda_home
        process_env["CUDA_PATH"] = cuda_home
        cuda_bin = os.path.join(cuda_home, "bin")
        if os.path.exists(cuda_bin):
            path_parts.append(cuda_bin)

    path_parts.append(process_env.get("PATH", ""))

    process_env["PATH"] = os.pathsep.join(part for part in path_parts if part)
    if os.name == "nt":
        process_env["Path"] = process_env["PATH"]
    process_env.setdefault("PYTHONUTF8", "1")
    process_env.setdefault("PYTHONIOENCODING", "utf-8")
    process_env.setdefault("TORCH_CUDA_ARCH_LIST", "12.0")
    process_env.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    process_env.setdefault("VSLANG", "1033")
    return process_env


def normalize_video_reconstruction_settings(value):
    raw = value if isinstance(value, dict) else {}
    defaults = get_video_reconstruction_config(persist_missing=False)
    quality = raw.get("default_quality")
    engine = raw.get("default_engine")
    vram_budget = raw.get("vram_budget")

    return {
        "default_quality": quality if quality in VALID_RECONSTRUCTION_QUALITIES else defaults["default_quality"],
        "default_engine": engine if engine in VALID_RECONSTRUCTION_ENGINES else defaults["default_engine"],
        "vram_budget": vram_budget if vram_budget in VALID_VRAM_BUDGETS else defaults["vram_budget"],
        "keep_intermediate_files": bool(raw.get("keep_intermediate_files")),
    }


def coerce_form_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def validate_reconstruction_options(data):
    if not isinstance(data, dict):
        data = {}

    config = get_video_reconstruction_config()
    mode = data.get("mode") or "auto"
    quality = data.get("quality") or config["default_quality"]
    engine = data.get("engine") or config["default_engine"]
    output_name = data.get("output_name")

    if mode not in VALID_RECONSTRUCTION_MODES:
        return None, {
            "error": "Unsupported reconstruction mode",
            "code": ERROR_INVALID_REQUEST,
            "field": "mode",
        }, 400
    if quality not in VALID_RECONSTRUCTION_QUALITIES:
        return None, {
            "error": "Unsupported reconstruction quality",
            "code": ERROR_INVALID_REQUEST,
            "field": "quality",
        }, 400
    if engine not in VALID_RECONSTRUCTION_ENGINES:
        return None, {
            "error": "Unsupported reconstruction engine",
            "code": ERROR_INVALID_REQUEST,
            "field": "engine",
        }, 400

    if output_name is not None:
        if not isinstance(output_name, str):
            return None, {
                "error": "output_name must be a string",
                "code": ERROR_INVALID_REQUEST,
                "field": "output_name",
            }, 400
        output_name = output_name.strip()
        if len(output_name) > 120:
            return None, {
                "error": "output_name is too long",
                "code": ERROR_INVALID_REQUEST,
                "field": "output_name",
            }, 400

    keep_intermediate_files = data.get("keep_intermediate_files")
    if keep_intermediate_files is None:
        keep_intermediate_files = config["keep_intermediate_files"]

    return {
        "mode": mode,
        "quality": quality,
        "engine": engine,
        "vram_budget": config["vram_budget"],
        "output_name": output_name or None,
        "keep_intermediate_files": coerce_form_bool(keep_intermediate_files, config["keep_intermediate_files"]),
    }, None, 200


def validate_create_request(data):
    request_data, error_payload, status_code = validate_reconstruction_options(data)
    if error_payload:
        return None, error_payload, status_code

    video_id = data.get("video_id") if isinstance(data, dict) else None
    if not isinstance(video_id, str) or not video_id.strip():
        return None, {
            "error": "video_id is required",
            "code": ERROR_INVALID_REQUEST,
            "field": "video_id",
        }, 400

    return {
        **request_data,
        "video_id": video_id.strip(),
    }, None, 200


def validate_upload_request(form_data, uploaded_file):
    request_data, error_payload, status_code = validate_reconstruction_options(dict(form_data or {}))
    if error_payload:
        return None, error_payload, status_code

    if not uploaded_file or not uploaded_file.filename:
        return None, {
            "error": "video file is required",
            "code": ERROR_INVALID_REQUEST,
            "field": "file",
        }, 400

    original_name = uploaded_file.filename
    extension = os.path.splitext(original_name)[1].lower()
    if extension not in photo_gallery.ALLOWED_VIDEO_EXTENSIONS:
        return None, {
            "error": "Unsupported video format",
            "code": ERROR_UNSUPPORTED_VIDEO,
            "field": "file",
        }, 400

    return {
        **request_data,
        "source_name": original_name,
    }, None, 200


def resolve_quality_profile(quality, vram_budget):
    base = QUALITY_PROFILES.get(quality, QUALITY_PROFILES["high"])
    limits = VRAM_PROFILE_LIMITS.get(vram_budget, VRAM_PROFILE_LIMITS["auto"])

    frame_count = max(24, int(round(base["frame_count"] * limits["frame_scale"])))
    max_iterations = max(1000, int(round(base["max_num_iterations"] * limits["iteration_scale"])))
    max_resolution = min(base["max_resolution"], limits["max_resolution_cap"])
    downscale_factor = resolve_downscale_factor(base["downscale_factor"], max_resolution)
    num_downscales = max(base["num_downscales"], downscale_factor_to_num_downscales(downscale_factor))

    return {
        **base,
        "frame_count": frame_count,
        "max_num_iterations": max_iterations,
        "max_resolution": max_resolution,
        "downscale_factor": downscale_factor,
        "num_downscales": num_downscales,
        "vram_budget": vram_budget if vram_budget in VRAM_PROFILE_LIMITS else "auto",
    }


def resolve_downscale_factor(base_downscale_factor, max_resolution):
    downscale_factor = max(1, int(base_downscale_factor))
    if max_resolution <= 1280:
        return max(downscale_factor, 4)
    if max_resolution <= 1920:
        return max(downscale_factor, 2)
    return downscale_factor


def downscale_factor_to_num_downscales(downscale_factor):
    downscale_factor = max(1, int(downscale_factor))
    num_downscales = 0
    generated_factor = 1
    while generated_factor < downscale_factor:
        generated_factor *= 2
        num_downscales += 1
    return num_downscales


def command_version(name, args=None, timeout=5):
    command = which(name)
    if not command:
        return {
            "name": name,
            "category": "required",
            "required": True,
            "available": False,
            "version": None,
            "message": f"{name} not found in PATH",
        }

    try:
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        result = subprocess.run(
            [command, *(args or ["-version"])],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        output = (result.stdout or result.stderr or "").strip().splitlines()
        return {
            "name": name,
            "category": "required",
            "required": True,
            "available": result.returncode == 0,
            "version": output[0][:220] if output else None,
            "message": None if result.returncode == 0 else f"{name} returned {result.returncode}",
        }
    except Exception as exc:
        return {
            "name": name,
            "category": "required",
            "required": True,
            "available": False,
            "version": None,
            "message": str(exc),
        }


def resolve_video_python():
    """Return the Python executable that hosts the video reconstruction env."""
    local_env = Path(__file__).resolve().parents[2] / ".video-reconstruction-env"
    candidates = [
        local_env / "Scripts" / "python.exe",
        local_env / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return which("python") or which("python3") or "python"


def python_module_available(module_name, python_executable=None):
    executable = python_executable or resolve_video_python()
    try:
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        result = subprocess.run(
            [executable, "-c", f"import {module_name}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
            env=env,
        )
        return result.returncode == 0
    except Exception:
        return False


def _decorate_dependency_status(dependencies, *, checked_at, refreshing, cached):
    result = copy.deepcopy(dependencies)
    summary = result.setdefault("summary", {})
    summary["checking"] = bool(refreshing)
    summary["checked_at"] = checked_at
    summary["cached"] = bool(cached)
    return result


def _pending_dependency_status():
    message = "Video reconstruction tools are being checked in the background."
    return {
        "required": {
            "available": False,
            "tools": [],
            "message": message,
        },
        "stable": {
            "available": False,
            "tools": [],
            "message": message,
        },
        "experimental": {
            "available": False,
            "tools": [],
            "message": "Experimental initialization status is pending.",
        },
        "summary": {
            "available": False,
            "stable_available": False,
            "experimental_available": False,
            "checking": True,
            "checked_at": None,
            "cached": False,
        },
    }


def _dependency_error_status(exc):
    message = f"Failed to check video reconstruction tools: {exc}"
    return {
        "required": {
            "available": False,
            "tools": [],
            "message": message,
        },
        "stable": {
            "available": False,
            "tools": [],
            "message": message,
        },
        "experimental": {
            "available": False,
            "tools": [],
            "message": "Experimental initialization status could not be checked.",
        },
        "summary": {
            "available": False,
            "stable_available": False,
            "experimental_available": False,
        },
    }


def _scan_dependencies():
    ensure_local_video_reconstruction_path()

    ffmpeg = command_version("ffmpeg")
    ffprobe = command_version("ffprobe")

    ns_process_data = command_version("ns-process-data", ["--help"], timeout=30)
    ns_train = command_version("ns-train", ["--help"], timeout=30)
    ns_export = command_version("ns-export", ["--help"], timeout=30)
    colmap = command_version("colmap", ["-h"], timeout=10)
    stable_tools = [ns_process_data, ns_train, ns_export, colmap]
    for tool in stable_tools:
        tool["category"] = "stable"
        tool["required"] = True

    vggt = {
        "name": "vggt",
        "category": "experimental",
        "required": False,
        "available": python_module_available("vggt"),
        "version": None,
        "message": None,
    }
    if not vggt["available"]:
        vggt["message"] = "VGGT is not configured locally. Auto will use the stable route."

    required_tools = [ffmpeg, ffprobe]
    stable_available = all(tool["available"] for tool in stable_tools)
    required_available = all(tool["available"] for tool in required_tools)
    experimental_available = vggt["available"]

    return {
        "required": {
            "available": required_available,
            "tools": required_tools,
            "message": None if required_available else "ffmpeg and ffprobe are required for video decoding.",
        },
        "stable": {
            "available": required_available and stable_available,
            "tools": stable_tools,
            "message": None if stable_available else "Nerfstudio CLI tools and COLMAP are required for the stable Splatfacto route.",
        },
        "experimental": {
            "available": experimental_available,
            "tools": [vggt],
            "message": None if experimental_available else "Experimental VGGT initialization is not configured.",
        },
        "summary": {
            "available": required_available and stable_available,
            "stable_available": required_available and stable_available,
            "experimental_available": experimental_available,
        },
    }


def resolve_engine_strategy(engine, dependencies=None):
    dependencies = dependencies or check_dependencies()
    stable_available = bool(dependencies["stable"]["available"])
    experimental_available = bool(dependencies["experimental"]["available"])

    if engine == "stable":
        if not stable_available:
            return None, ERROR_STABLE_UNAVAILABLE
        return "stable", None

    if engine == "experimental":
        if not experimental_available:
            return None, ERROR_EXPERIMENTAL_UNAVAILABLE
        if not stable_available:
            return None, ERROR_STABLE_UNAVAILABLE
        return "experimental", None

    if stable_available:
        return "stable", None
    if experimental_available:
        return None, ERROR_STABLE_UNAVAILABLE
    return None, ERROR_DEPENDENCY_MISSING


def sanitize_output_stem(name):
    raw = str(name or "").strip()
    if not raw:
        raw = "video-reconstruction"
    raw = os.path.splitext(os.path.basename(raw))[0]
    raw = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", raw)
    raw = re.sub(r"\s+", "_", raw).strip("._ ")
    if not raw:
        raw = "video-reconstruction"

    safe_ascii = secure_filename(raw)
    if safe_ascii:
        return safe_ascii[:96]

    readable = "".join(ch for ch in raw if ch.isalnum() or ch in ("-", "_", " "))
    readable = re.sub(r"\s+", "_", readable).strip("._ ")
    return (readable or "video-reconstruction")[:96]


def unique_output_paths(paths, requested_name, fallback_name):
    base = sanitize_output_stem(requested_name or fallback_name)
    for index in range(1000):
        suffix = "" if index == 0 else f"-{index + 1}"
        stem = f"{base}{suffix}"
        ply_path = os.path.join(paths.output_folder, f"{stem}.ply")
        spz_path = os.path.join(paths.output_folder, f"{stem}.spz")
        if not os.path.exists(ply_path) and not os.path.exists(spz_path):
            return stem, ply_path, spz_path
    raise RuntimeError("Could not allocate a unique output name")


def resolve_source_video(paths, video_id):
    resolved = photo_gallery.resolve_media_path(
        paths,
        video_id,
        expected_type=photo_gallery.MEDIA_TYPE_VIDEO,
        allow_stale=True,
    )
    if not resolved:
        return None

    album, full_path, meta = resolved
    root_path = os.path.realpath(album["path"])
    real_path = os.path.realpath(full_path)
    if not is_real_path_inside(real_path, root_path) or not os.path.isfile(real_path):
        return None
    if meta.get("media_type") != photo_gallery.MEDIA_TYPE_VIDEO:
        return None
    return album, real_path, meta


def build_video_task(paths, request_data):
    source = resolve_source_video(paths, request_data["video_id"])
    if not source:
        return None, {
            "error": "Video not found",
            "code": ERROR_SOURCE_UNAVAILABLE,
        }, 404

    _, full_path, meta = source
    dependencies = check_dependencies()
    if dependencies.get("summary", {}).get("checking"):
        return None, {
            "error": "Video reconstruction dependencies are still being checked",
            "code": ERROR_DEPENDENCIES_CHECKING,
            "dependencies": dependencies,
        }, 409
    engine, engine_error = resolve_engine_strategy(request_data["engine"], dependencies)
    if engine_error:
        return None, {
            "error": "Video reconstruction dependencies are not available",
            "code": engine_error,
            "dependencies": dependencies,
        }, 409

    output_name, output_path, spz_path = unique_output_paths(
        paths,
        request_data.get("output_name"),
        meta.get("name") or os.path.basename(full_path),
    )

    task_payload = {
        "kind": TASK_KIND_VIDEO_3DGS,
        "filename": f"{output_name}.ply",
        "source_media_id": request_data["video_id"],
        "source_name": meta.get("name") or os.path.basename(full_path),
        "source_video_path": full_path,
        "mode": request_data["mode"],
        "quality": request_data["quality"],
        "engine": request_data["engine"],
        "resolved_engine": engine,
        "vram_budget": request_data["vram_budget"],
        "output_name": output_name,
        "output_path": output_path,
        "spz_path": spz_path,
        "keep_intermediate_files": request_data["keep_intermediate_files"],
        "details": {
            "dependencies": dependencies,
            "warnings": [],
            "logs": [],
        },
    }
    prepare_video_model_assets(paths, task_payload, generate_thumbnail=False)
    return task_payload, None, 200


def save_uploaded_source_video(paths, uploaded_file):
    original_name = uploaded_file.filename or "video.mp4"
    safe_name = secure_filename(original_name)
    if not safe_name:
        _, ext = os.path.splitext(original_name)
        safe_name = f"video{ext.lower() if ext else '.mp4'}"

    upload_id = uuid.uuid4().hex
    upload_dir = os.path.join(model_gallery.get_video_uploads_folder(paths), upload_id)
    os.makedirs(upload_dir, exist_ok=True)
    target_path = os.path.realpath(os.path.join(upload_dir, safe_name))
    upload_root = os.path.realpath(model_gallery.get_video_uploads_folder(paths))
    if not is_real_path_inside(target_path, upload_root):
        raise ValueError("Unsafe uploaded video path")

    uploaded_file.save(target_path)
    return target_path


def build_uploaded_video_task(paths, request_data, uploaded_file):
    dependencies = check_dependencies()
    if dependencies.get("summary", {}).get("checking"):
        return None, {
            "error": "Video reconstruction dependencies are still being checked",
            "code": ERROR_DEPENDENCIES_CHECKING,
            "dependencies": dependencies,
        }, 409
    engine, engine_error = resolve_engine_strategy(request_data["engine"], dependencies)
    if engine_error:
        return None, {
            "error": "Video reconstruction dependencies are not available",
            "code": engine_error,
            "dependencies": dependencies,
        }, 409

    source_name = request_data.get("source_name") or uploaded_file.filename or "video.mp4"
    output_name, output_path, spz_path = unique_output_paths(
        paths,
        request_data.get("output_name"),
        source_name,
    )
    source_video_path = save_uploaded_source_video(paths, uploaded_file)

    task_payload = {
        "kind": TASK_KIND_VIDEO_3DGS,
        "filename": f"{output_name}.ply",
        "source_media_id": None,
        "source_name": source_name,
        "source_video_path": source_video_path,
        "source_mime_type": uploaded_file.mimetype,
        "mode": request_data["mode"],
        "quality": request_data["quality"],
        "engine": request_data["engine"],
        "resolved_engine": engine,
        "vram_budget": request_data["vram_budget"],
        "output_name": output_name,
        "output_path": output_path,
        "spz_path": spz_path,
        "keep_intermediate_files": request_data["keep_intermediate_files"],
        "details": {
            "dependencies": dependencies,
            "warnings": [],
            "logs": [],
        },
    }
    prepare_video_model_assets(paths, task_payload, generate_thumbnail=False)
    return task_payload, None, 200


def _refresh_dependency_status_sync():
    global _DEPENDENCY_STATUS_CACHE, _DEPENDENCY_STATUS_CHECKED_AT, _DEPENDENCY_STATUS_REFRESHING

    try:
        dependencies = _scan_dependencies()
    except Exception as exc:
        dependencies = _dependency_error_status(exc)

    checked_at = time.time()
    with _DEPENDENCY_STATUS_LOCK:
        _DEPENDENCY_STATUS_CACHE = dependencies
        _DEPENDENCY_STATUS_CHECKED_AT = checked_at
        _DEPENDENCY_STATUS_REFRESHING = False

    return _decorate_dependency_status(
        dependencies,
        checked_at=checked_at,
        refreshing=False,
        cached=True,
    )


def start_dependency_warmup(force=False):
    """Start one non-blocking dependency scan for this process."""
    global _DEPENDENCY_STATUS_REFRESHING

    with _DEPENDENCY_STATUS_LOCK:
        if _DEPENDENCY_STATUS_REFRESHING:
            return False
        if _DEPENDENCY_STATUS_CACHE is not None and not force:
            return False
        _DEPENDENCY_STATUS_REFRESHING = True

    thread = threading.Thread(
        target=_refresh_dependency_status_sync,
        name="video-reconstruction-dependency-check",
        daemon=True,
    )
    thread.start()
    return True


def get_dependency_status(force=False):
    """Return cached dependency status immediately and warm it in the background."""
    if force:
        start_dependency_warmup(force=True)
    else:
        start_dependency_warmup()

    with _DEPENDENCY_STATUS_LOCK:
        if _DEPENDENCY_STATUS_CACHE is None:
            return _pending_dependency_status()
        return _decorate_dependency_status(
            _DEPENDENCY_STATUS_CACHE,
            checked_at=_DEPENDENCY_STATUS_CHECKED_AT,
            refreshing=_DEPENDENCY_STATUS_REFRESHING,
            cached=True,
        )


def check_dependencies(force=False):
    """Return video reconstruction dependencies, reusing the per-process cache."""
    global _DEPENDENCY_STATUS_REFRESHING

    with _DEPENDENCY_STATUS_LOCK:
        if _DEPENDENCY_STATUS_CACHE is not None and not force:
            return _decorate_dependency_status(
                _DEPENDENCY_STATUS_CACHE,
                checked_at=_DEPENDENCY_STATUS_CHECKED_AT,
                refreshing=_DEPENDENCY_STATUS_REFRESHING,
                cached=True,
            )
        if _DEPENDENCY_STATUS_REFRESHING and not force:
            return _pending_dependency_status()
        _DEPENDENCY_STATUS_REFRESHING = True

    return _refresh_dependency_status_sync()


def build_video_model_metadata(task):
    """Build safe sidecar metadata for a video reconstruction output."""
    return {
        "source_media_type": "video",
        "source_media_id": task.get("source_media_id"),
        "source_name": task.get("source_name"),
        "source_video_path": task.get("source_video_path"),
        "source_mime_type": task.get("source_mime_type"),
        "generator": TASK_KIND_VIDEO_3DGS,
        "mode": task.get("mode"),
        "quality": task.get("quality"),
        "engine": task.get("engine"),
        "resolved_engine": task.get("resolved_engine"),
    }


def prepare_video_model_assets(paths, task, *, generate_thumbnail=True):
    """Write sidecar metadata early and optionally prepare the video thumbnail."""
    model_id = os.path.splitext(os.path.basename(task["output_path"]))[0]
    metadata = build_video_model_metadata(task)
    try:
        model_gallery.write_model_metadata(paths, model_id, metadata)
    except Exception as exc:
        print(f"⚠️ Failed to write model metadata for {model_id}: {exc}")

    if generate_thumbnail:
        try:
            model_gallery.generate_video_thumbnail(paths, task["source_video_path"], model_id)
        except Exception as exc:
            print(f"⚠️ Failed to generate video model thumbnail for {model_id}: {exc}")


def persist_video_model_assets(paths, task):
    """为视频重建输出写入图库元数据并生成源视频缩略图。"""
    prepare_video_model_assets(paths, task, generate_thumbnail=True)


def update_task(task_manager, task_id, **patch):
    log_snapshot = None
    with task_manager.task_lock:
        task = task_manager.task_status.get(task_id)
        if task:
            previous_stage = task.get("stage")
            task.update(patch)
            log_snapshot = {
                "filename": task.get("filename"),
                "status": task.get("status"),
                "stage": task.get("stage"),
                "progress": task.get("progress"),
                "error": task.get("error"),
                "error_code": task.get("error_code"),
                "output_path": task.get("output_path"),
                "previous_stage": previous_stage,
            }

    if not log_snapshot:
        return

    status = patch.get("status")
    stage = patch.get("stage")
    if status == "failed":
        runtime.log(
            "ERROR",
            "Video task "
            f"{task_id} failed: file={log_snapshot['filename']} "
            f"stage={log_snapshot['stage']} code={log_snapshot['error_code']} "
            f"error={log_snapshot['error']}",
        )
    elif status == "cancelled":
        runtime.log("WARN", f"Video task {task_id} cancelled: file={log_snapshot['filename']} stage={log_snapshot['stage']}")
    elif status == "completed":
        log_level = "WARN" if log_snapshot.get("error") else "INFO"
        runtime.log(
            log_level,
            "Video task "
            f"{task_id} completed: file={log_snapshot['filename']} output={log_snapshot['output_path']} "
            f"warning={log_snapshot['error']}",
        )
    elif stage and stage != log_snapshot["previous_stage"]:
        runtime.log(
            "INFO",
            "Video task "
            f"{task_id} stage={stage} progress={log_snapshot['progress']} file={log_snapshot['filename']}",
        )


def append_task_log(task_manager, task_id, line, limit=80):
    text = str(line or "").rstrip()
    if not text:
        return
    with task_manager.task_lock:
        task = task_manager.task_status.get(task_id)
        if not task:
            return
        details = task.setdefault("details", {})
        logs = details.setdefault("logs", [])
        logs.append(text[-1000:])
        if len(logs) > limit:
            del logs[:-limit]
    runtime.log("DEBUG", f"Video task {task_id} | {text}")


def is_task_cancelled(task_manager, task_id):
    with task_manager.task_lock:
        return task_manager.task_status.get(task_id, {}).get("status") == "cancelled"


def wait_for_process(task_manager, task_id, process, output_lines, stage=None, profile=None):
    cancelled = False
    last_reported_progress = None
    for line in iter(process.stdout.readline, ""):
        if not line:
            break
        output_lines.append(line)
        append_task_log(task_manager, task_id, line)
        if stage == "video_optimize" and profile:
            step_progress = parse_training_progress(line, profile)
            if step_progress is not None and step_progress != last_reported_progress:
                last_reported_progress = step_progress
                update_task(task_manager, task_id, progress=step_progress, stage=stage)
        if is_task_cancelled(task_manager, task_id):
            cancelled = True
            break

    if cancelled:
        terminate_process_tree(process)
        return None, True

    if process.stdout:
        process.stdout.close()
    return process.wait(), False


TRAIN_STEP_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")


def parse_training_progress(line, profile):
    """Map a Nerfstudio "step/total" log line into the optimize progress band.

    Only matches whose denominator equals the configured training iteration
    count are trusted, so unrelated "a/b" tokens in the log do not move the bar.
    Returns an integer percentage within [video_optimize, video_export), or None.
    """
    max_iter = int(profile.get("max_num_iterations") or 0)
    if max_iter <= 0:
        return None

    step = None
    for match in TRAIN_STEP_PATTERN.finditer(line):
        candidate_step = int(match.group(1))
        candidate_total = int(match.group(2))
        if candidate_total == max_iter:
            step = candidate_step

    if step is None:
        return None

    base = STAGE_PROGRESS["video_optimize"]
    ceiling = STAGE_PROGRESS["video_export"]
    ratio = min(1.0, max(0.0, step / max_iter))
    return int(base + (ceiling - base) * ratio)


def terminate_process_tree(process):
    """Terminate the process and its children so GPU workers don't leak.

    ns-train / ns-process-data can spawn child processes (and a viewer); a plain
    process.terminate() only signals the parent, which on Windows leaves orphans
    holding VRAM and can OOM the next queued task. Kill the whole tree instead,
    falling back to single-process terminate/kill if the tree call fails.
    """
    if process.poll() is not None:
        return

    pid = process.pid
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=False,
                capture_output=True,
                timeout=15,
            )
            return
        import signal

        try:
            group_id = os.getpgid(pid)
        except (ProcessLookupError, OSError):
            group_id = None

        if group_id is not None:
            try:
                os.killpg(group_id, signal.SIGTERM)
                process.wait(timeout=5)
                return
            except ProcessLookupError:
                return
            except Exception:
                try:
                    os.killpg(group_id, signal.SIGKILL)
                    return
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback: best-effort single-process termination.
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def run_command(task_manager, task_id, cmd, cwd=None, stage=None, progress=None, profile=None):
    if stage:
        update_task(task_manager, task_id, stage=stage, progress=progress or STAGE_PROGRESS.get(stage, 0))

    process_env = build_video_process_env()
    command_name = Path(str(cmd[0])).name if cmd else "command"

    append_task_log(task_manager, task_id, "$ " + " ".join(str(part) for part in cmd))
    runtime.log(
        "INFO",
        f"Video task {task_id} starting stage={stage or '-'} command={command_name}",
    )
    runtime.log(
        "DEBUG",
        "Video task "
        f"{task_id} command stage={stage or '-'} cwd={cwd or os.getcwd()}: "
        f"{runtime.format_command_for_log(cmd)}",
    )
    popen_kwargs = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=process_env,
        **popen_kwargs,
    )
    with task_manager.task_lock:
        task_manager.running_processes[task_id] = process

    output_lines = []
    try:
        return_code, cancelled = wait_for_process(
            task_manager,
            task_id,
            process,
            output_lines,
            stage=stage,
            profile=profile,
        )
    finally:
        with task_manager.task_lock:
            if task_manager.running_processes.get(task_id) is process:
                task_manager.running_processes.pop(task_id, None)

    if cancelled:
        runtime.log("WARN", f"Video task {task_id} command cancelled stage={stage or '-'}")
    else:
        level = "INFO" if return_code == 0 else "ERROR"
        runtime.log("DEBUG", f"Video task {task_id} command produced {len(output_lines)} output lines stage={stage or '-'}")
        runtime.log(level, f"Video task {task_id} command finished stage={stage or '-'} return_code={return_code}")

    return return_code, output_lines, cancelled


def contains_oom(text):
    normalized = (text or "").lower()
    return any(pattern in normalized for pattern in OOM_PATTERNS)


def build_failure_message(return_code, output_lines):
    output = "".join(output_lines or [])
    tail = "\n".join(output.splitlines()[-24:])
    if contains_oom(output):
        return ERROR_OOM, (
            "GPU memory is not enough for this reconstruction. "
            "Try a lower quality preset, fewer frames, or lower resolution."
        )
    return None, tail or f"Command failed with return code {return_code}"


def clean_job_dir(job_dir, keep):
    if keep:
        return
    try:
        shutil.rmtree(job_dir)
    except OSError:
        pass


def find_exported_ply(export_dir):
    candidates = sorted(Path(export_dir).rglob("*.ply"), key=lambda path: path.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else None


def should_apply_focused_cleanup(task):
    return task.get("mode") != "environment"


def clean_gaussian_splat_ply(source_path, output_path, profile=None):
    import numpy as np
    from plyfile import PlyData, PlyElement

    cleanup_profile = profile or FOCUSED_CLEANUP_PROFILE
    ply = PlyData.read(source_path)
    vertex = ply["vertex"].data
    names = vertex.dtype.names or ()
    required_names = {"x", "y", "z"}
    if not required_names.issubset(names):
        raise ValueError("PLY vertex data is missing x/y/z fields.")

    positions = np.column_stack([vertex["x"], vertex["y"], vertex["z"]]).astype(np.float64, copy=False)
    quantile_min, quantile_max = cleanup_profile["position_quantiles"]
    lower_bounds = np.percentile(positions, quantile_min, axis=0)
    upper_bounds = np.percentile(positions, quantile_max, axis=0)
    position_mask = np.all((positions >= lower_bounds) & (positions <= upper_bounds), axis=1)

    if "opacity" in names:
        opacity = np.asarray(vertex["opacity"], dtype=np.float64)
        alpha = 1.0 / (1.0 + np.exp(-opacity))
    else:
        alpha = np.ones(len(vertex), dtype=np.float64)
    alpha_mask = alpha >= cleanup_profile["alpha_min"]

    scale_names = [name for name in ("scale_0", "scale_1", "scale_2") if name in names]
    if scale_names:
        scales = np.column_stack([vertex[name] for name in scale_names]).astype(np.float64, copy=False)
        max_scale = np.exp(np.max(scales, axis=1))
        scale_limit = float(np.percentile(max_scale, cleanup_profile["scale_quantile"]))
        scale_mask = max_scale <= scale_limit
    else:
        scale_limit = None
        scale_mask = np.ones(len(vertex), dtype=bool)

    mask = position_mask & alpha_mask & scale_mask
    input_vertices = int(len(vertex))
    output_vertices = int(mask.sum())
    keep_ratio = output_vertices / input_vertices if input_vertices else 0.0
    stats = {
        "input_vertices": input_vertices,
        "output_vertices": output_vertices,
        "keep_ratio": keep_ratio,
        "position_quantiles": list(cleanup_profile["position_quantiles"]),
        "alpha_min": cleanup_profile["alpha_min"],
        "scale_quantile": cleanup_profile["scale_quantile"],
        "scale_limit": scale_limit,
        "skipped": False,
    }

    too_small = (
        output_vertices < cleanup_profile["min_vertices"]
        or keep_ratio < cleanup_profile["min_keep_ratio"]
    )
    if too_small:
        shutil.copy2(source_path, output_path)
        stats["output_vertices"] = input_vertices
        stats["keep_ratio"] = 1.0
        stats["skipped"] = True
        stats["reason"] = "cleanup_would_remove_too_much"
        return stats

    cleaned_vertex = vertex[mask].copy()
    PlyData([PlyElement.describe(cleaned_vertex, "vertex")], text=False).write(output_path)
    return stats


def build_process_data_command(source_video_path, data_dir, profile):
    return [
        "ns-process-data",
        "video",
        "--data",
        source_video_path,
        "--output-dir",
        data_dir,
        "--num-frames-target",
        str(profile["frame_count"]),
        "--num-downscales",
        str(profile["num_downscales"]),
        "--matching-method",
        profile["matching_method"],
    ]


def build_train_command(data_dir, output_dir, profile):
    return [
        "ns-train",
        "splatfacto",
        "--output-dir",
        output_dir,
        "--max-num-iterations",
        str(profile["max_num_iterations"]),
        "--viewer.quit-on-train-completion",
        "True",
        "--pipeline.datamanager.train-cameras-sampling-strategy",
        profile["train_cameras_sampling_strategy"],
        "--pipeline.model.camera-optimizer.mode",
        profile["camera_optimizer_mode"],
        "--pipeline.model.num-random",
        str(profile["num_random"]),
        "--pipeline.model.densify-grad-thresh",
        str(profile["densify_grad_thresh"]),
        "--pipeline.model.cull-alpha-thresh",
        str(profile["cull_alpha_thresh"]),
        "--pipeline.model.use-scale-regularization",
        str(profile["use_scale_regularization"]),
        "--pipeline.model.use-bilateral-grid",
        str(profile["use_bilateral_grid"]),
        "--pipeline.datamanager.cache-images",
        profile["cache_images"],
        "nerfstudio-data",
        "--data",
        data_dir,
        "--downscale-factor",
        str(profile["downscale_factor"]),
    ]


def build_export_command(config_path, export_dir):
    return [
        "ns-export",
        "gaussian-splat",
        "--load-config",
        config_path,
        "--output-dir",
        export_dir,
    ]


def find_nerfstudio_config(train_dir):
    candidates = sorted(Path(train_dir).rglob("config.yml"), key=lambda path: path.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else None


def add_object_mode_warning(task):
    details = task.setdefault("details", {})
    warnings = details.setdefault("warnings", [])
    warning = {
        "code": "video_reconstruction_object_foreground_degraded",
        "message": "Automatic foreground segmentation is not configured; object mode will run without masks.",
    }
    if warning not in warnings:
        warnings.append(warning)


def run_video_reconstruction_task(task_manager, task_id, task):
    job_dir = os.path.join(task_manager.paths.video_reconstruction_jobs_folder, task_id)
    source_dir = os.path.join(job_dir, "source")
    data_dir = os.path.join(job_dir, "nerfstudio-data")
    train_dir = os.path.join(job_dir, "train")
    export_dir = os.path.join(job_dir, "export")
    logs_dir = os.path.join(job_dir, "logs")
    keep_intermediate = bool(task.get("keep_intermediate_files"))
    profile = resolve_quality_profile(task.get("quality"), task.get("vram_budget"))
    task.setdefault("details", {})["resource_profile"] = profile

    for folder in (source_dir, data_dir, train_dir, export_dir, logs_dir):
        os.makedirs(folder, exist_ok=True)

    try:
        update_task(
            task_manager,
            task_id,
            status="processing",
            progress=STAGE_PROGRESS["video_prepare"],
            stage="video_prepare",
        )

        if task.get("mode") == "object":
            add_object_mode_warning(task)
            update_task(
                task_manager,
                task_id,
                progress=STAGE_PROGRESS["video_foreground"],
                stage="video_foreground",
            )
            append_task_log(
                task_manager,
                task_id,
                "Automatic foreground segmentation is not configured; continuing without masks.",
            )

        process_cmd = build_process_data_command(task["source_video_path"], data_dir, profile)
        return_code, output_lines, cancelled = run_command(
            task_manager,
            task_id,
            process_cmd,
            cwd=job_dir,
            stage="video_extract_frames",
            progress=STAGE_PROGRESS["video_extract_frames"],
        )
        if cancelled:
            update_task(task_manager, task_id, status="cancelled", error=None)
            clean_job_dir(job_dir, keep_intermediate)
            return
        if is_task_cancelled(task_manager, task_id):
            update_task(task_manager, task_id, status="cancelled", error=None)
            clean_job_dir(job_dir, keep_intermediate)
            return
        if return_code != 0:
            code, message = build_failure_message(return_code, output_lines)
            update_task(task_manager, task_id, status="failed", error=message, error_code=code)
            clean_job_dir(job_dir, keep_intermediate)
            return

        train_cmd = build_train_command(data_dir, train_dir, profile)
        return_code, output_lines, cancelled = run_command(
            task_manager,
            task_id,
            train_cmd,
            cwd=job_dir,
            stage="video_optimize",
            progress=STAGE_PROGRESS["video_optimize"],
            profile=profile,
        )
        if cancelled:
            update_task(task_manager, task_id, status="cancelled", error=None)
            clean_job_dir(job_dir, keep_intermediate)
            return
        if is_task_cancelled(task_manager, task_id):
            update_task(task_manager, task_id, status="cancelled", error=None)
            clean_job_dir(job_dir, keep_intermediate)
            return
        if return_code != 0:
            code, message = build_failure_message(return_code, output_lines)
            update_task(task_manager, task_id, status="failed", error=message, error_code=code)
            clean_job_dir(job_dir, keep_intermediate)
            return

        config_path = find_nerfstudio_config(train_dir)
        if not config_path:
            update_task(
                task_manager,
                task_id,
                status="failed",
                error="Nerfstudio training finished but config.yml was not found.",
                error_code=ERROR_OUTPUT_MISSING,
            )
            clean_job_dir(job_dir, keep_intermediate)
            return

        return_code, output_lines, cancelled = run_command(
            task_manager,
            task_id,
            build_export_command(config_path, export_dir),
            cwd=job_dir,
            stage="video_export",
            progress=STAGE_PROGRESS["video_export"],
        )
        if cancelled:
            update_task(task_manager, task_id, status="cancelled", error=None)
            clean_job_dir(job_dir, keep_intermediate)
            return
        if is_task_cancelled(task_manager, task_id):
            update_task(task_manager, task_id, status="cancelled", error=None)
            clean_job_dir(job_dir, keep_intermediate)
            return
        if return_code != 0:
            code, message = build_failure_message(return_code, output_lines)
            update_task(task_manager, task_id, status="failed", error=message, error_code=code)
            clean_job_dir(job_dir, keep_intermediate)
            return

        exported_ply = find_exported_ply(export_dir)
        if not exported_ply:
            update_task(
                task_manager,
                task_id,
                status="failed",
                error="Nerfstudio export finished but no .ply file was found.",
                error_code=ERROR_OUTPUT_MISSING,
            )
            clean_job_dir(job_dir, keep_intermediate)
            return

        output_ply = exported_ply
        if should_apply_focused_cleanup(task):
            focused_ply = os.path.join(export_dir, "splat-focused.ply")
            try:
                cleanup_stats = clean_gaussian_splat_ply(exported_ply, focused_ply)
                task.setdefault("details", {})["focused_cleanup"] = cleanup_stats
                output_ply = focused_ply
                if cleanup_stats.get("skipped"):
                    append_task_log(task_manager, task_id, "Focused cleanup skipped because it would remove too much geometry.")
                else:
                    append_task_log(
                        task_manager,
                        task_id,
                        (
                            "Focused cleanup kept "
                            f"{cleanup_stats['output_vertices']} / {cleanup_stats['input_vertices']} splats "
                            f"({cleanup_stats['keep_ratio']:.1%})."
                        ),
                    )
            except Exception as exc:
                output_ply = exported_ply
                details = task.setdefault("details", {})
                warnings = details.setdefault("warnings", [])
                warnings.append({
                    "code": "video_reconstruction_cleanup_failed",
                    "message": f"Focused cleanup failed; the raw export was kept. {exc}",
                })
                append_task_log(task_manager, task_id, f"Focused cleanup failed: {exc}")

        os.makedirs(task_manager.paths.output_folder, exist_ok=True)
        shutil.copy2(output_ply, task["output_path"])
        persist_video_model_assets(task_manager.paths, task)

        spz_error = None
        update_task(
            task_manager,
            task_id,
            progress=STAGE_PROGRESS["video_compress_spz"],
            stage="video_compress_spz",
        )
        try:
            task_manager.spz_converter(task["output_path"], task["spz_path"])
        except Exception as exc:
            spz_error = str(exc)
            append_task_log(task_manager, task_id, f"SPZ conversion failed: {spz_error}")

        update_task(
            task_manager,
            task_id,
            status="completed",
            progress=STAGE_PROGRESS["video_done"],
            stage="video_done",
            output_path=task["output_path"],
            spz_path=task["spz_path"] if os.path.exists(task["spz_path"]) else None,
            error=spz_error,
            error_code=ERROR_SPZ_FAILED if spz_error else None,
            completed_at=time.time(),
        )
        clean_job_dir(job_dir, keep_intermediate)
    except Exception as exc:
        if is_task_cancelled(task_manager, task_id):
            update_task(task_manager, task_id, status="cancelled", error=None)
        else:
            error_text = traceback.format_exc()
            runtime.log("ERROR", f"Video task {task_id} exception traceback:\n{error_text}")
            update_task(task_manager, task_id, status="failed", error=error_text)
        clean_job_dir(job_dir, keep_intermediate)
