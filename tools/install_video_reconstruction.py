#!/usr/bin/env python3
"""Install optional Windows dependencies for video 3DGS reconstruction."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENV_DIR = ROOT / ".video-reconstruction-env"
COLMAP_DIR = ENV_DIR / "colmap"
COLMAP_EXE = COLMAP_DIR / "bin" / "colmap.exe"
COLMAP_WRAPPER = ENV_DIR / "Scripts" / "colmap.cmd"

TORCH_VERSION = "2.8.0"
TORCHVISION_VERSION = "0.23.0"
NERFSTUDIO_VERSION = "1.1.5"
FPSAMPLE_VERSION = "0.3.3"
GSPLAT_VERSION = "1.5.3"
CUDA_TOOLKIT_VERSION = "12.8"
TORCH_CUDA_ARCH_LIST = "12.0"

COLMAP_VERSION = "4.0.4"
COLMAP_ZIP_NAME = "colmap-x64-windows-cuda.zip"
COLMAP_URLS = (
    f"https://github.com/colmap/colmap/releases/download/{COLMAP_VERSION}/{COLMAP_ZIP_NAME}",
    f"https://downloads.sourceforge.net/project/colmap.mirror/{COLMAP_VERSION}/{COLMAP_ZIP_NAME}",
)


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    log("+ " + " ".join(cmd))
    return subprocess.run(cmd, check=True, env=env, text=True, timeout=timeout)


def completed(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int = 30) -> bool:
    try:
        subprocess.run(
            cmd,
            check=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return True
    except Exception:
        return False


def find_existing_path(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def find_vcvars64() -> Path | None:
    return find_existing_path(
        [
            Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"),
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"),
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"),
        ]
    )


def find_cuda_home() -> Path | None:
    configured = os.environ.get("CUDA_HOME") or os.environ.get("CUDA_PATH")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8"),
            Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9"),
        ]
    )
    for candidate in candidates:
        if (candidate / "bin" / "nvcc.exe").exists():
            return candidate
    return None


def read_vcvars_environment() -> dict[str, str]:
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


def winget_exe() -> str:
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError("winget is required to install Visual Studio Build Tools and CUDA Toolkit automatically")
    return winget


def winget_install(args: list[str]) -> None:
    run(
        [
            winget_exe(),
            "install",
            "--accept-source-agreements",
            "--accept-package-agreements",
            *args,
        ],
        timeout=None,
    )


def ensure_visual_cpp_build_tools() -> None:
    vcvars = find_vcvars64()
    if vcvars:
        log(f"[OK] Visual Studio C++ build tools found: {vcvars}")
        return

    log("[INFO] Installing Visual Studio 2022 Build Tools with C++ workload")
    winget_install(
        [
            "--id",
            "Microsoft.VisualStudio.2022.BuildTools",
            "--exact",
            "--override",
            "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended",
        ]
    )

    vcvars = find_vcvars64()
    if not vcvars:
        raise RuntimeError("Visual Studio C++ build tools installation finished, but vcvars64.bat was not found")


def ensure_cuda_toolkit() -> None:
    cuda_home = find_cuda_home()
    if cuda_home:
        log(f"[OK] CUDA Toolkit found: {cuda_home}")
        return

    log(f"[INFO] Installing NVIDIA CUDA Toolkit {CUDA_TOOLKIT_VERSION}")
    winget_install(
        [
            "--id",
            "Nvidia.CUDA",
            "--version",
            CUDA_TOOLKIT_VERSION,
            "--exact",
        ]
    )

    cuda_home = find_cuda_home()
    if not cuda_home:
        raise RuntimeError("CUDA Toolkit installation finished, but nvcc.exe was not found")


def path_env() -> dict[str, str]:
    env = os.environ.copy()
    vc_env = read_vcvars_environment()
    if vc_env:
        env.update(vc_env)
        for key in ("PATH", "Path", "path"):
            if vc_env.get(key):
                env["PATH"] = vc_env[key]
                break

    cuda_home = find_cuda_home()
    if cuda_home:
        env["CUDA_HOME"] = str(cuda_home)
        env["CUDA_PATH"] = str(cuda_home)

    path_parts = [
        str(ENV_DIR / "Scripts"),
        str(COLMAP_DIR / "bin"),
    ]
    if cuda_home:
        path_parts.append(str(cuda_home / "bin"))
    path_parts.append(env.get("PATH", ""))

    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("TORCH_CUDA_ARCH_LIST", TORCH_CUDA_ARCH_LIST)
    env.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    env.setdefault("VSLANG", "1033")
    env["PATH"] = os.pathsep.join(path_parts)
    env["Path"] = env["PATH"]
    return env


def ensure_inside(path: Path, parent: Path) -> None:
    resolved = path.resolve()
    root = parent.resolve()
    if resolved != root and root not in resolved.parents:
        raise RuntimeError(f"Refusing to modify path outside {root}: {resolved}")


def choose_base_python() -> list[str]:
    version = sys.version_info
    if version.major == 3 and 10 <= version.minor <= 12:
        return [sys.executable]

    py_launcher = shutil.which("py")
    if py_launcher:
        for minor in ("3.12", "3.11", "3.10"):
            cmd = [py_launcher, f"-{minor}"]
            if completed([*cmd, "--version"], timeout=10):
                return cmd

    return [sys.executable]


def env_python() -> Path:
    return ENV_DIR / "Scripts" / "python.exe"


def ensure_venv() -> None:
    python_exe = env_python()
    if python_exe.exists():
        log(f"[OK] Video reconstruction venv exists: {ENV_DIR}")
        return

    base_python = choose_base_python()
    log(f"[INFO] Creating video reconstruction venv at {ENV_DIR}")
    run([*base_python, "-m", "venv", str(ENV_DIR)])


def pip_install(args: list[str]) -> None:
    run([str(env_python()), "-m", "pip", "install", *args])


def ensure_python_packages() -> None:
    pip_install(["--upgrade", "pip", "setuptools", "wheel"])

    torch_check = (
        "import torch; "
        "assert torch.__version__.startswith('2.8.0'), torch.__version__; "
        "assert torch.cuda.is_available(); "
        "x=torch.ones((16,16),device='cuda'); y=(x@x).sum(); "
        "torch.cuda.synchronize(); print(torch.__version__, torch.cuda.get_device_name(0))"
    )
    if completed([str(env_python()), "-c", torch_check], timeout=30):
        log("[OK] CUDA PyTorch is already ready")
    else:
        log("[INFO] Installing CUDA PyTorch for RTX 50-series / CUDA 12.8")
        pip_install(
            [
                f"torch=={TORCH_VERSION}",
                f"torchvision=={TORCHVISION_VERSION}",
                "--index-url",
                "https://download.pytorch.org/whl/cu128",
            ]
        )

    ns_train = ENV_DIR / "Scripts" / "ns-train.exe"
    if ns_train.exists() and completed([str(env_python()), "-c", "import nerfstudio"], timeout=30):
        log("[OK] Nerfstudio is already installed")
    else:
        log("[INFO] Installing Nerfstudio / Splatfacto")
        pip_install([f"fpsample=={FPSAMPLE_VERSION}"])
        pip_install([f"nerfstudio=={NERFSTUDIO_VERSION}"])

    gsplat_check = (
        "import gsplat; "
        f"assert getattr(gsplat, '__version__', '') == '{GSPLAT_VERSION}', "
        "getattr(gsplat, '__version__', 'unknown')"
    )
    if completed([str(env_python()), "-c", gsplat_check], timeout=30):
        log(f"[OK] gsplat {GSPLAT_VERSION} is already installed")
    else:
        pip_install([f"gsplat=={GSPLAT_VERSION}"])

    patch_gsplat_windows_build()


def verify_gsplat_cuda_extension() -> None:
    check = (
        "from gsplat.cuda._backend import _C; "
        "assert _C is not None, 'gsplat CUDA extension did not load'; "
        "import torch; "
        "assert torch.cuda.is_available(), 'CUDA is not available to PyTorch'; "
        "print('gsplat CUDA ready on', torch.cuda.get_device_name(0))"
    )
    log("[INFO] Verifying gsplat CUDA extension (first run may compile for several minutes)")
    run([str(env_python()), "-c", check], env=path_env(), timeout=1200)


def clear_gsplat_torch_extension_cache() -> None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return

    cache_root = Path(local_app_data) / "torch_extensions"
    if not cache_root.exists():
        return

    for cache_dir in cache_root.rglob("gsplat_cuda"):
        if cache_dir.is_dir():
            ensure_inside(cache_dir, cache_root)
            shutil.rmtree(cache_dir)
            log(f"[OK] Cleared gsplat build cache: {cache_dir}")


def patch_gsplat_windows_build() -> None:
    if os.name != "nt":
        return

    backend_path = ENV_DIR / "Lib" / "site-packages" / "gsplat" / "cuda" / "_backend.py"
    if not backend_path.exists():
        return

    text = backend_path.read_text(encoding="utf-8")
    old = 'extra_cflags = [opt_level, "-Wno-attributes"]'
    new = 'extra_cflags = [opt_level, "/wd5030"]'
    if old not in text:
        log("[OK] gsplat Windows build flags already patched")
        return

    backend_path.write_text(text.replace(old, new), encoding="utf-8")
    log(f"[OK] Patched gsplat Windows build flags: {backend_path}")
    clear_gsplat_torch_extension_cache()


def download_file(url: str, destination: Path) -> bool:
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl:
        try:
            run([curl, "-L", "--retry", "3", "--retry-delay", "5", "-o", str(destination), url])
            return destination.exists() and destination.stat().st_size > 100 * 1024 * 1024
        except subprocess.CalledProcessError:
            return False

    try:
        log(f"+ download {url}")
        urllib.request.urlretrieve(url, destination)
        return destination.exists() and destination.stat().st_size > 100 * 1024 * 1024
    except Exception as exc:
        log(f"[WARN] Download failed: {exc}")
        return False


def ensure_colmap() -> None:
    if COLMAP_EXE.exists():
        log(f"[OK] COLMAP exists: {COLMAP_EXE}")
        return

    ensure_inside(COLMAP_DIR, ENV_DIR)
    zip_path = Path(os.environ.get("TEMP", str(ROOT))) / f"colmap-{COLMAP_VERSION}-windows-cuda.zip"
    if not zip_path.exists() or zip_path.stat().st_size < 100 * 1024 * 1024:
        for url in COLMAP_URLS:
            log(f"[INFO] Downloading COLMAP from {url}")
            if download_file(url, zip_path):
                break
        else:
            raise RuntimeError("Could not download COLMAP Windows CUDA package")

    if COLMAP_DIR.exists():
        ensure_inside(COLMAP_DIR, ENV_DIR)
        shutil.rmtree(COLMAP_DIR)
    COLMAP_DIR.mkdir(parents=True, exist_ok=True)

    log(f"[INFO] Extracting COLMAP to {COLMAP_DIR}")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(COLMAP_DIR)

    if not COLMAP_EXE.exists():
        candidates = list(COLMAP_DIR.rglob("colmap.exe"))
        raise RuntimeError(f"COLMAP extraction did not produce {COLMAP_EXE}; found {candidates}")


def ensure_colmap_wrapper() -> None:
    real_colmap = str(COLMAP_EXE)
    wrapper = f"""@echo off
