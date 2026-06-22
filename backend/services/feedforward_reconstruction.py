"""前馈（feed-forward）重建引擎集成（π³ / Pi3）。

本模块只负责“几何阶段”的前馈替代：在抽帧目录上调用 π³ 推理，得到每帧
相机内外参，并写出 Nerfstudio `transforms.json`（已知位姿、跳过 COLMAP），
之后完全复用现有 `ns-train`/`ns-export`/cleanup/SPZ 后段。

合规红线：π³ 代码为 BSD-3，但**模型权重为 CC BY-NC 4.0（非商业）**，因此权重
默认不打包、不自动下载，由用户自行下载放置到约定目录并接受其许可。本模块只做
“探测是否就绪”，绝不触发任何下载。

GPU 相关推理在独立 worker 脚本 ``feedforward_inference_worker.py`` 中运行（通过
子进程在视频重建环境的 Python 下执行），本模块的纯逻辑（位姿换算、transforms.json
生成、依赖探测、命令拼装）可在无 GPU 环境单测。
"""

import json
import os
import subprocess
from pathlib import Path

# --- 引擎标识与错误码 -------------------------------------------------------

FEEDFORWARD_ENGINE_LABEL = "pi3"

# π³ 仓库的推理包导入名（用户 clone Pi3 仓库后，其包名为 ``pi3``）。
FEEDFORWARD_MODULE_NAME = "pi3"

# worker 输出 JSON 的协议版本，便于未来演进时做兼容判断。
FEEDFORWARD_OUTPUT_VERSION = 1

ERROR_FEEDFORWARD_UNAVAILABLE = "video_reconstruction_feedforward_unavailable"
ERROR_FEEDFORWARD_WEIGHTS_MISSING = "video_reconstruction_feedforward_weights_missing"
ERROR_FEEDFORWARD_INFERENCE_FAILED = "video_reconstruction_feedforward_inference_failed"
ERROR_FEEDFORWARD_INVALID_POSES = "video_reconstruction_feedforward_invalid_poses"
ERROR_FEEDFORWARD_OOM = "video_reconstruction_feedforward_oom"

# 用户放置权重的约定目录（默认）。可用环境变量覆盖。
_WEIGHTS_DIR_ENV = "SHARP_GUI_FEEDFORWARD_WEIGHTS_DIR"
_DEFAULT_WEIGHTS_DIRNAME = ".feedforward-weights"

# 在约定目录下按优先级查找的权重文件（Pi3X 优先，质量更好）。
_WEIGHTS_CANDIDATES = (
    os.path.join("pi3x", "model.safetensors"),
    os.path.join("pi3", "model.safetensors"),
    "pi3x.safetensors",
    "pi3.safetensors",
    "model.safetensors",
)

# 12GB 第一验证平台为基准的“单次前馈推理帧数上限”，按显存档调整。
# π³/VGGT 量级模型一次性吃所有帧，帧数/分辨率越高越易 OOM，这里给保守上限，
# 超出时由 worker 在帧序列上均匀下采样到该上限。
FEEDFORWARD_FRAME_CAPS = {
    "auto": 48,
    "8gb": 24,
    "12gb": 48,
    "16gb": 64,
    "24gb": 96,
}


class FeedforwardError(Exception):
    """前馈几何阶段的可本地化错误，``code`` 为前端可识别的错误码。"""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def project_root():
    return Path(__file__).resolve().parents[2]


