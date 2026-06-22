## Context

视频重建当前稳定路线为 `ns-process-data video`（抽帧 + COLMAP 几何）→ `ns-train splatfacto`（优化）→ `ns-export`（导出 PLY）→ focused cleanup → `ply_to_spz` → 模型图库。实测 high 档（180 帧、30k 迭代）端到端约 1 小时，其中 COLMAP 几何阶段约 14 分钟，且对长视频/弱重叠素材容易因 `sequential`/`exhaustive` 配准断裂而只重建一部分，甚至注册相机过少触发训练崩溃。

前馈式重建（VGGT、DUSt3R/MASt3R、MapAnything、π³ 等）用一次神经网络推理直接回归相机位姿与几何，几何阶段可降到分钟级，并在 COLMAP 易失败场景更稳。由于本项目开源，许可是首要约束：DUSt3R/MASt3R/InstantSplat 为 CC-BY-NC（非商业，排除）；VGGT 默认权重为 Meta 研究许可、商业权重 gated；**π³（Pi3，ICLR 2026）代码为 BSD-3，backbone 为 DINOv2（Apache 2.0），且在相机位姿/深度/点云上为 SOTA**，故选定 π³ 作为首个前馈实验引擎。

引擎策略接口在现有 `resolve_engine_strategy` 中已存在 `auto` / `stable` / `experimental` 三档，`design.md`（add-video-3dgs-reconstruction）早已把“实验引擎 = 前馈几何初始化”作为占位；本变更将其落地为 π³。

## Goals / Non-Goals

**Goals:**

- 引入 π³ 前馈引擎，仅替换 COLMAP 几何阶段，把几何耗时从十几分钟降到分钟级，并提升弱重叠/长视频的配准鲁棒性。
- 完整复用现有稳定路线后段（Nerfstudio 训练、导出、focused cleanup、SPZ、缩略图、sidecar、模型图库）。
- 接入现有引擎策略：`auto` 前馈优先并在失败时回退 COLMAP；`stable` 仍走 COLMAP；`experimental` 强制前馈、不可用则拒绝。
- 严守开源许可：权重默认不打包、不自动下载受限/gated 权重；仅分发集成代码。
- 第一验证平台为 Windows + RTX 5070 Ti Laptop 12GB；通过帧预算/分辨率约束控制显存。
- 不破坏现有图片生成、照片转 3D、视频播放、模型查看与既有 COLMAP 视频重建。

**Non-Goals:**

- 不移除或替换稳定 COLMAP 路线（保留为默认与安全回退）。
- 不默认打包或自动下载受限模型权重。
- 不做动态 4DGS、点云/模型编辑、mesh 重建。
- 不保证 π³ 在所有困难视频（强反光、透明、剧烈运动模糊）上都成功。
- 首版不引入 VGGT/MapAnything；仅以它们为备选记录。

## Decisions

### 决策：选用 π³（Pi3）作为首个前馈引擎

**原因**

- **许可最友好**（开源首要约束）：π³ 代码 BSD-3，backbone DINOv2 为 Apache 2.0，无 DUSt3R 系 CC-BY-NC、无 VGGT 的 Meta 研究/gated 限制。
- **质量 SOTA**：ICLR 2026，相机位姿/深度/点云优于 VGGT；permutation-equivariant，对视频抽帧的无严格顺序输入鲁棒。
- **输出契合**：直接给相机位姿与点云，便于转 Nerfstudio `transforms.json`。

**备选**

- VGGT：最成熟、生态广，但默认权重研究许可、商业权重 gated；作为备选，若 π³ 权重许可或效果不满足可切换 `VGGT-1B-Commercial`（用户自配）。
- MapAnything（Meta，metric 输出）：许可待核实，作为备选。
- DUSt3R/MASt3R/InstantSplat：CC-BY-NC，开源分发不友好，排除。

### 决策：只替换几何阶段，后段完全复用稳定路线

```text
视频 → 抽帧（沿用质量档帧预算）
     → π³ 前馈推理（相机内外参 + 点云）
     → 生成 Nerfstudio transforms.json（含已知位姿，跳过 COLMAP）
     → ns-train splatfacto（nerfstudio-data，使用已知位姿）
     → ns-export → focused cleanup（object 模式聚焦）→ ply_to_spz → 模型图库
```

