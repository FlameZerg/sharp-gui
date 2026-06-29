## Context

Sharp GUI 当前的一键 Windows 完整便携包流程由 `build_portable_release.bat` 进入 `tools/build_portable_release.ps1`，默认生成两个核心包：`cu128-rtx50` 和 `cu126-mainstream`。单包构建脚本会复制应用文件、已构建 React 前端、`ml-sharp`、包内 Python、Python site-packages、Sharp 模型缓存，并生成 `portable-run.bat`、`portable-run-verbose.bat`、`sharp.cmd` 和 `portable-package.json`。

视频 3DGS 重建的稳定路线依赖 `.video-reconstruction-env`、Nerfstudio/Splatfacto/gsplat、COLMAP 和 `ffmpeg/ffprobe`。当前普通安装脚本可以安装或复用该环境，普通 `run.bat` 也会把 `.video-reconstruction-env\Scripts` 和 `.video-reconstruction-env\colmap\bin` 加入 PATH；但现有便携 ZIP 不包含这些依赖。直接复制当前 `.video-reconstruction-env` 也不够安全，因为 `pyvenv.cfg`、`ns-*.exe` launcher 和 `colmap.cmd` 中存在打包机绝对路径。

目标发布版本是 `v1.3.0`。维护者接受复用当前已验证的 Windows + RTX 5070 Ti Laptop GPU / CUDA 12.8 环境作为发布源，但希望原有两个包保持原样，并额外提供一个包含视频重建环境的增强包。

## Goals / Non-Goals

**Goals:**

- 在一键发布流程中新增第三个 Windows RTX 50 视频重建便携包目标。
- 保持 `cu128-rtx50` 和 `cu126-mainstream` 两个核心包的内容、命名和默认用途不变。
- 第三包包含可迁移的视频重建运行时：Nerfstudio/Splatfacto/gsplat、COLMAP、`ffmpeg/ffprobe`。
- 生成相对路径 wrapper，让包移动目录或换 Windows 用户后仍优先使用包内视频重建环境。
- 为第三包写入清晰的 metadata、说明、SHA256 和 Release 模板条目。
- 以 `v1.3.0` 本地打包并校验产物和关键命令。

**Non-Goals:**

- 不为 CPU-only、macOS、Linux、MPS 或非 NVIDIA GPU 提供视频重建完整包。
- 不承诺 RTX 50 以下显卡的视频重建完整包；`cu126-mainstream` 继续作为核心主程序包。
- 不改视频重建算法、质量档、任务队列或 Viewer 行为。
- 不把大型 ZIP 上传到 GitHub Release；仍通过网盘或外部分发链接承载。
- 不重构 OpenSpec 中既有 `add-video-3dgs-reconstruction` 功能 change。

## Decisions

### 决策：第三包作为独立目标，而不是扩充原有两个包

**Why:** 视频重建环境当前约 9GB，且包含 Nerfstudio、COLMAP、CUDA 扩展和 ffmpeg。把它塞进现有两个核心包会显著增加体积、下载成本和风险，也会让只用图片生成的用户被迫下载无关依赖。独立第三包能服务维护者发布和视频重建用户，同时保留核心包稳定性。

**Alternatives considered:**

- 修改 `cu128-rtx50` 直接包含视频环境：下载体积和故障面扩大，且改变已有用户预期。
- 新增 `cu126` 视频包：当前视频重建只在 RTX 50 / CUDA 12.8 路线真实验证过，容易给 RTX 20/30/40 用户过度承诺。
- 继续只提供手动安装：不能满足 `v1.3.0` 发布时“完整便携视频重建包”的目标。

### 决策：复制视频环境后生成相对路径 wrapper

**Why:** Windows venv 的 `pyvenv.cfg`、pip console launcher 和当前 `colmap.cmd` 都可能记录绝对路径。第三包不能只机械复制 `.video-reconstruction-env`，需要在 staging 中生成 `video-recon\Scripts\ns-train.cmd`、`ns-process-data.cmd`、`ns-export.cmd`、`colmap.cmd` 等相对路径入口，由这些 wrapper 调用包内 Python 和包内 COLMAP。

