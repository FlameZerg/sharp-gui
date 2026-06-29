## Why

当前 Windows 完整便携包已经覆盖主程序、包内 Python、CUDA PyTorch、ml-sharp 和模型缓存，但不包含视频 3DGS 重建所需的 Nerfstudio/Splatfacto、COLMAP、ffmpeg/ffprobe 环境。维护者即将以 `v1.3.0` 发布视频重建能力，需要一个可复用当前已验证环境、同时不扩大原有两个核心包体积和风险的第三个发布包。

## What Changes

- 新增一个 Windows RTX 50 视频重建完整便携包目标，面向已验证的 CUDA 12.8 / RTX 50 路线。
- 保持现有 `cu128-rtx50` 和 `cu126-mainstream` 两个核心便携包的默认内容与适用范围不变。
- 第三个包必须包含可迁移的视频重建运行时，包括 Nerfstudio/Splatfacto/gsplat、COLMAP、ffmpeg/ffprobe，并在启动时按包目录相对路径接入。
- 打包流程必须能用 `v1.3.0` 生成 ZIP、SHA256 和 Release 模板，并校验包内视频重建命令可用。
- 不在本次变更中承诺 Linux/macOS、CPU/MPS、非 NVIDIA 或 RTX 50 以下的视频重建完整环境包。

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `windows-portable-release-packages`: 增加可选的视频重建完整便携包发布矩阵、包内视频重建运行时路径和校验要求。

## Impact

- `tools/build_portable_release.ps1`: 一键发布流程新增第三包目标、参数开关、Release 模板矩阵和校验汇总。
- `tools/build_portable_package.ps1`: 单包构建新增视频重建运行时打包、便携化 wrapper、启动脚本 PATH 接入和包元数据。
- `build_portable_release.bat`: 保持公开入口不变，继续转发到 PowerShell 发布脚本。
- `README.md` / `README.en.md` 或 Release 模板相关说明：发布矩阵需要说明第三包用途、适用显卡和 SHA256。
- `openspec/specs/windows-portable-release-packages`: 更新 Windows 便携包规格，覆盖视频重建包行为。
