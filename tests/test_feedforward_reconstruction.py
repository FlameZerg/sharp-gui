"""前馈（π³）重建引擎的无 GPU 单测：位姿/内参换算、transforms.json 生成、
依赖探测、引擎策略分发与 auto 回退。GPU 实际推理在第一验证平台手动验证。"""

import json
import os

import numpy as np
import pytest

from backend.paths import build_path_context
from backend.services import feedforward_reconstruction as ff
from backend.services import video_reconstruction
from backend.services.task_queue import TaskManager


def make_video_task(paths, workspace, **overrides):
    source_path = workspace / "album" / "clip.mp4"
    source_path.parent.mkdir(exist_ok=True)
    source_path.write_bytes(b"video")
    task = {
        "id": "video-task",
        "kind": "video_3dgs",
        "filename": "clip.ply",
        "status": "pending",
        "created_at": 1,
        "source_media_id": "album_clip",
        "source_name": "clip.mp4",
        "source_video_path": str(source_path),
        "mode": "auto",
        "quality": "preview",
        "engine": "auto",
        "resolved_engine": "stable",
        "output_name": "clip",
        "output_path": os.path.join(paths.output_folder, "clip.ply"),
        "spz_path": os.path.join(paths.output_folder, "clip.spz"),
        "keep_intermediate_files": False,
        "details": {"warnings": [], "logs": []},
        "error": None,
    }
    task.update(overrides)
    return task


def test_opencv_c2w_to_nerfstudio_flips_y_and_z_axes():
    # 单位矩阵：相机在原点，OpenCV 朝 +Z，OpenGL 应朝 -Z。
    converted = ff.opencv_c2w_to_nerfstudio(np.eye(4).tolist())
    converted = np.asarray(converted)
    # 翻转相机 Y、Z 轴，位置不变，世界系不变。
    assert np.allclose(converted, np.diag([1.0, -1.0, -1.0, 1.0]))

    # 带平移：相机位置（第 4 列）必须保持不变。
    c2w = np.eye(4)
    c2w[:3, 3] = [1.0, 2.0, 3.0]
    out = np.asarray(ff.opencv_c2w_to_nerfstudio(c2w.tolist()))
    assert np.allclose(out[:3, 3], [1.0, 2.0, 3.0])


def test_opencv_c2w_to_nerfstudio_rejects_invalid_matrix():
    with pytest.raises(ff.FeedforwardError) as exc:
        ff.opencv_c2w_to_nerfstudio([[1, 0], [0, 1]])
    assert exc.value.code == ff.ERROR_FEEDFORWARD_INVALID_POSES

    bad = np.eye(4).tolist()
    bad[0][0] = float("nan")
    with pytest.raises(ff.FeedforwardError):
        ff.opencv_c2w_to_nerfstudio(bad)


def _sample_inference_data():
    return {
        "version": 1,
        "engine": "pi3",
        "frames": [
            {
                "file_name": "frame_00001.png",
                "w": 1920,
                "h": 1080,
                "fl_x": 1500.0,
                "fl_y": 1500.0,
                "cx": 960.0,
                "cy": 540.0,
                "transform_matrix": np.eye(4).tolist(),
            },
            {
                "file_name": "frame_00002.png",
                "w": 1920,
                "h": 1080,
                "fl_x": 1500.0,
                "fl_y": 1500.0,
                "cx": 960.0,
                "cy": 540.0,
                "transform_matrix": np.eye(4).tolist(),
            },
        ],
    }


def test_build_transforms_document_uses_nerfstudio_layout():
    document = ff.build_transforms_document(_sample_inference_data())

    assert document["camera_model"] == "OPENCV"
    assert document["w"] == 1920 and document["h"] == 1080
    assert len(document["frames"]) == 2
    first = document["frames"][0]
    assert first["file_path"] == "images/frame_00001.png"
    assert first["fl_x"] == 1500.0 and first["cy"] == 540.0
    # 位姿已转成 OpenGL 约定（OpenCV 单位阵 -> diag(1,-1,-1,1)）。
    assert np.allclose(np.asarray(first["transform_matrix"]), np.diag([1.0, -1.0, -1.0, 1.0]))