**Alternatives considered:**

- 修补原 `ns-*.exe` 二进制 launcher：实现脆弱，容易受 pip launcher 格式影响。
- 运行时重新安装 Nerfstudio：依赖网络、编译工具和包源，不符合完整便携包定位。
- 要求用户把包解压到原始路径：不可接受，违背便携包契约。

### 决策：把视频环境放在包根 `.video-reconstruction-env`

**Why:** 后端已经会自动把项目根目录下 `.video-reconstruction-env\Scripts` 和 `.video-reconstruction-env\colmap\bin` 加入 PATH，保持相同目录名可以复用现有运行时约定。第三包只需在该目录下增加便携 wrapper，并让 `portable-run.bat` 在启动前显式添加同一组路径。

**Alternatives considered:**

- 放到 `video-recon-runtime\`：命名更清楚，但需要额外改后端自动 PATH 发现逻辑。
- 合并到主 `python\Lib\site-packages`：Nerfstudio 与主程序依赖耦合加深，回滚困难。

### 决策：ffmpeg/ffprobe 使用包内 `tools\ffmpeg\bin`

**Why:** `.video-reconstruction-env` 不一定包含 ffmpeg 可执行文件，当前机器通过系统 PATH 提供 `C:\Tools\ffmpeg\bin`。第三包需要显式复制 `ffmpeg.exe` 和 `ffprobe.exe` 所在目录，避免目标机器依赖系统 PATH。

**Alternatives considered:**

- 只依赖目标机器 PATH：不符合完整视频重建包定位。
- 在包内下载 ffmpeg：增加构建时网络和来源不稳定性；本轮优先复用本机已验证工具。

### 决策：校验分为 ZIP 内容校验和 staging/解压后命令校验

**Why:** 7-Zip `t` 只能证明压缩包结构完整，不能证明视频重建命令可运行。第三包生成后必须额外确认 ZIP 内包含关键路径，并在 staging 或解压目录运行 `torch.cuda`、`ns-process-data --help`、`ns-train --help`、`ns-export --help`、`colmap -h`、`ffmpeg -version`、`ffprobe -version`。

**Alternatives considered:**

- 只依赖后端诊断 API：需要启动服务，适合作为补充但不替代包级命令校验。
- 跑完整视频重建任务：耗时过长，发布前可人工选择性执行，不作为每次一键打包的强制步骤。

## Risks / Trade-offs

- [第三包体积显著增大] -> 保留独立目标和可跳过参数，不影响两个核心包；Release 模板明确区分下载用途。
- [Windows venv 仍可能残留绝对路径] -> 构建后扫描关键文本/launcher，并优先使用相对路径 `.cmd` wrapper；校验命令从包内 PATH 启动。
- [ffmpeg 来源依赖维护者机器] -> 打包时要求 `ffmpeg.exe` 和 `ffprobe.exe` 同时可解析；metadata 记录包内工具位置。
- [RTX 50 以外用户误用第三包] -> 包名、metadata、Release 模板和说明均标注 `cu128-rtx50-video-recon`，并保留 `cu126-mainstream` 为核心包。
- [校验耗时增加] -> 默认只做命令级快速校验，不跑完整重建；保留跳过开关用于排障。

## Migration Plan

1. 更新 OpenSpec 规格和任务。
2. 扩展打包脚本，新增视频重建包目标和 portable wrapper 生成。
3. 使用 `build_portable_release.bat -Version v1.3.0` 生成三个包。
4. 校验 ZIP、SHA256、Release 模板和第三包命令可用性。
5. 如第三包失败，可使用跳过开关仅发布原两个核心包；原两个核心包不依赖本变更新增的视频环境逻辑。

## Open Questions

- 是否将第三包作为每次默认生成目标长期保留，还是仅在 `v1.3.0` 发布阶段默认生成，后续按参数启用。
- 是否需要未来再追加 `cu126-video-recon`，取决于 RTX 20/30/40 上 Nerfstudio/gsplat/COLMAP 的真实验证结果。
