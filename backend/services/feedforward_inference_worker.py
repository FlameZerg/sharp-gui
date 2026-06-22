"""π³（Pi3 / Pi3X）前馈推理 worker。

本脚本在视频重建环境的 Python 下作为独立子进程运行（需要 torch + π³ 包 + GPU），
读取一个抽帧目录，输出每帧的相机内外参到 JSON，供后端转换为 Nerfstudio
``transforms.json``。后端模块本身不导入 torch，因此无 GPU 环境也能加载/单测后端。

输出 JSON 协议：
{
  "version": 1,
  "engine": "pi3",
  "frames": [
    {
      "file_name": "frame_00001.png",   # 相对抽帧目录的文件名
      "w": <原图宽>, "h": <原图高>,
      "fl_x": <px>, "fl_y": <px>, "cx": <px>, "cy": <px>,
      "transform_matrix": [[..4x4 c2w, OpenCV 约定..]]
    }, ...
  ]
}

合规：仅当用户已自行下载并通过 ``--ckpt`` 指定本地权重时才加载；脚本绝不联网下载。
"""

import argparse
import json
import os
import sys


def log(message):
    print(f"[pi3-worker] {message}", flush=True)


def list_image_files(images_dir):
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    names = [
        name
        for name in os.listdir(images_dir)
        if os.path.splitext(name)[1].lower() in exts
    ]
    names.sort()
    return names


def subsample(names, max_frames):
    if max_frames <= 0 or len(names) <= max_frames:
        return names
    # 在整段序列上均匀取 max_frames 帧，保持首尾覆盖。
    import numpy as np

    indices = np.linspace(0, len(names) - 1, num=max_frames)
    indices = sorted({int(round(i)) for i in indices})
    return [names[i] for i in indices]


def load_model(checkpoint, device):
    import torch

    model = None
    last_error = None
    # 优先 Pi3X（推荐），回退原始 Pi3。
    for module_name, class_name in (("pi3.models.pi3x", "Pi3X"), ("pi3.models.pi3", "Pi3")):
        try:
            module = __import__(module_name, fromlist=[class_name])
            klass = getattr(module, class_name)
        except Exception as exc:  # noqa: BLE001 - 探测式导入
            last_error = exc
            continue
        try:
            if checkpoint and os.path.isfile(checkpoint):
                model = klass()
                state = _load_state_dict(checkpoint, device)
                model.load_state_dict(state, strict=False)
            else:
                # 无本地权重时不强制联网；交由调用方保证 checkpoint 就绪。
                model = klass.from_pretrained(_default_repo(class_name))
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            model = None
            continue

    if model is None:
        raise RuntimeError(f"Unable to load π³ model: {last_error}")

    return model.to(device).eval()


def _default_repo(class_name):
    return "yyfz233/Pi3X" if class_name == "Pi3X" else "yyfz233/Pi3"


def _load_state_dict(checkpoint, device):
    if checkpoint.endswith(".safetensors"):
        from safetensors.torch import load_file

        return load_file(checkpoint, device="cpu")
    import torch

    state = torch.load(checkpoint, map_location="cpu")
    return state.get("model", state) if isinstance(state, dict) else state


def recover_intrinsics(local_points, conf, proc_w, proc_h):
    """从相机坐标系局部点图按置信度加权最小二乘回归针孔内参。

    ``local_points``: (H, W, 3) numpy；``conf``: (H, W) 概率；返回处理分辨率下的
    (fl_x, fl_y, cx, cy)。
    """
    import numpy as np

    pts = local_points.reshape(-1, 3)
    weights = conf.reshape(-1)
    z = pts[:, 2]
    valid = (z > 1e-6) & np.isfinite(z) & np.isfinite(weights)

    ys, xs = np.mgrid[0:proc_h, 0:proc_w]
    u = xs.reshape(-1).astype(np.float64)
    v = ys.reshape(-1).astype(np.float64)

    valid &= np.isfinite(u) & np.isfinite(v)
    if valid.sum() < 16:
        # 退化时用合理默认：焦距≈max(W,H)，主点居中。
        return float(max(proc_w, proc_h)), float(max(proc_w, proc_h)), proc_w / 2.0, proc_h / 2.0

    x_over_z = pts[valid, 0] / z[valid]
    y_over_z = pts[valid, 1] / z[valid]
    w = np.clip(weights[valid], 1e-3, None)

    fl_x, cx = _weighted_linear_fit(x_over_z, u[valid], w)
    fl_y, cy = _weighted_linear_fit(y_over_z, v[valid], w)

    # 合理性兜底。
    if not (np.isfinite(fl_x) and fl_x > 1e-3):
        fl_x = float(max(proc_w, proc_h))
    if not (np.isfinite(fl_y) and fl_y > 1e-3):
        fl_y = float(max(proc_w, proc_h))
    if not np.isfinite(cx):
        cx = proc_w / 2.0
    if not np.isfinite(cy):
        cy = proc_h / 2.0
    return float(fl_x), float(fl_y), float(cx), float(cy)


