> 第一验证平台：Windows + NVIDIA RTX 5070 Ti Laptop GPU 12GB。其他平台需真实验证后再写入支持矩阵。
> 合规红线：前馈权重默认不打包、不自动下载受限/gated 权重；项目仅分发集成代码。

## 1. 选型确认与环境准备

- [x] 1.1 最终核对 π³（Pi3）权重许可与其 DINOv2 backbone 许可，记录到 design 备注；若权重受限则确认仍走“用户自行下载”模式或切换 `VGGT-1B-Commercial` 备选。
- [ ] 1.2 在 Windows RTX 5070 Ti Laptop 12GB 上准备 π³ 推理环境（复用 `.video-reconstruction-env` 或独立环境），确认可加载权重并对一组图像跑通前馈推理。（需真实 GPU，第一平台手动验证）
- [x] 1.3 明确 π³ 权重的约定存放目录与配置方式，编写用户自行下载/放置说明（不在安装脚本中默认下载受限权重）。
- [x] 1.4 调研 π³ 输出格式：相机内参、外参（位姿）、点云、坐标轴与尺度约定，记录到 design。

## 2. 前馈推理与位姿导出

- [x] 2.1 实现前馈推理调用模块：输入抽帧目录，输出每帧相机内外参与可选点云，封装子进程或进程内推理与超时/异常处理。
- [x] 2.2 实现前馈位姿 → Nerfstudio `transforms.json` 转换：按 OpenGL/Blender 约定写 c2w 与内参，使 `ns-train` 可用已知位姿跳过 COLMAP。
- [x] 2.3 处理尺度/中心：依赖 Nerfstudio auto-scale 与 center；必要时归一化点云尺度，保证训练稳定。
- [ ] 2.4 校验生成的 `transforms.json` 能被 `ns-train splatfacto`（nerfstudio-data）正常加载并训练。（需真实 GPU，第一平台手动验证）
- [x] 2.5 增加前馈推理失败/无效位姿/显存不足的识别，转换为可本地化错误码并供回退判断。

## 3. 引擎策略与管线集成

- [x] 3.1 扩展 `resolve_engine_strategy`：`auto` 前馈优先、`stable` 仅 COLMAP、`experimental` 强制前馈不可用则拒绝。
- [x] 3.2 在视频重建任务流程中按解析后的引擎分发几何阶段：前馈路线 vs 现有 COLMAP `ns-process-data` 路线。
- [x] 3.3 实现 `auto` 回退：前馈失败/不可用时自动改用 COLMAP 稳定路线重做几何阶段，记录回退原因，任务继续。
- [x] 3.4 复用现有训练、导出、focused cleanup（含 object 聚焦）、SPZ、sidecar、缩略图后段，确保前馈结果与 COLMAP 结果输出契约一致。
- [x] 3.5 为前馈路线接入帧预算/分辨率上限与显存约束，超限时下采样/分块或限制帧数。

## 4. 依赖检测与设置/诊断

- [x] 4.1 扩展视频重建依赖检测：探测前馈推理环境与权重就绪状态，区分 available/missing/checking 并给原因。
- [x] 4.2 将前馈引擎状态纳入设置页视频重建诊断，显示就绪/缺失与“未配置不影响稳定路线”的本地化说明。
- [x] 4.3 任务创建复用依赖缓存判断前馈可用性；`experimental` 不可用时以本地化错误拒绝。

## 5. 前端类型、状态与国际化

- [x] 5.1 前端类型/状态：扩展依赖状态与引擎相关字段以覆盖前馈引擎就绪态。
- [x] 5.2 设置页 UI 展示前馈引擎诊断与说明，遵循现有玻璃态与样式规范。
- [x] 5.3 新增前馈引擎相关用户可见文案，`en.json` 与 `zh.json` 同步。

## 6. 合规与文档

- [x] 6.1 README（中/英）与 `.agents/rules` 记录前馈引擎为可选实验增强、权重需用户自行配置、默认不打包，且第一验证平台为 Windows + RTX 5070 Ti Laptop 12GB。
- [x] 6.2 在设置页或文档明确 π³/DINOv2 许可来源与用户责任，避免分发受限权重。
- [x] 6.3 更新 `design.md` 记录最终选型核对结果、坐标/尺度约定与显存上限实测值。

## 7. 验证与回归

- [x] 7.1 后端测试：引擎策略解析（auto/stable/experimental）、前馈失败回退、依赖检测状态、transforms.json 生成的位姿/内参正确性（合成数据）。
- [x] 7.2 运行 `pytest`、`npm run lint`、`npm run build`、`python -m compileall backend tests`、`openspec validate add-feedforward-reconstruction-engine --strict`、`git diff --check`。
- [ ] 7.3 第一平台手动验证：π³ 路线在真实视频上生成有效位姿并训练导出 `.ply/.spz`，几何阶段耗时显著低于 COLMAP。（需真实 GPU）
- [ ] 7.4 第一平台手动验证：`auto` 在前馈不可用/失败时回退 COLMAP；`experimental` 在权重缺失时以本地化错误拒绝。（需真实 GPU）
- [ ] 7.5 回归：缺权重的干净环境下稳定 COLMAP 路线、图片生成、照片转 3D、视频播放、模型查看不受影响。（需真实 GPU，第一平台手动验证）
- [ ] 7.6 验证前馈生成模型在模型图库、查看器、下载、分享、缩略图、原视频预览与既有视频模型体验一致，且响应不暴露绝对路径。（需真实 GPU，第一平台手动验证）
