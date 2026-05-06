## 背景与可行性结论

结论：**如果改用网盘发布，完整单 ZIP 是可行且更适合国内普通用户的。** GitHub Release 只保留版本说明、网盘链接和 SHA256 校验值即可，不再把 GitHub 当作大文件分发渠道。技术重点从“GitHub 托管完整大包”转为“维护者本机一键打包、包内路径可迁移、目标机器一键启动”。

当前仓库状态显示：

- `install.bat` 负责安装 Python / Git、克隆 `ml-sharp`、创建 venv、安装 requirements、修复 PyTorch CUDA wheel、下载模型。
- `tools/install_torch.py` 已经有按驱动 CUDA 版本选择 `cu128` / `cu126` 的基础逻辑，方向是对的。
- `.github/workflows/release.yml` 当前只适合发布源码式 ZIP，不适合承载完整 Windows GPU 运行时与模型。
- 本地 `venv` 约 7.45 GiB，模型 `sharp_2572gikvuh.pt` 约 2.68 GiB；完整包会很大，但用户已明确“大小不用管”，网盘发布可以接受。

外部兼容性依据：

- PyTorch 官方 previous versions 页面提供 `torch==2.8.0` 的 `cu128` 与 `cu126` wheel 安装入口，可对应当前 `tools/install_torch.py` 的版本策略：<https://pytorch.org/get-started/previous-versions/>
- NVIDIA 官方 CUDA GPU 列表把 GeForce RTX 50 系列列为 compute capability 12.0，因此 RTX 50 必须使用包含新架构支持的 PyTorch/CUDA wheel：<https://developer.nvidia.com/cuda-gpus>
- GitHub Release 仍可作为版本说明入口，但大包本体通过网盘发布：<https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases>

## 目标 / 非目标

**目标：**

- 让 Windows 普通用户下载匹配 GPU 的完整 ZIP 后，不再依赖在线 pip/npm/git/模型下载即可启动。
- 以 RTX 50 兼容性作为首要硬件分包约束，避免安装到不支持新架构 kernel 的 PyTorch wheel。
- 保持最大兼容性：不要求用户安装 CUDA Toolkit；只要求 NVIDIA 驱动满足目标包声明的最低 CUDA 运行时能力。
- 本机一键生成完整 ZIP、包说明、包元数据和 SHA256 文件；GitHub Release 正文只贴网盘链接与校验值。
- 保留现有在线安装脚本作为维护和兜底路径。

**非目标：**

- 首版不提供纯 CPU 包。
- 首版不支持 Linux/macOS 便携包。
- 不把 `ml-sharp/` 上游源码改成项目 fork。
- 不承诺在没有 NVIDIA GPU 或驱动过旧的机器上可运行推理。
- 不追求单文件 EXE；体积、可验证性和故障可诊断性优先。

## 推荐发布形态

首版建议维护者本机生成以下完整 ZIP：

- `sharp-gui-vX.Y.Z-windows-cu128-rtx50-portable.zip`：面向 RTX 50 系列，包含 `torch + cu128`、包内 Python、依赖、模型和前端构建产物。
- `sharp-gui-vX.Y.Z-windows-cu126-mainstream-portable.zip`：面向非 RTX 50 的 NVIDIA GPU，包含 `torch + cu126` 对应运行时、模型和完整应用。
- 每个 ZIP 旁边提供同名 `.sha256.txt`，GitHub Release 正文和网盘说明页都贴出校验值。

这样做的好处是用户理解成本最低：下载一个 ZIP，解压，双击 `portable-run.bat`。缺点是 RTX 50 包和 mainstream 包会重复包含模型，网盘占用更大；但用户已经明确“大小不用管”，这个权衡可以接受。

## 关键决策

### 决策：做本地完整 ZIP，而不是 GitHub 自动上传大资产

