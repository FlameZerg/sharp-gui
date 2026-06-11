# windows-portable-release-packages Specification

## Purpose

定义 Sharp GUI 在 Windows x64 NVIDIA GPU 环境下的完整便携 ZIP 发布能力，包括本地一键打包、硬件分包、包内运行时路径、校验文件、缓存策略，以及 GitHub Release 通过网盘链接分发大包的说明要求。

## Requirements

### Requirement: Windows Release 必须提供按 GPU 目标区分的完整便携 ZIP 包

Windows Release MUST 提供 Windows x64 GPU 完整便携 ZIP 包的外部下载链接，并按支持的 NVIDIA 运行时目标拆分；便携包路径不得要求普通用户再运行在线依赖安装脚本。

#### Scenario: RTX 50 用户下载匹配包

- **WHEN** 用户使用 RTX 50 系列 GPU
- **THEN** Release 必须链接到 `cu128-rtx50` 完整便携 ZIP
- **AND** 包元数据必须声明该包面向 RTX 50 / CUDA 12.8 兼容驱动

#### Scenario: 非 RTX 50 NVIDIA 用户下载主流包

- **WHEN** 用户使用受支持的非 RTX 50 NVIDIA GPU
- **THEN** Release 必须在该包可用时链接到 `cu126-mainstream` 完整便携 ZIP
- **AND** 包元数据必须声明该包要求的最低驱动 CUDA 能力

#### Scenario: 不提供纯 CPU 包

- **WHEN** 首个 Windows 完整便携包版本列出下载说明
- **THEN** Release 不得把纯 CPU 包作为受支持下载选项展示

### Requirement: 本地打包脚本必须生成完整 ZIP 与校验文件

Windows 便携包流程 MUST 包含本地一键打包脚本，用于生成完整 ZIP、包元数据和 SHA256 校验文件。

#### Scenario: 维护者在本地构建便携包

- **WHEN** 维护者在已验证的 Windows GPU 环境中运行本地打包脚本
- **THEN** 脚本必须构建或验证 React 前端
- **AND** 脚本必须把应用、Python 运行时、Python 依赖、所选前端依赖、`ml-sharp` 源码、模型缓存、便携启动入口和包元数据复制到 staging 目录
- **AND** 脚本必须产出一个用于外部分发的完整 ZIP

#### Scenario: 生成包校验文件

- **WHEN** 完整 ZIP 创建完成
- **THEN** 打包脚本必须为该 ZIP 生成 `.sha256.txt` 文件
- **AND** 该校验值必须适合发布到 GitHub Release 正文和外部网盘说明页

#### Scenario: 打包脚本默认保留有用缓存

- **WHEN** 维护者使用默认选项运行一键发布打包脚本
- **THEN** 脚本必须保留 `.portable-venvs` 等可复用打包缓存
- **AND** 脚本必须保留输出目录中的历史 ZIP 产物
- **AND** 脚本必须在完成后打印缓存位置和手动清理说明

### Requirement: 便携启动器必须使用包内运行时路径

Windows 便携启动器 MUST 使用包内运行时路径启动 Sharp GUI，使启动过程不依赖系统级 Python、Node、Git、pip 网络访问或 CUDA Toolkit。

#### Scenario: 用户启动已解压的便携包

- **WHEN** 用户在解压后的包目录运行 `portable-run.bat`
- **THEN** 启动器必须设置包内 `PATH`、`TORCH_HOME`、`PYTHONUTF8`、`PYTHONIOENCODING` 和 `SHARP_FRONTEND_MODE`
- **AND** 启动器必须使用包内 Python 运行时启动 `app.py`

#### Scenario: 必须提供包内 Sharp CLI

- **WHEN** 后端调用 `sharp` 命令执行推理
- **THEN** 便携包必须提供包内 `sharp.cmd` 入口
- **AND** 该入口必须通过包内 Python 运行时调用 `sharp.cli:main_cli`

### Requirement: 便携运行时必须把模型与缓存数据放在包工作区内

Windows 便携运行时 MUST 使用包内路径保存模型文件和运行缓存，使启动过程不依赖用户 home 目录中的缓存。

#### Scenario: 模型已包含在包资产中

- **WHEN** 完整 ZIP 解压后便携运行时启动
- **THEN** Sharp GUI 必须使用 `.cache\torch\hub\checkpoints` 下的包内模型文件
- **AND** 正常启动时不得尝试重新下载 Sharp 模型

#### Scenario: 用户从另一个 Windows 账号运行

- **WHEN** 包目录被移动到另一个 Windows 用户配置目录
- **THEN** 启动器必须按包目录相对路径解析模型和缓存路径
- **AND** 启动不得要求原始打包机器或原始 Windows 用户配置目录中的文件

### Requirement: GitHub Release 必须用中文说明链接到外部完整 ZIP 包

GitHub Release MUST 提供中文说明和外部下载链接，引导用户下载完整 Windows 便携 ZIP 包，而不是要求 GitHub 直接托管大型 ZIP 文件。

#### Scenario: 外部包发布

- **WHEN** Windows 便携包发布
- **THEN** 维护者必须把完整 ZIP 和匹配的 SHA256 文件上传到外部存储服务
- **AND** GitHub Release 必须链接到这些外部文件

#### Scenario: Release Note 解释下载矩阵

- **WHEN** GitHub Release 创建
- **THEN** Release 正文必须用中文说明 RTX 50 用户和非 RTX 50 NVIDIA 用户分别应该下载哪个完整 ZIP
- **AND** Release 正文必须包含 SHA256 值或 SHA256 文件链接
- **AND** Release 正文必须说明首个便携包版本不包含纯 CPU 模式
