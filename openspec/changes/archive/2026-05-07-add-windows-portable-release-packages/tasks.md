## 1. 方案固化与资产规范

- [x] 1.1 定义 Windows 便携包资产命名规范，使用 `sharp-gui-<version>-windows-<target>-portable.zip`。
- [x] 1.2 定义包内 `portable-package.json` 与同名 `.sha256.txt`，覆盖版本、目标 GPU、PyTorch/CUDA 信息、SHA256 和兼容说明。
- [x] 1.3 明确首版发布矩阵：`cu128-rtx50`、`cu126-mainstream`，不包含 CPU 包。
- [x] 1.4 生成 `portable-release-template-<version>.md` 作为 Windows 下载说明草案，按 GPU 类型列出网盘链接占位、适用显卡和 SHA256。

## 2. 便携启动与本地校验

- [x] 2.1 新增 Windows 便携入口脚本生成逻辑，包内生成 `portable-run.bat`。
- [x] 2.2 在便携模式下设置包内运行目录、`PATH`、`PYTHONUTF8`、`PYTHONIOENCODING`、`TORCH_HOME` 和 `SHARP_FRONTEND_MODE`。
- [x] 2.3 在 `portable-run.bat` 中增加 PyTorch CUDA 可用性和简单 CUDA kernel smoke test，并提供下载错包或驱动过旧时的提示。
- [x] 2.4 采用完整 ZIP 解压即准备完成的方式，不再需要首次解包 runtime/model 分卷。
- [x] 2.5 便携模式下提供 `sharp.cmd`，确保后端调用 Sharp CLI 时优先使用包内入口。

## 3. 本地打包脚本

- [x] 3.1 新增 Windows 本地打包公开入口 `build_portable_release.bat`，并保留 `tools/build_portable_package.ps1` 作为内部单包构建实现。
- [x] 3.2 打包脚本支持按当前 venv 自动识别 `cu128-rtx50` / `cu128-nvidia` / `cu126-mainstream` 目标。
- [x] 3.3 将 Sharp 模型复制到包内 `.cache\torch\hub\checkpoints` 路径。
- [x] 3.4 对完整包使用 7-Zip ZIP64 压缩，避免 PowerShell `Compress-Archive` 的大文件兼容风险。
- [x] 3.5 自动生成 `portable-package.json` 与 `.sha256.txt`。
- [x] 3.6 新增一键发布入口 `build_portable_release.bat`，默认构建 `cu128-rtx50` 与 `cu126-mainstream` 两个完整包，并生成 Release 网盘链接模板。
- [x] 3.7 增加版本号保护：正式打包必须使用 `-Version vX.Y.Z` 或解析到有效 tag/version，避免误发布 `local-*` 测试包。
- [x] 3.8 增加缓存提示策略：默认保留 `.portable-venvs` 加速缓存和历史旧版本产物，发布完成后打印缓存位置与手动清理命令。
- [x] 3.9 增强前端构建路径：优先复用现有 `node_modules`，绕开 Windows `.bin` shim 权限问题；`npm ci` 失败时回退到兼容当前 lockfile 的安装方式。

## 4. GitHub Release 与网盘发布流程

- [x] 4.1 保留现有 GitHub Release 流程，不上传完整便携大包。
- [x] 4.2 一键脚本生成 Release 网盘链接模板，由维护者在正式发布时补充网盘链接。
- [x] 4.3 在 `commit-and-release` skill 中记录 GitHub Release 正文需要包含中文下载矩阵、网盘链接、最低驱动要求和 SHA256。
- [x] 4.4 记录每次本地打包使用的机器、GPU、PyTorch/CUDA 版本和 smoke test 结果。

## 5. 验证与回归

- [x] 5.1 已在当前 RTX 50 Windows 环境完整生成 `cu128-rtx50` 与 `cu126-mainstream` 两个 `v1.0.7` ZIP。
- [x] 5.2 已对两个 ZIP 执行 7-Zip 完整性测试并生成 SHA256。
- [x] 5.3 已验证 `cu128-rtx50` 包内 Python / PyTorch CUDA 简单 kernel 在 RTX 50 本机可运行。
- [x] 5.4 已验证 `cu126-mainstream` 包在 RTX 50 本机因缺少 `sm_120` kernel 按预期失败，确认不能用一个 cu126 包兼容 RTX 50。
- [x] 5.5 已修复并验证 Windows CMD 启动脚本的编码、换行、百分号和 PATH 拼接问题。
- [x] 5.6 已验证一键打包脚本能够完整产出便携包、SHA256 和 Release 模板。

## 发布前人工验证备注

以下属于每次正式发布前的发布 QA，不作为本次 OpenSpec 变更的未完成实现项：

- 建议在干净 Windows 11 + RTX 50 + 驱动 CUDA 12.8+ 机器上，下载 `cu128-rtx50` 完整 ZIP 后完成一次真实推理。
- 建议在干净 Windows 11 + 非 RTX 50 NVIDIA + 驱动 CUDA 12.6+ 机器上，下载 `cu126-mainstream` 完整 ZIP 后完成一次真实推理。
- 建议在断网环境下验证已下载完整 ZIP 可以启动，并用 `.sha256.txt` 校验下载完整性。