def resolve_weights_dir():
    override = os.environ.get(_WEIGHTS_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return project_root() / _DEFAULT_WEIGHTS_DIRNAME


def resolve_weights_checkpoint():
    """返回已就绪的权重文件路径，找不到则返回 ``None``（绝不触发下载）。"""
    weights_dir = resolve_weights_dir()
    for candidate in _WEIGHTS_CANDIDATES:
        path = weights_dir / candidate
        if path.is_file():
            return str(path)
    # 兜底：目录下任意 .safetensors。
    if weights_dir.is_dir():
        for path in sorted(weights_dir.rglob("*.safetensors")):
            if path.is_file():
                return str(path)
    return None


def _module_available(module_name, python_executable):
    try:
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        result = subprocess.run(
            [python_executable, "-c", f"import {module_name}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        return result.returncode == 0
    except Exception:
        return False


def max_frames_for_budget(vram_budget):
    return FEEDFORWARD_FRAME_CAPS.get(vram_budget, FEEDFORWARD_FRAME_CAPS["auto"])


def detect_feedforward_status(python_executable):
    """探测前馈引擎是否就绪。

    返回结构兼容依赖诊断里的 ``experimental`` 分组：
    ``{available, engine_available, weights_available, weights_path, tools, message}``。
    """
    engine_available = _module_available(FEEDFORWARD_MODULE_NAME, python_executable)
    weights_path = resolve_weights_checkpoint()
    weights_available = weights_path is not None
    available = engine_available and weights_available

    weights_dir = str(resolve_weights_dir())
    engine_tool = {
        "name": "pi3-engine",
        "category": "experimental",
        "required": False,
        "available": engine_available,
        "version": None,
        "message": None
        if engine_available
        else (
            "π³ (Pi3) inference package is not installed in the video reconstruction "
            "environment. Auto will use the stable COLMAP route."
        ),
    }
    weights_tool = {
        "name": "pi3-weights",
        "category": "experimental",
        "required": False,
        "available": weights_available,
        "version": None,
        "message": None
        if weights_available
        else (
            "π³ model weights (CC BY-NC 4.0) are not configured. Download them "
            f"yourself and place them under {weights_dir}."
        ),
    }

    if available:
        message = None
    elif not engine_available:
        message = engine_tool["message"]
    else:
        message = weights_tool["message"]

    return {
        "available": available,
        "engine_available": engine_available,
        "weights_available": weights_available,
        "weights_path": weights_path,
        "weights_dir": weights_dir,
        "tools": [engine_tool, weights_tool],
        "message": message,
    }


# --- 位姿/内参换算与 transforms.json 生成（纯逻辑，可单测） ----------------

# OpenCV c2w -> OpenGL/Blender c2w：翻转相机坐标系的 Y、Z 轴。
_OPENCV_TO_OPENGL = ((1.0, 0.0, 0.0, 0.0),
                     (0.0, -1.0, 0.0, 0.0),
                     (0.0, 0.0, -1.0, 0.0),
                     (0.0, 0.0, 0.0, 1.0))


def opencv_c2w_to_nerfstudio(matrix):
    """把 OpenCV 约定的 4x4 c2w 矩阵转成 Nerfstudio/OpenGL 约定。

    ``matrix`` 为 4x4 的嵌套列表/序列；返回 4 行 4 列的 Python 列表。
    """
    import numpy as np

    c2w = np.asarray(matrix, dtype=np.float64)
    if c2w.shape != (4, 4):
        raise FeedforwardError(
            ERROR_FEEDFORWARD_INVALID_POSES,
            "Feed-forward inference returned a pose that is not a 4x4 matrix.",
        )
    if not np.isfinite(c2w).all():
        raise FeedforwardError(
            ERROR_FEEDFORWARD_INVALID_POSES,
            "Feed-forward inference returned a non-finite camera pose.",
        )
    flip = np.asarray(_OPENCV_TO_OPENGL, dtype=np.float64)
    converted = c2w @ flip
    return converted.tolist()


def build_transforms_document(inference_data):
    """根据 worker 输出构造 Nerfstudio ``transforms.json`` 文档（dict）。

    每帧写入独立内参（π³ 各帧可能不同），并在顶层冗余一份分辨率，OpenCV
    针孔相机模型。``inference_data`` 的结构见 worker 脚本说明。
    """
    frames_in = inference_data.get("frames")
    if not isinstance(frames_in, list) or not frames_in:
        raise FeedforwardError(
            ERROR_FEEDFORWARD_INVALID_POSES,
            "Feed-forward inference did not return any camera frames.",
        )

    out_frames = []
    width = None
    height = None
    for frame in frames_in:
        file_name = frame.get("file_name")
        matrix = frame.get("transform_matrix")
        if not file_name or matrix is None:
            raise FeedforwardError(
                ERROR_FEEDFORWARD_INVALID_POSES,
                "Feed-forward inference returned a frame without a pose or file name.",
            )
        fl_x = frame.get("fl_x")
        fl_y = frame.get("fl_y")
        cx = frame.get("cx")
        cy = frame.get("cy")
        w = int(frame.get("w") or 0)
        h = int(frame.get("h") or 0)
        if not all(isinstance(v, (int, float)) for v in (fl_x, fl_y, cx, cy)) or w <= 0 or h <= 0:
            raise FeedforwardError(
                ERROR_FEEDFORWARD_INVALID_POSES,
                "Feed-forward inference returned invalid camera intrinsics.",
            )
        if width is None:
            width, height = w, h
        out_frames.append({
            "file_path": f"images/{file_name}",
            "fl_x": float(fl_x),
            "fl_y": float(fl_y),
            "cx": float(cx),
            "cy": float(cy),
            "w": w,
            "h": h,
            "transform_matrix": opencv_c2w_to_nerfstudio(matrix),
        })

    document = {
        "camera_model": "OPENCV",
        "w": width,
        "h": height,
        "frames": out_frames,
    }
    return document


def write_nerfstudio_transforms(inference_data, transforms_path):
    """生成并写出 ``transforms.json``，返回写入的帧数。"""
    document = build_transforms_document(inference_data)
    os.makedirs(os.path.dirname(transforms_path) or ".", exist_ok=True)
    with open(transforms_path, "w", encoding="utf-8") as file:
        json.dump(document, file, indent=2)
    return len(document["frames"])


def parse_inference_output(output_json_path):
    """读取并校验 worker 输出 JSON，失败时抛 ``FeedforwardError``。"""
    try:
        with open(output_json_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError) as exc:
        raise FeedforwardError(
            ERROR_FEEDFORWARD_INFERENCE_FAILED,
            f"Feed-forward inference produced no readable output: {exc}",
        )
    if not isinstance(data, dict) or not data.get("frames"):
        raise FeedforwardError(
            ERROR_FEEDFORWARD_INVALID_POSES,
            "Feed-forward inference output is missing camera frames.",
        )
    return data


def build_inference_command(python_executable, images_dir, output_json_path, checkpoint, *, max_frames, device="cuda"):
    """拼装调用 worker 脚本的子进程命令。"""
    worker = str(Path(__file__).resolve().parent / "feedforward_inference_worker.py")
    cmd = [
        python_executable,
        worker,
        "--images",
        str(images_dir),
        "--output",
        str(output_json_path),
        "--device",
        device,
        "--max-frames",
        str(int(max_frames)),
    ]
    if checkpoint:
        cmd += ["--ckpt", str(checkpoint)]
    return cmd
