import gzip
import math
import os
import struct
from io import BytesIO

import numpy as np
from plyfile import PlyData

SPZ_MAGIC = 1347635022
SPZ_VERSION = 3
SQRT1_2 = 1.0 / math.sqrt(2.0)
QUAT_VALUEMASK = (1 << 9) - 1


def ply_to_splat(ply_path):
    """将 PLY 文件转换为更紧凑的 .splat 格式。"""
    plydata = PlyData.read(ply_path)
    vert = plydata["vertex"]

    sorted_indices = np.argsort(
        -np.exp(vert["scale_0"] + vert["scale_1"] + vert["scale_2"])
        / (1 + np.exp(-vert["opacity"]))
    )

    buffer = BytesIO()
    sh_c0 = 0.28209479177387814

    for idx in sorted_indices:
        v = vert[idx]

        position = np.array([v["x"], v["y"], v["z"]], dtype=np.float32)
        buffer.write(position.tobytes())

        scales = np.exp(np.array([v["scale_0"], v["scale_1"], v["scale_2"]], dtype=np.float32))
        buffer.write(scales.tobytes())

        color = np.array([
            0.5 + sh_c0 * v["f_dc_0"],
            0.5 + sh_c0 * v["f_dc_1"],
            0.5 + sh_c0 * v["f_dc_2"],
            1 / (1 + np.exp(-v["opacity"])),
        ])
        buffer.write((color * 255).clip(0, 255).astype(np.uint8).tobytes())

        rot = np.array([v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]], dtype=np.float32)
        rot_normalized = (rot / np.linalg.norm(rot)) * 128 + 128
        buffer.write(rot_normalized.clip(0, 255).astype(np.uint8).tobytes())

    return buffer.getvalue()


def ply_to_spz(ply_path, spz_path=None, fractional_bits=11):
    """将 PLY 高斯泼溅模型转换为 SPZ 格式 (Niantic v3)。"""
    plydata = PlyData.read(ply_path)
    vert = plydata["vertex"].data
    n = len(vert)

    if spz_path is None:
        spz_path = os.path.splitext(ply_path)[0] + ".spz"

    sh_degree = 0
    scale_factor = 1 << fractional_bits
    sh_c0 = 0.28209479177387814

    header = struct.pack(
        "<IIIBBBB",
        SPZ_MAGIC,
        SPZ_VERSION,
        n,
        sh_degree,
        fractional_bits,
        0,
        0,
    )

    xyz = np.column_stack([
        vert["x"].astype(np.float64),
        vert["y"].astype(np.float64),
        vert["z"].astype(np.float64),
    ])
    quantized = np.round(xyz * scale_factor).astype(np.int32)
    quantized = np.clip(quantized, -(1 << 23) + 1, (1 << 23) - 1)
    unsigned = quantized.astype(np.uint32) & 0xFFFFFF
    b0 = (unsigned & 0xFF).astype(np.uint8)
    b1 = ((unsigned >> 8) & 0xFF).astype(np.uint8)
    b2 = ((unsigned >> 16) & 0xFF).astype(np.uint8)
    centers = np.column_stack([
        b0[:, 0], b1[:, 0], b2[:, 0],
        b0[:, 1], b1[:, 1], b2[:, 1],
        b0[:, 2], b1[:, 2], b2[:, 2],
    ]).flatten().tobytes()

    logits = vert["opacity"].astype(np.float64)
    alphas = 1.0 / (1.0 + np.exp(-np.clip(logits, -20, 20)))
    alpha_bytes = np.round(alphas * 255).clip(0, 255).astype(np.uint8).tobytes()

    colors = np.column_stack([
        0.5 + sh_c0 * vert["f_dc_0"].astype(np.float64),
        0.5 + sh_c0 * vert["f_dc_1"].astype(np.float64),
        0.5 + sh_c0 * vert["f_dc_2"].astype(np.float64),
    ])
    rgb_scale = sh_c0 / 0.15
    rgb_encoded = np.round(((colors - 0.5) / rgb_scale + 0.5) * 255).clip(0, 255).astype(np.uint8)
    rgb_bytes = rgb_encoded.flatten().tobytes()

    log_scales = np.column_stack([
        vert["scale_0"].astype(np.float64),
        vert["scale_1"].astype(np.float64),
        vert["scale_2"].astype(np.float64),
    ])
    scale_encoded = np.round((log_scales + 10.0) * 16.0).clip(0, 255).astype(np.uint8)
    scale_bytes = scale_encoded.flatten().tobytes()

    quats = np.column_stack([
        vert["rot_1"].astype(np.float64),
        vert["rot_2"].astype(np.float64),
        vert["rot_3"].astype(np.float64),
        vert["rot_0"].astype(np.float64),
    ])
    norms = np.linalg.norm(quats, axis=1, keepdims=True)
    norms[norms < 1e-10] = 1.0
    quats /= norms

    quat_packed = np.zeros(n, dtype=np.uint32)
    for i in range(n):
        q = quats[i]
        il = int(np.argmax(np.abs(q)))
        negate = 1 if q[il] < 0 else 0
        comp = il
        for j in range(4):
            if j != il:
                negbit = (1 if q[j] < 0 else 0) ^ negate
                mag = int(QUAT_VALUEMASK * (abs(q[j]) / SQRT1_2) + 0.5)
                mag = min(QUAT_VALUEMASK, mag)
                comp = (comp << 10) | (negbit << 9) | mag
        quat_packed[i] = comp & 0xFFFFFFFF
    quat_bytes = quat_packed.astype("<u4").tobytes()

    raw = header + centers + alpha_bytes + rgb_bytes + scale_bytes + quat_bytes
    compressed = gzip.compress(raw, compresslevel=6)

    with open(spz_path, "wb") as f:
        f.write(compressed)

    return spz_path