def test_build_transforms_document_rejects_invalid_intrinsics():
    data = _sample_inference_data()
    data["frames"][0]["fl_x"] = None
    with pytest.raises(ff.FeedforwardError) as exc:
        ff.build_transforms_document(data)
    assert exc.value.code == ff.ERROR_FEEDFORWARD_INVALID_POSES


def test_build_transforms_document_rejects_empty_frames():
    with pytest.raises(ff.FeedforwardError):
        ff.build_transforms_document({"frames": []})


def test_write_nerfstudio_transforms_roundtrip(tmp_path):
    transforms_path = tmp_path / "data" / "transforms.json"
    count = ff.write_nerfstudio_transforms(_sample_inference_data(), str(transforms_path))
    assert count == 2

    with open(transforms_path, "r", encoding="utf-8") as file:
        document = json.load(file)
    assert document["frames"][1]["file_path"] == "images/frame_00002.png"


def test_parse_inference_output_errors_on_missing_file(tmp_path):
    with pytest.raises(ff.FeedforwardError) as exc:
        ff.parse_inference_output(str(tmp_path / "nope.json"))
    assert exc.value.code == ff.ERROR_FEEDFORWARD_INFERENCE_FAILED


def test_parse_inference_output_errors_on_missing_frames(tmp_path):
    path = tmp_path / "out.json"
    path.write_text(json.dumps({"version": 1, "engine": "pi3"}), encoding="utf-8")
    with pytest.raises(ff.FeedforwardError) as exc:
        ff.parse_inference_output(str(path))
    assert exc.value.code == ff.ERROR_FEEDFORWARD_INVALID_POSES


def test_max_frames_for_budget_uses_conservative_caps():
    assert ff.max_frames_for_budget("8gb") == 24
    assert ff.max_frames_for_budget("12gb") == 48
    assert ff.max_frames_for_budget("unknown") == ff.FEEDFORWARD_FRAME_CAPS["auto"]


def test_detect_feedforward_status_reports_missing_weights(monkeypatch, tmp_path):
    # 引擎包可导入，但权重缺失：应报告 weights 未配置，整体不可用。
    monkeypatch.setattr(ff, "_module_available", lambda *_a, **_k: True)
    monkeypatch.setenv(ff._WEIGHTS_DIR_ENV, str(tmp_path / "empty-weights"))

    status = ff.detect_feedforward_status("python")
    assert status["engine_available"] is True
    assert status["weights_available"] is False
    assert status["available"] is False
    assert status["weights_path"] is None
    # 提示用户自行下载权重。
    assert any(tool["name"] == "pi3-weights" and not tool["available"] for tool in status["tools"])


def test_detect_feedforward_status_ready_when_weights_present(monkeypatch, tmp_path):
    weights_dir = tmp_path / "weights" / "pi3x"
    weights_dir.mkdir(parents=True)
    (weights_dir / "model.safetensors").write_bytes(b"weights")
    monkeypatch.setattr(ff, "_module_available", lambda *_a, **_k: True)
    monkeypatch.setenv(ff._WEIGHTS_DIR_ENV, str(tmp_path / "weights"))

    status = ff.detect_feedforward_status("python")
    assert status["available"] is True
    assert status["weights_path"].endswith("model.safetensors")


def test_build_inference_command_includes_worker_and_checkpoint():
    cmd = ff.build_inference_command(
        "python", "/imgs", "/out.json", "/weights/model.safetensors", max_frames=32, device="cuda"
    )
    assert cmd[0] == "python"
    assert cmd[1].endswith("feedforward_inference_worker.py")
    assert "--ckpt" in cmd and "/weights/model.safetensors" in cmd
    assert cmd[cmd.index("--max-frames") + 1] == "32"