**原因**

- 改动面最小、风险可控；训练/导出/cleanup/SPZ/sidecar/缩略图全部复用，产物仍是现有 `outputs/*.ply/.spz`。
- Nerfstudio `nerfstudio-data` dataparser 支持读取带位姿的 `transforms.json`，无需重跑 COLMAP。

**备选**

- 走 InstantSplat 式一体化前馈+3DGS 管线：更快但与现有 Nerfstudio 后段割裂，且依赖 NC 许可，排除。
- 用 π³ 点云直接当最终模型：质量不足，仍需 3DGS 优化。

### 决策：引擎策略与自动回退

复用 `resolve_engine_strategy` 的三档语义并强化 `auto`：

```text
auto:        前馈就绪 → 前馈优先；前馈推理失败或不可用 → 自动回退 COLMAP exhaustive 稳定路线
stable:      始终 COLMAP 稳定路线
experimental: 强制前馈；前馈不可用 → 以可本地化错误拒绝创建任务
```

**原因**

- `auto` 给用户“能快就快、不行也能成”的稳妥默认；`experimental` 给高级用户明确入口；`stable` 保底。
- 回退在“前馈推理阶段失败”时触发：若 π³ 推理异常/OOM/位姿无效，记录原因并以 COLMAP 重跑该任务的几何阶段。

**备选**

- 前馈失败直接判任务失败：体验差，放弃。

### 决策：位姿→transforms.json 的坐标与尺度处理

π³ 输出 affine-invariant 相机位姿与 scale-invariant 局部点云（非度量尺度）。生成 `transforms.json` 时按 Nerfstudio OpenGL/Blender 约定（+X 右、+Y 上、-Z 为视线）写入 c2w 矩阵与内参；尺度由 Nerfstudio dataparser 的 `auto_scale_poses` 吸收，几何中心由 `center_method=poses` 归一。

**原因**

- Nerfstudio 训练对尺度/中心不敏感（内部会归一化），无需前馈输出为度量尺度。
- 与现有 object 模式相机环绕聚焦裁剪（基于 `dataparser_transforms.json` 对齐）天然兼容。

**风险点**：内参与畸变约定、坐标轴方向若写错会导致训练发散——需在第一平台用已知视频校验。

### 决策：权重不打包、用户自行配置（开源合规）

```text
默认安装：仅集成代码，无前馈权重
依赖检测：探测 π³ 推理环境与权重是否就绪 → 设置页显示状态
用户配置：用户自行下载 π³（BSD）与 DINOv2（Apache）权重到约定目录并接受其许可
缺失行为：前馈不可用，auto 回退 COLMAP，experimental 拒绝并提示如何配置
```

**原因**

- 沿用 add-video-3dgs-reconstruction 既定原则“实验引擎不默认打包 checkpoint、不自动下载 gated/非商业权重”。
- 项目分发只承载集成代码，权重许可由用户接受，规避开源分发的许可风险。

### 决策：显存与帧预算约束（12GB 第一平台）

前馈 Transformer 一次处理多帧，显存随帧数/分辨率上升。复用现有质量档帧预算与显存预算缩放；为前馈路线设定更保守的“单次推理帧数上限”，超出时分块或下采样；OOM 时记录可本地化建议并回退 COLMAP（`auto`）。

**原因**

- π³/VGGT 量级模型在 12GB 上对大量高分辨率帧易 OOM，需上限保护。

## 选型核对结果（Task 1.1 / 1.4，调研得出，GPU 实测前的结论）

**许可核对（以 Pi3 仓库 2025-12-28 README 为准）**

- 代码（脚本/工具/逻辑）：BSD 3-Clause，允许商业使用。
- **模型权重（Pi3 与 Pi3X）：CC BY-NC 4.0，仅限非商业研究/教育用途**，再分发须保留该限制。
- backbone DINOv2：Apache 2.0。
- 结论：代码可集成分发；**权重受非商业限制，因此严格采用“默认不打包、不自动下载、由用户自行下载并接受 CC BY-NC 4.0”模式**，与既定合规红线一致。商业场景下用户需自行评估 `VGGT-1B-Commercial` 等备选。

