import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from shutil import which

from werkzeug.utils import secure_filename

from backend.config import get_video_reconstruction_config
from backend.services import photo_gallery
from backend.services.static_files import is_real_path_inside

TASK_KIND_VIDEO_3DGS = "video_3dgs"

VALID_RECONSTRUCTION_MODES = {"auto", "object", "environment"}
VALID_RECONSTRUCTION_QUALITIES = {"preview", "high", "extreme"}
VALID_RECONSTRUCTION_ENGINES = {"auto", "stable", "experimental"}
VALID_VRAM_BUDGETS = {"auto", "8gb", "12gb", "16gb", "24gb"}

ERROR_DEPENDENCY_MISSING = "video_reconstruction_dependency_missing"
ERROR_STABLE_UNAVAILABLE = "video_reconstruction_stable_unavailable"
ERROR_EXPERIMENTAL_UNAVAILABLE = "video_reconstruction_experimental_unavailable"
ERROR_INVALID_REQUEST = "video_reconstruction_invalid_request"
ERROR_SOURCE_UNAVAILABLE = "video_reconstruction_source_unavailable"
ERROR_CANCELLED = "video_reconstruction_cancelled"
ERROR_OOM = "video_reconstruction_oom"
ERROR_OUTPUT_MISSING = "video_reconstruction_output_missing"
ERROR_SPZ_FAILED = "video_reconstruction_spz_failed"

QUALITY_PROFILES = {
    "preview": {
        "frame_count": 90,
        "max_resolution": 1280,
        "max_num_iterations": 7000,
        "progress_weight": 0.18,
    },
    "high": {
        "frame_count": 180,
        "max_resolution": 1600,
        "max_num_iterations": 15000,
        "progress_weight": 0.45,
    },
    "extreme": {
        "frame_count": 300,
        "max_resolution": 1920,
        "max_num_iterations": 30000,
        "progress_weight": 0.72,
    },
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


def validate_create_request(data):
    if not isinstance(data, dict):
        data = {}

    video_id = data.get("video_id")
    if not isinstance(video_id, str) or not video_id.strip():
        return None, {
            "error": "video_id is required",
            "code": ERROR_INVALID_REQUEST,
            "field": "video_id",
        }, 400

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
        "video_id": video_id.strip(),
        "mode": mode,
        "quality": quality,
        "engine": engine,
        "vram_budget": config["vram_budget"],
        "output_name": output_name or None,
        "keep_intermediate_files": bool(keep_intermediate_files),
    }, None, 200


def resolve_quality_profile(quality, vram_budget):
    base = QUALITY_PROFILES.get(quality, QUALITY_PROFILES["high"])
    limits = VRAM_PROFILE_LIMITS.get(vram_budget, VRAM_PROFILE_LIMITS["auto"])

    frame_count = max(24, int(round(base["frame_count"] * limits["frame_scale"])))
    max_iterations = max(1000, int(round(base["max_num_iterations"] * limits["iteration_scale"])))
    max_resolution = min(base["max_resolution"], limits["max_resolution_cap"])

    return {
        **base,
        "frame_count": frame_count,
        "max_num_iterations": max_iterations,
        "max_resolution": max_resolution,
        "vram_budget": vram_budget if vram_budget in VRAM_PROFILE_LIMITS else "auto",
    }


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
        result = subprocess.run(
            [command, *(args or ["-version"])],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
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


def python_module_available(module_name):
    try:
        result = subprocess.run(
            ["python", "-c", f"import {module_name}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_dependencies():
    ffmpeg = command_version("ffmpeg")
    ffprobe = command_version("ffprobe")

    ns_process_data = command_version("ns-process-data", ["--help"])
    ns_train = command_version("ns-train", ["--help"])
    ns_export = command_version("ns-export", ["--help"])
    stable_tools = [ns_process_data, ns_train, ns_export]
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
            "message": None if stable_available else "Nerfstudio CLI tools are required for the stable Splatfacto route.",
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
    return task_payload, None, 200


def update_task(task_manager, task_id, **patch):
    with task_manager.task_lock:
        task = task_manager.task_status.get(task_id)
        if task:
            task.update(patch)


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


def is_task_cancelled(task_manager, task_id):
    with task_manager.task_lock:
        return task_manager.task_status.get(task_id, {}).get("status") == "cancelled"


def wait_for_process(task_manager, task_id, process, output_lines):
    cancelled = False
    for line in iter(process.stdout.readline, ""):
        if not line:
            break
        output_lines.append(line)
        append_task_log(task_manager, task_id, line)
        if is_task_cancelled(task_manager, task_id):
            cancelled = True
            break

    if cancelled:
        terminate_process(process)
        return None, True

    if process.stdout:
        process.stdout.close()
    return process.wait(), False


def terminate_process(process):
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def run_command(task_manager, task_id, cmd, cwd=None, stage=None, progress=None):
    if stage:
        update_task(task_manager, task_id, stage=stage, progress=progress or STAGE_PROGRESS.get(stage, 0))

    process_env = os.environ.copy()
    process_env.setdefault("PYTHONUTF8", "1")
    process_env.setdefault("PYTHONIOENCODING", "utf-8")

    append_task_log(task_manager, task_id, "$ " + " ".join(str(part) for part in cmd))
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
    )
    with task_manager.task_lock:
        task_manager.running_processes[task_id] = process

    output_lines = []
    try:
        return_code, cancelled = wait_for_process(task_manager, task_id, process, output_lines)
    finally:
        with task_manager.task_lock:
            if task_manager.running_processes.get(task_id) is process:
                task_manager.running_processes.pop(task_id, None)

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
    ]


def build_train_command(data_dir, output_dir, profile):
    return [
        "ns-train",
        "splatfacto",
        "--data",
        data_dir,
        "--output-dir",
        output_dir,
        "--max-num-iterations",
        str(profile["max_num_iterations"]),
        "--viewer.quit-on-train-completion",
        "True",
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

        os.makedirs(task_manager.paths.output_folder, exist_ok=True)
        shutil.copy2(exported_ply, task["output_path"])

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
            update_task(task_manager, task_id, status="failed", error=str(exc))
        clean_job_dir(job_dir, keep_intermediate)