def test_feedforward_geometry_falls_back_to_colmap_on_auto(workspace, monkeypatch):
    """auto 策略下前馈推理失败应自动回退 COLMAP 并继续。"""
    paths = build_path_context({"workspace_folder": str(workspace)})
    task_manager = TaskManager(paths=paths)
    task = make_video_task(
        paths,
        workspace,
        engine="auto",
        resolved_engine="feedforward",
        details={
            "warnings": [],
            "logs": [],
            "dependencies": {"stable": {"available": True}, "experimental": {"available": True}},
        },
    )

    calls = []

    def fake_run_command(_manager, _task_id, cmd, **_kwargs):
        calls.append(cmd[0])
        if cmd[0] == "ffmpeg":
            return 0, [], False
        if cmd[0].endswith("python") or "python" in os.path.basename(cmd[0]):
            # 前馈推理 worker：返回非零模拟失败。
            return 1, ["pi3 boom\n"], False
        if cmd[0] == "ns-process-data":
            data_dir = cmd[cmd.index("--output-dir") + 1]
            os.makedirs(data_dir, exist_ok=True)
            with open(os.path.join(data_dir, "transforms.json"), "w", encoding="utf-8") as file:
                json.dump({"frames": []}, file)
            return 0, [], False
        return 0, [], False

    monkeypatch.setattr("backend.services.video_reconstruction.run_command", fake_run_command)
    monkeypatch.setattr("backend.services.video_reconstruction.probe_video_duration", lambda *_a: 10.0)

    job_dir = os.path.join(paths.video_reconstruction_jobs_folder, task["id"])
    data_dir = os.path.join(job_dir, "nerfstudio-data")
    os.makedirs(data_dir, exist_ok=True)
    profile = video_reconstruction.resolve_quality_profile("preview", "12gb")

    status, code, _message = video_reconstruction.run_geometry_stage(
        task_manager, task["id"], task, job_dir, data_dir, profile
    )

    assert status == "ok"
    assert "ns-process-data" in calls  # 回退到 COLMAP
    assert task["details"]["geometry_fallback"]["to"] == "colmap"
    assert task["details"]["geometry_engine"] == "colmap"


def test_feedforward_geometry_experimental_rejects_without_fallback(workspace, monkeypatch):
    """experimental 策略下前馈失败应直接失败，不回退 COLMAP。"""
    paths = build_path_context({"workspace_folder": str(workspace)})
    task_manager = TaskManager(paths=paths)
    task = make_video_task(
        paths,
        workspace,
        engine="experimental",
        resolved_engine="feedforward",
        details={
            "warnings": [],
            "logs": [],
            "dependencies": {"stable": {"available": True}, "experimental": {"available": True}},
        },
    )

    calls = []

    def fake_run_command(_manager, _task_id, cmd, **_kwargs):
        calls.append(cmd[0])
        if cmd[0] == "ffmpeg":
            return 0, [], False
        # worker 失败（OOM）。
        return 1, ["CUDA out of memory\n"], False

    monkeypatch.setattr("backend.services.video_reconstruction.run_command", fake_run_command)
    monkeypatch.setattr("backend.services.video_reconstruction.probe_video_duration", lambda *_a: 10.0)

    job_dir = os.path.join(paths.video_reconstruction_jobs_folder, task["id"])
    data_dir = os.path.join(job_dir, "nerfstudio-data")
    os.makedirs(data_dir, exist_ok=True)
    profile = video_reconstruction.resolve_quality_profile("preview", "12gb")

    status, code, _message = video_reconstruction.run_geometry_stage(
        task_manager, task["id"], task, job_dir, data_dir, profile
    )

    assert status == "failed"
    assert code == ff.ERROR_FEEDFORWARD_OOM
    assert "ns-process-data" not in calls  # 不回退
