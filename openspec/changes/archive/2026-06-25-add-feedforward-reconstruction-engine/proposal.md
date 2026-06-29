> **状态：已废弃（2026-06-24）**
>
> 本变更仅作为前馈式重建探索记录保留，不再进入当前产品实现。废弃原因：在目标 Windows + RTX 5070 Ti Laptop 12GB 环境验证中，Pi3/Pi3X 路线对多帧一次性推理的显存压力过高并出现 OOM；降低帧数后的 smoke 产物质量异常，无法达到稳定路线的可验收效果；长视频场景需要覆盖足够视角，当前方案的帧预算与质量目标矛盾；同时权重许可/分发要求不适合作为默认能力。当前分支回到已验证的 COLMAP + Nerfstudio/Splatfacto 稳定路线。

## Why

当前视频重建的几何阶段依赖 COLMAP（`ns-process-data`），对一段普通视频常耗时十几分钟，且对长视频/弱重叠素材容易配准断裂（只重建前半段、相机过少甚至训练崩溃）。前馈式（feed-forward）重建用一次神经网络推理直接得到相机位姿与几何，可把几何阶段从十几分钟压到分钟级，并在 COLMAP 易失败的场景更稳。本变更引入一个许可友好的前馈引擎作为可选实验路线，在不破坏现有稳定 COLMAP 路线的前提下显著提速并提升鲁棒性。

## What Changes

- 新增前馈重建引擎（π³ / Pi3，BSD-3 代码 + DINOv2/Apache backbone）作为视频重建的实验路线：从抽帧后的图像前馈推理出相机位姿（及点云），替换最慢的 COLMAP 几何阶段。
- 复用现有稳定路线后段：前馈位姿写入 Nerfstudio `transforms.json`（已知位姿、跳过 COLMAP），继续走 `ns-train splatfacto` 训练、导出、focused cleanup、SPZ 压缩与模型图库集成。
- 接入现有引擎策略语义：`auto` 优先用前馈、失败或不可用时自动回退 COLMAP 稳定路线；`stable` 仍走 COLMAP；`experimental` 强制前馈、不可用则拒绝创建任务。
- 扩展依赖检测：识别前馈引擎与其权重是否就绪，在设置页与任务错误中给出明确状态；缺失时不影响稳定路线。
- 合规：前馈模型权重**默认不打包、不自动下载**，由用户自行下载配置并接受其许可；项目仅分发集成代码。
- 第一验证平台：Windows + NVIDIA RTX 5070 Ti Laptop GPU 12GB；其他平台需真实验证后再写入支持矩阵。
- 不改变现有图片生成、照片转 3D、视频播放、模型查看与既有 COLMAP 视频重建行为。

首版明确不做：

- 不删除或替换稳定 COLMAP 路线（保留为默认与回退）。
- 不默认打包或自动下载受限/gated 模型权重。
- 不做动态 4DGS、点云编辑、模型裁剪编辑器。
- 不承诺前馈引擎在所有困难视频上都成功。

## Capabilities

### New Capabilities
- `feedforward-reconstruction-engine`: 定义将前馈式相机位姿/几何推理作为视频重建实验引擎的完整能力，包括引擎检测与就绪状态、前馈推理产出位姿、与现有 Nerfstudio 训练管线的对接（已知位姿、跳过 COLMAP）、引擎策略与自动回退、显存与帧预算约束、权重许可合规与不打包策略，以及失败处理。

### Modified Capabilities
<!-- 现有 video-3dgs-reconstruction 能力尚未归档到 openspec/specs/，本变更以新增能力形式扩展其引擎选择，不在此声明 spec 级修改。 -->

## Impact

后端影响：

- `backend/services/video_reconstruction.py`：新增前馈引擎依赖检测、前馈推理调用、位姿→`transforms.json` 生成、引擎分发（前馈 vs COLMAP）与回退逻辑；复用现有训练/导出/cleanup/SPZ 后段。
- 引擎策略 `resolve_engine_strategy`：把“实验路线”从占位落地为前馈引擎；`auto` 增加“前馈优先、失败回退 COLMAP”。
- 依赖诊断 API 与设置响应：暴露前馈引擎与权重就绪状态。
- `backend/security/access_control.py`：沿用现有生成权限矩阵，无新增公开端点权限放宽。

前端影响：

- 设置页视频重建诊断：增加前馈引擎就绪状态与“未配置时回退稳定路线”说明。
- i18n：新增前馈引擎相关用户可见文案，中英文同步。

运行依赖与合规影响：

- 新增可选前馈推理依赖（π³ 及其 DINOv2 backbone），由用户自行配置；默认安装不包含权重。
- 安装/运行脚本（Windows）可选支持准备前馈环境，但不得默认下载受限权重。

数据与兼容性影响：

- 前馈引擎仅替换几何阶段，最终产物仍为现有 `outputs/*.ply` / `.spz`，模型图库、查看器、下载、分享路径不变。
- 中间文件写入现有 workspace 派生目录，不污染源视频与 `inputs/`。