维护者在本机运行项目根目录的 `build_portable_release.bat` 生成完整 ZIP、SHA256 文件和 Release 网盘链接模板，然后上传到网盘；GitHub Release 正文只放下载链接、适用 GPU、驱动要求和 SHA256。

原因：

- 国内用户从 GitHub 下载超大包体验差，网盘更符合真实分发方式。
- 完整单 ZIP 比多文件分卷更不容易漏下载，也更容易被非技术用户理解。
- SHA256 仍然保留，避免网盘转存或下载过程损坏后难以排查。

考虑过的替代方案：

- GitHub Release 上传完整包：受大小和国内速度限制，不符合当前分发目标。
- 多分卷包：更省单文件大小，但用户容易漏下或不会解压。
- 模型独立包：节省网盘空间，但下载步骤变多；当前阶段优先降低用户操作复杂度。

### 决策：使用维护者本机 Windows 环境生成 Windows 包

Windows 便携包由维护者在已经验证能推理的 Windows x64 环境中生成。打包脚本复制当前 Python 运行时、当前 venv 的 site-packages、`ml-sharp`、模型缓存和前端构建产物，并在包内生成 `portable-run.bat`。

原因：

- Windows PyTorch wheel、entry point、DLL 搜索路径和脚本行为需要在 Windows 上验证。
- 这能保证“打出来的包”与维护者本机已验证环境一致。
- 不需要配置自托管 runner，也不依赖 GitHub-hosted runner 的磁盘空间。

考虑过的替代方案：

- GitHub Actions 自动完整打包：后续可以做，但当前不是必要条件。
- 手动压缩项目目录：容易把日志、证书、用户数据、绝对路径和无关缓存带进包里，因此使用脚本控制 staging 内容。
- PyInstaller 单 EXE：理论上用户体验好，但 PyTorch、CUDA DLL、gsplat 扩展、模型文件和动态库路径会让构建与排错复杂度明显上升。

### 决策：按 PyTorch CUDA wheel 能力分别生成 RTX 50 与非 RTX 50 包

RTX 50 系列应使用 `cu128-rtx50` 包；其他 NVIDIA 用户可使用 `cu126-mainstream` 包。公开的一键脚本默认使用主 `venv` 生成 `cu128-rtx50`，并自动维护 `.portable-venvs\cu126` 打包缓存来生成 `cu126-mainstream`；内部单包脚本仍支持根据当前 venv 的 PyTorch CUDA 版本和本机 GPU 名称推断包名，也允许维护者显式指定目标。

原因：

- RTX 50 属于新架构，必须避免旧 CUDA wheel 缺少目标架构 kernel。
- 当前项目已经在 `tools/install_torch.py` 中按驱动 CUDA 版本选择 `cu128` / `cu126`，可以延续这套判断。
- 不提供 CPU 包时，错误降级到 CPU 反而会掩盖用户下载错包或驱动过旧的问题。

考虑过的替代方案：

- 只提供 `cu128` 一个包覆盖全部 NVIDIA 用户：最简单，但对驱动版本要求更高，可能降低旧驱动用户成功率。
- 自动下载缺失 runtime：会回到网络依赖，不符合完整包目标。
- 首版包含 CPU 包兜底：会增加资产数量和测试矩阵，且用户明确说先不提供 CPU 版本。

## 风险 / 缓解

- [完整 ZIP 体积很大] -> 使用网盘发布；GitHub Release 只贴链接和 SHA256；打包时优先使用 7-Zip ZIP64。
- [不同 GPU 包重复包含模型] -> 接受空间换简单；如果后续网盘空间压力变大，再拆成模型包。
- [Windows runtime 不可迁移] -> 不直接依赖 venv 激活脚本；包内生成 `sharp.cmd`，并在 `portable-run.bat` 中显式设置 `PATH`、`TORCH_HOME` 和 Python 环境变量。
- [RTX 50 包无法覆盖所有驱动状态] -> Release 说明中写清目标包和推荐驱动；至少在一台真实 RTX 50 机器上做 smoke test。
- [用户下载错 GPU 包] -> 首版通过包名和 Release 文档降低误用风险；后续可在 `portable-run.bat` 中增强 `nvidia-smi` 前置校验。
- [模型文件路径仍使用用户 home cache] -> 便携模式设置 `TORCH_HOME` 到包内 `.cache\torch`，避免依赖用户目录和重复下载。