def _weighted_linear_fit(a, b, w):
    """加权最小二乘拟合 b ≈ slope * a + intercept，返回 (slope, intercept)。"""
    import numpy as np

    sw = w.sum()
    a_mean = (w * a).sum() / sw
    b_mean = (w * b).sum() / sw
    cov = (w * (a - a_mean) * (b - b_mean)).sum()
    var = (w * (a - a_mean) ** 2).sum()
    if var <= 1e-12:
        return float("nan"), float("nan")
    slope = cov / var
    intercept = b_mean - slope * a_mean
    return slope, intercept


def run(args):
    import numpy as np
    import torch
    from PIL import Image

    names = list_image_files(args.images)
    if not names:
        raise RuntimeError(f"No images found in {args.images}")
    names = subsample(names, args.max_frames)
    log(f"Using {len(names)} frames for feed-forward inference")

    # 原图尺寸（用于把内参缩放回保存帧分辨率）。
    original_sizes = {}
    for name in names:
        with Image.open(os.path.join(args.images, name)) as img:
            original_sizes[name] = img.size  # (W, H)

    device = args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu"
    log(f"Loading π³ model on {device}")
    model = load_model(args.ckpt, device)

    from pi3.utils.basic import load_images_as_tensor

    imgs = load_images_as_tensor(args.images, interval=1)
    # 只取被选中的帧（load_images_as_tensor 读取全目录，按排序对齐）。
    if imgs.shape[0] != len(names):
        all_names = list_image_files(args.images)
        keep = [all_names.index(n) for n in names if n in all_names]
        imgs = imgs[keep]
    imgs = imgs.to(device)
    proc_h, proc_w = int(imgs.shape[-2]), int(imgs.shape[-1])

    dtype = torch.bfloat16 if (device == "cuda" and torch.cuda.get_device_capability()[0] >= 8) else torch.float16
    log("Running model inference...")
    with torch.no_grad():
        if device == "cuda":
            with torch.amp.autocast("cuda", dtype=dtype):
                results = model(imgs[None])
        else:
            results = model(imgs[None])

    poses = results["camera_poses"][0].float().cpu().numpy()        # (N,4,4) OpenCV c2w
    local_points = results["local_points"][0].float().cpu().numpy()  # (N,H,W,3)
    conf_logits = results["conf"][0].float().cpu().numpy()           # (N,H,W,1)
    conf = 1.0 / (1.0 + np.exp(-conf_logits[..., 0]))                # sigmoid -> (N,H,W)

    frames = []
    for index, name in enumerate(names):
        orig_w, orig_h = original_sizes[name]
        fl_x, fl_y, cx, cy = recover_intrinsics(local_points[index], conf[index], proc_w, proc_h)
        # 处理分辨率 -> 保存帧分辨率线性缩放。
        sx = orig_w / float(proc_w)
        sy = orig_h / float(proc_h)
        frames.append({
            "file_name": name,
            "w": int(orig_w),
            "h": int(orig_h),
            "fl_x": fl_x * sx,
            "fl_y": fl_y * sy,
            "cx": cx * sx,
            "cy": cy * sy,
            "transform_matrix": poses[index].tolist(),
        })

    document = {"version": 1, "engine": "pi3", "frames": frames}
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(document, file)
    log(f"Wrote {len(frames)} camera frames to {args.output}")


def main():
    parser = argparse.ArgumentParser(description="π³ feed-forward inference worker")
    parser.add_argument("--images", required=True, help="Directory of extracted frames")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--ckpt", default=None, help="Local model checkpoint (.safetensors)")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-frames", type=int, default=48)
    args = parser.parse_args()
    try:
        run(args)
    except Exception as exc:  # noqa: BLE001 - 顶层兜底，错误信息进 stderr 供回退判断
        log(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
