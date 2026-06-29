## 1. Packaging Contract

- [x] 1.1 Extend `tools/build_portable_package.ps1` target validation and package naming to support `cu128-rtx50-video-recon`.
- [x] 1.2 Add package metadata fields that distinguish core packages from the video reconstruction package and record bundled video tools.
- [x] 1.3 Keep existing `cu128-rtx50` and `cu126-mainstream` package behavior unchanged unless the video recon target is selected.

## 2. Video Reconstruction Runtime Bundling

- [x] 2.1 Copy `.video-reconstruction-env` into the video recon package staging directory when the target requires it.
- [x] 2.2 Generate relocatable wrapper commands for `ns-process-data`, `ns-train`, `ns-export`, and other Nerfstudio entrypoints used by diagnostics or reconstruction.
- [x] 2.3 Generate a relocatable `colmap.cmd` wrapper that calls package-local COLMAP and preserves the existing argument compatibility mapping.
- [x] 2.4 Copy package-local `ffmpeg.exe` and `ffprobe.exe` into the video recon package and expose them through startup PATH.
- [x] 2.5 Update generated `portable-run.bat` so video recon packages prepend package-local video reconstruction paths before launching `app.py`.

## 3. Release Orchestration

- [x] 3.1 Extend `tools/build_portable_release.ps1` to build the third `cu128-rtx50-video-recon` package by default.
- [x] 3.2 Add a skip switch for the video recon package so maintainers can still build only the two core packages.
- [x] 3.3 Update Release template generation to include RTX 50 core, RTX 50 video reconstruction, and mainstream NVIDIA rows with clear Chinese descriptions.
- [x] 3.4 Ensure SHA256 generation and ZIP integrity testing include the third package.

## 4. Documentation and OpenSpec

- [x] 4.1 Update README download guidance in Chinese and English to mention the optional RTX 50 video reconstruction package without overstating GPU compatibility.
- [x] 4.2 Keep manual video reconstruction setup guidance available for users who do not download the enhanced package.
- [x] 4.3 Validate OpenSpec artifacts for `add-video-recon-portable-bundle`.

## 5. v1.3.0 Build and Verification

- [x] 5.1 Run a plan-only build for `v1.3.0` and confirm the expected three package names.
- [x] 5.2 Build `v1.3.0` packages or, if full rebuild is too slow, build the video recon package plus verify release orchestration logic.
- [x] 5.3 Verify the video recon ZIP contains `.video-reconstruction-env`, package-local COLMAP, package-local ffmpeg/ffprobe, and metadata.
- [x] 5.4 Verify package-local commands: CUDA PyTorch import/kernel, `ns-process-data --help`, `ns-train --help`, `ns-export --help`, `colmap -h`, `ffmpeg -version`, and `ffprobe -version`.
- [x] 5.5 Verify SHA256 files and `portable-release-template-v1.3.0.md` were generated and contain all expected package rows.