## 最终实现范围

1. 新增根目录公开入口 `build_portable_release.bat`，无参数时生成 `cu128-rtx50` 与 `cu126-mainstream` 两个完整 ZIP。
2. 新增内部单包实现 `tools/build_portable_package.ps1`，生成完整 ZIP、`portable-package.json`、包内说明、`sharp.cmd`、`portable-run.bat` 和 `.sha256.txt`。
3. 新增高层编排脚本 `tools/build_portable_release.ps1`，负责版本号解析与保护、准备 `.portable-venvs\cu126`、调用单包打包、测试 ZIP 完整性、生成 Release 网盘链接模板。
4. Windows 便携入口脚本设置 `PATH` / `PYTHONUTF8` / `PYTHONIOENCODING` / `TORCH_HOME` / `SHARP_FRONTEND_MODE`，并使用包内 Python 启动 `app.py`。
5. 默认保留 `.portable-venvs` 和 `portable-dist` 中的历史旧版本产物，只清理 `.portable-build`；脚本结束时打印缓存位置和手动清理命令。
6. 更新 `commit-and-release` skill，把一键打包、网盘分发、缓存保留、版本号保护和单入口约定写入后续 agent 发布流程。

回滚策略：

- 保留现有 `install.bat` 和源码 ZIP 发布；如果完整便携包失败，可以暂时只在 Release 正文撤下网盘链接，不影响当前在线安装方式。

已完成验证点：

- 本机生成过 `cu128-rtx50` 与 `cu126-mainstream` 两个 `v1.0.7` 完整 ZIP，并生成对应 SHA256 文件。
- 两个 ZIP 均通过 7-Zip 完整性测试。
- 在 RTX 50 本机验证 `cu128-rtx50` 包内 Python / PyTorch CUDA 简单 kernel 可运行。
- 在 RTX 50 本机验证 `cu126-mainstream` 包会因缺少 `sm_120` kernel 按预期失败，确认 RTX 50 不能用 mainstream 包替代。
- 修复过 Windows CMD 便携启动脚本的编码、换行、百分号和 PATH 拼接问题。
- 修复过前端构建在 `npm ci` lockfile 不一致、Windows `.bin` shim 权限问题下的回退路径。

发布前建议验证点：

- 在干净 Windows 11 + RTX 50 + 驱动 CUDA 12.8+ 机器上，下载 `cu128-rtx50` 完整 ZIP 后可启动并完成一次推理。
- 在干净 Windows 11 + 非 RTX 50 NVIDIA + 驱动 CUDA 12.6+ 机器上，下载 `cu126-mainstream` 完整 ZIP 后可启动并完成一次推理。
- 下载损坏时，用户可通过 `.sha256.txt` 发现问题。
- 断网环境下，已下载完整 ZIP 后仍可完成启动和推理。
- GitHub Release 页面能通过网盘链接和 SHA256 复现对应版本。

## 开放问题

- 当前实现已选择 `cu126-mainstream` + `cu128-rtx50` 作为首版最大兼容性矩阵；后续如果目标用户驱动普遍升级，再评估是否增加统一 `cu128` 主流包。
- 是否要在 `portable-run.bat` 中强制校验 RTX 50 / driver CUDA 版本。首版已有 CUDA smoke test，但更友好的“下载错包提示”还可以继续增强。
- 完整 ZIP 建议使用什么网盘和是否需要密码/失效期策略，需要发布流程层面决定。
