#!/usr/bin/env python3
"""Install and validate the PyTorch build used by Sharp GUI.

The ml-sharp requirements pin torch/torchvision versions. On Windows, pip may
install a CPU build first, and older CUDA wheels can appear usable while missing
kernels for new NVIDIA architectures such as sm_120. This helper runs after the
core requirements and makes the final torch install match the local driver.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass


TORCH_VERSION = "2.8.0"
TORCHVISION_VERSION = "0.23.0"
CUDA_CHOICES = (
    ((12, 8), "cu128"),
    ((12, 6), "cu126"),
)


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    detail: str
    version: str | None = None
    cuda: str | None = None
    device_name: str | None = None
    capability: tuple[int, int] | None = None
    arch_list: tuple[str, ...] = ()


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True)


def driver_cuda_version() -> tuple[int, int] | None:
    try:
        output = subprocess.check_output(
            ["nvidia-smi"], stderr=subprocess.STDOUT, text=True, timeout=15
        )
    except Exception:
        return None
    match = re.search(r"CUDA Version:\s*(\d+)\.(\d+)", output)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def nvidia_gpu_names() -> list[str]:
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15,
        )
    except Exception:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def choose_cuda_index(driver_cuda: tuple[int, int] | None) -> str | None:
    if driver_cuda is None:
        return None
    for minimum, tag in CUDA_CHOICES:
        if driver_cuda >= minimum:
            return tag
    return None


def verify_cuda_runtime() -> VerifyResult:
    try:
        import torch
    except Exception as exc:
        return VerifyResult(False, f"torch import failed: {exc}")

    version = getattr(torch, "__version__", None)
    torch_cuda = getattr(getattr(torch, "version", None), "cuda", None)

    if not torch.cuda.is_available():
        return VerifyResult(
            False,
            "torch.cuda.is_available() is False",
            version=version,
            cuda=torch_cuda,
        )

    try:
        device_name = torch.cuda.get_device_name(0)
        capability = torch.cuda.get_device_capability(0)
        arch_list = tuple(torch.cuda.get_arch_list())
        x = torch.ones((16, 16), device="cuda")
        y = (x @ x).sum()
        torch.cuda.synchronize()
        _ = float(y.cpu())
    except Exception as exc:
        first_line = str(exc).splitlines()[0] if str(exc) else repr(exc)
        return VerifyResult(
            False,
            f"CUDA kernel test failed: {first_line}",
            version=version,
            cuda=torch_cuda,
        )

    return VerifyResult(
        True,
        "CUDA kernel test passed",
        version=version,
        cuda=torch_cuda,
        device_name=device_name,
        capability=capability,
        arch_list=arch_list,
    )


def verify_torch_import() -> bool:
    try:
        import torch

        print(f"[OK] PyTorch import: {torch.__version__}")
        return True
    except Exception as exc:
        print(f"[ERROR] PyTorch import failed: {exc}")
        return False


def pip_install_torch(index_tag: str | None) -> bool:
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        "--no-deps",
        f"torch=={TORCH_VERSION}",
        f"torchvision=={TORCHVISION_VERSION}",
    ]
    if index_tag:
        cmd.extend(["--index-url", f"https://download.pytorch.org/whl/{index_tag}"])
    try:
        run(cmd)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] pip install failed with exit code {exc.returncode}")
        return False


def install_cpu_fallback() -> int:
    print("[INFO] Installing CPU PyTorch fallback.")
    if not pip_install_torch(None):
        return 1
    return 0 if verify_torch_import() else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--cpu-only", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    if args.cpu_only:
        return install_cpu_fallback()

    current = verify_cuda_runtime()
    if current.ok:
        print(
            f"[OK] CUDA PyTorch ready: torch={current.version}, "
            f"cuda={current.cuda}, device={current.device_name}, "
            f"capability={current.capability}, archs={','.join(current.arch_list)}"
        )
        return 0

    print(f"[INFO] Current PyTorch CUDA check: {current.detail}")
    if current.version:
        print(f"[INFO] Current torch={current.version}, cuda={current.cuda}")

    if args.check_only:
        return 1

    gpu_names = nvidia_gpu_names()
    if not gpu_names:
        print("[INFO] No NVIDIA GPU detected. Keeping/installing CPU PyTorch.")
        return install_cpu_fallback()

    print("[INFO] NVIDIA GPU detected: " + "; ".join(gpu_names))
    driver_cuda = driver_cuda_version()
    print(f"[INFO] NVIDIA driver reports CUDA {driver_cuda or 'unknown'}")
    index_tag = choose_cuda_index(driver_cuda)

    if index_tag is None:
        print(
            "[WARN] Driver CUDA is below 12.6 or could not be detected. "
            "Falling back to CPU PyTorch for a reliable install."
        )
        return install_cpu_fallback()

    print(
        f"[INFO] Installing torch {TORCH_VERSION} / "
        f"torchvision {TORCHVISION_VERSION} from {index_tag}."
    )
    if not pip_install_torch(index_tag):
        print("[WARN] CUDA PyTorch install failed; falling back to CPU.")
        return install_cpu_fallback()

    updated = verify_cuda_runtime()
    if updated.ok:
        print(
            f"[OK] CUDA PyTorch verified: torch={updated.version}, "
            f"cuda={updated.cuda}, device={updated.device_name}, "
            f"capability={updated.capability}, archs={','.join(updated.arch_list)}"
        )
        return 0

    print(f"[WARN] CUDA PyTorch installed but failed verification: {updated.detail}")
    print("[WARN] Falling back to CPU PyTorch so inference remains functional.")
    return install_cpu_fallback()


if __name__ == "__main__":
    raise SystemExit(main())