**π³ 推理接口与输出格式（README「Model Input & Output」）**

- 输入：`torch.Tensor`，形状 `B×N×3×H×W`，像素值 `[0,1]`。
- 输出 `dict`：
  - `points`：全局点云 `B×N×H×W×3`（由 `local_points` 与 `camera_poses` 反投影得到）。
  - `local_points`：每视图相机坐标系局部点图 `B×N×H×W×3`。
  - `conf`：局部点置信度 logits `B×N×H×W×1`（需 `sigmoid` 取 `[0,1]`，越大越好）。
  - `camera_poses`：相机到世界（c2w）`4×4` 矩阵，**OpenCV 约定**，`B×N×4×4`。
- 加载入口：`Pi3.from_pretrained("yyfz233/Pi3")` 或 `Pi3X.from_pretrained("yyfz233/Pi3X")`（推荐 Pi3X，卷积头点云更平滑、置信度更可靠、支持近似度量尺度）。可用 `--ckpt` 指定本地 `model.safetensors`，规避自动下载。

**坐标/内参换算约定（落地实现采用）**

- π³ 不直接输出内参；由 `local_points`（相机坐标 `x,y,z`）与像素网格 `(u,v)` 按 `u=fx·x/z+cx`、`v=fy·y/z+cy` 用置信度加权最小二乘回归 `fx,fy,cx,cy`，并按「处理分辨率 → 保存帧分辨率」线性缩放。
- OpenCV c2w（+X 右、+Y 下、+Z 视线方向）→ Nerfstudio/OpenGL c2w（+X 右、+Y 上、-Z 视线方向）：`c2w_gl = c2w_cv @ diag(1, -1, -1, 1)`（翻转相机 Y、Z 轴，相机位置与世界系不变）。该约定与现有 `estimate_object_focus` 读取 `transforms.json` 时 `forward = -c2w[:,2]` 的假设一致。
- 尺度/中心：写入 `transforms.json` 后交由 Nerfstudio `nerfstudio-data` dataparser 的 `auto_scale_poses` 与 `center_method=poses` 吸收，前馈输出无需度量尺度。

> 待 GPU 实测确认项（Task 1.2 / 2.4 / 6.3）：π³ 实际处理分辨率与 12GB 单次推理帧数上限、内参回归在真实视频上的精度、`transforms.json` 能否被 `ns-train splatfacto` 直接训练。

## Risks / Trade-offs

- [π³ 权重许可细则未最终确认] -> 实现前到其发布页核对；无论结论如何均采用“用户自行下载、默认不打包”模式；必要时切换 `VGGT-1B-Commercial` 备选。
- [显存 OOM] -> 设前馈单次帧数上限 + 下采样/分块；`auto` 失败回退 COLMAP；记录降质量/降帧建议。
- [坐标/内参约定写错导致训练发散] -> 在第一平台用已验证视频校准 transforms.json；与现有 object 聚焦裁剪共用坐标对齐路径。
- [前馈尺度非度量] -> 依赖 Nerfstudio auto-scale；验证训练稳定与导出正常。
- [新增推理依赖与环境复杂度] -> 依赖检测前置，缺失不影响稳定路线；Windows 环境准备脚本可选、不默认下载权重。
- [前馈对困难素材失败] -> `auto` 回退 COLMAP；文案明确前馈为实验增强，不承诺全成功。
- [破坏既有稳定路线] -> 前馈为新增分支，stable 路径与现有行为保持不变；回退路径复用现有 COLMAP 实现。

## 验证（第一平台：Windows + RTX 5070 Ti Laptop 12GB）

- π³ 在抽帧图像上推理出有效相机位姿，生成的 `transforms.json` 能被 `ns-train splatfacto` 正常训练并导出 `.ply/.spz`。
- 同一视频对比：前馈几何阶段耗时显著低于 COLMAP（目标分钟级 vs ~14 分钟）。
- `auto` 在前馈不可用/失败时正确回退 COLMAP；`experimental` 在权重缺失时以可本地化错误拒绝。
- 前馈生成模型在模型图库、查看器、下载、分享、缩略图、原视频预览均与既有视频模型一致。
- 缺权重的干净环境下，稳定 COLMAP 路线与现有所有能力不受影响。
