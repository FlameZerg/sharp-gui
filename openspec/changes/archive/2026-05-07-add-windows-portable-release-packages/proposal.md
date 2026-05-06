## Why / 为什么

Sharp GUI 现在有 Windows 一键安装脚本，但真实 Windows 环境差异过大：Python / Git / PATH / SSL / 国内外网络 / NVIDIA 驱动 / PyTorch CUDA wheel 选择都会影响安装成功率。对普通用户来说，失败点太多，尤其是 RTX 50 系列这类新硬件如果安装到不包含对应 CUDA kernel 的 PyTorch wheel，就会出现“能安装但不能跑”的情况。

因此需要把 Windows 发布形态从“在线安装依赖”升级为“带完整依赖的本地完整 ZIP 包”：维护者在本机运行一键打包脚本，生成适合网盘分发的完整压缩包；用户下载匹配硬件的包后，通过一个入口脚本启动，尽量不依赖目标机器的 Python、Node、Git、pip 网络访问或 CUDA Toolkit。

## What Changes / 变更内容

- 新增 Windows x64 GPU 本地完整包方案，ZIP 中包含应用主体、包内 Python 运行时、Python 依赖、前端依赖、模型文件、校验信息和启动入口。
- 按 NVIDIA GPU / PyTorch CUDA wheel 能力分别在本地打包，至少支持生成 `RTX50 / CUDA 12.8` 与 `其他 NVIDIA / CUDA 12.6+` 两类完整包；首版不提供纯 CPU 包。
- GitHub Release 不上传大包本体，只发布版本说明、网盘链接、SHA256 校验值和下载建议。
- 新增包内 `portable-package.json` 与单 ZIP SHA256 文件，用于维护者和用户核对版本、包类型、CUDA 目标和完整性。
- 新增 Windows 便携启动流程：直接使用包内 Python、包内模型缓存和已构建 React 前端启动 `app.py`。
- 保留现有 `install.bat` 在线安装脚本作为开发者/备用安装方式，不把它作为普通用户 Windows 推荐路径。
- 在发布流程中加入运行时 smoke test：至少验证 Python 导入、Sharp CLI 可调用、模型文件完整性、PyTorch CUDA wheel 元数据与简单 CUDA kernel。

## Capabilities

### New Capabilities

- `windows-portable-release-packages`：定义 Windows x64 GPU 离线/准便携发布包的资产结构、硬件分包策略、校验机制、启动流程和 GitHub Release 网盘分发说明。

### Modified Capabilities

- 无。现有安装脚本与普通源码发布包可保留为备用路径。

## 影响范围

- 发布流程：GitHub Release 正文、Release Note 模板，以及网盘链接维护方式。
- Windows 脚本：新增唯一公开入口 `build_portable_release.bat`，以及包内生成的 `portable-run.bat` / `sharp.cmd`。
- 工具脚本：新增 `tools/build_portable_package.ps1`，复用 `tools/download_model.py` 与当前已验证 venv。
- 文档：Release 网盘链接模板、发布 skill 与 Windows 下载说明草案。
- 不修改 `ml-sharp/` 上游源码；如需适配 Sharp CLI 调用，应在项目外层启动脚本或环境变量层处理。