setlocal enabledelayedexpansion
set "ARGS="

:loop
if "%~1"=="" goto run
set "ARG=%~1"
if /I "!ARG!"=="--SiftExtraction.use_gpu" set "ARG=--FeatureExtraction.use_gpu"
if /I "!ARG!"=="--SiftMatching.use_gpu" set "ARG=--FeatureMatching.use_gpu"
set ARGS=!ARGS! "!ARG!"
shift
goto loop

:run
"{real_colmap}" !ARGS!
exit /b %ERRORLEVEL%
"""
    COLMAP_WRAPPER.parent.mkdir(parents=True, exist_ok=True)
    COLMAP_WRAPPER.write_text(wrapper, encoding="utf-8", newline="\r\n")
    log(f"[OK] COLMAP compatibility wrapper ready: {COLMAP_WRAPPER}")


def verify_commands() -> None:
    env = path_env()
    checks = [
        ([str(ENV_DIR / "Scripts" / "ns-process-data.exe"), "--help"], 45),
        ([str(ENV_DIR / "Scripts" / "ns-train.exe"), "--help"], 45),
        ([str(ENV_DIR / "Scripts" / "ns-export.exe"), "--help"], 45),
        ([str(COLMAP_EXE), "-h"], 15),
    ]
    for cmd, timeout in checks:
        if not completed(cmd, env=env, timeout=timeout):
            raise RuntimeError(f"Command validation failed: {' '.join(cmd)}")
    log("[OK] Video reconstruction commands are ready")


def main() -> int:
    if os.name != "nt":
        log("[INFO] This helper currently targets Windows only; skipping.")
        return 0

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    ensure_venv()
    ensure_visual_cpp_build_tools()
    ensure_cuda_toolkit()
    ensure_python_packages()
    ensure_colmap()
    ensure_colmap_wrapper()
    verify_commands()
    verify_gsplat_cuda_extension()

    log("")
    log("[OK] Video reconstruction environment installed")
    log(f"     Nerfstudio: {ENV_DIR / 'Scripts'}")
    log(f"     COLMAP:     {COLMAP_DIR / 'bin'}")
    log(f"     CUDA:       {find_cuda_home()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
