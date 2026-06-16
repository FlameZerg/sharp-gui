## 背景

Sharp GUI 当前有三条已经成型的能力边界：

1. **单图生成模型**：前端通过 `/api/generate` 上传图片，后端 `TaskManager` 调用 `sharp predict -i <input> -o <outputs>`，完成后检查同名 `.ply` 并自动转 `.spz`。
2. **本地媒体图库**：用户可以配置本机/NAS 相册，浏览照片和视频。照片可以通过 `photo-conversions` 复制到 `inputs/` 并进入现有 SHARP 队列；视频目前只能预览、下载，不能转 3D。
3. **模型图库与查看器**：模型图库扫描 `outputs/*.ply`，如果有同名 `.spz` 则优先作为紧凑模型源；Spark Viewer 已支持 PLY/SPZ 等格式。

本变更要新增的是视频重建管线，但产品上不应该成为一个孤立工具。最自然的用户路径是：

```text
本地媒体图库中的视频
    │
    ├─ 选择栏：生成 3D
    └─ 视频预览：生成 3D
          │
          ▼
    选择模式和质量
          │
          ▼
    进入现有任务队列
          │
          ▼
    输出 .ply/.spz 到 outputs/
          │
          ▼
    出现在现有模型图库，用 Spark Viewer 打开
```

从技术上看，物品视频和环境视频都属于“视频到静态 3DGS”的大类，但不应被当作完全相同的输入：

- **物品视频**通常要求前景主体干净、居中、可从背景中分离；转台视频尤其不能简单按“静态环境 + 相机移动”处理。
- **环境视频**通常要求相机在空间中移动并产生视差，重点是全画面的相机位姿、稀疏几何和大场景训练。

所以产品入口保持一个，底层策略允许按 `自动 / 物品 / 环境` 分流。

## 目标 / 非目标

**目标：**

- 从单个本地视频自动生成一个静态 3DGS 模型，最终产物是现有模型图库可识别的 `.ply/.spz`。
- 入口无缝接入本地媒体图库和视频预览，不新增割裂的主导航视图。
- 用户只需要选择简单的模式和质量档位，不需要手动抽帧、手动跑 COLMAP、手工删除点云或修剪模型。
- 默认方案优先保证稳定可落地，能在 12GB 显存笔记本 GPU 上通过帧预算和质量档位控制资源使用。
- 保留前沿增强空间：VGGT/VGGT-Omega 等初始化路线可以作为实验引擎，但不得阻塞稳定路线。
- 所有新增 UI 延续现有 Apple 玻璃态、CSS Modules、CSS Variables、双语 i18n 和触控可达规范。
- 不破坏现有 SHARP 单图生成、照片转 3D、视频预览、模型图库和 Spark Viewer。

**非目标：**

- 不实现动态 4DGS、动态人物/车辆重建或时间维度播放。
- 不实现模型编辑器、点云编辑、手工裁剪、手工分割、mesh 修补或 retopology。
- 不修改 `ml-sharp/`、`static/lib/`、legacy `templates/index.html`。
- 不引入云端处理、账号登录、远程 GPU 调度或多机训练。
- 不保证所有视频都能成功；困难材质、运动模糊、无纹理墙面、强反光、透明物体等仍需要失败提示和拍摄建议。

## 技术决策

### 决策：使用“一个入口、两类场景策略、统一输出”的产品模型

用户只看到一个主要动作：“从视频生成 3D”。开始前通过轻量弹窗选择：

```text
模式：自动 / 物品 / 环境
质量：快速预览 / 高质量 / 极致
输出名称：默认从视频文件名派生，可编辑
高级：引擎策略、保留中间文件、帧预算（可折叠）
```

**原因**

- 入口过多会破坏现有媒体图库的简洁性。
- 用户通常知道自己拍的是物品还是环境，但不应被迫理解底层管线。
- 统一输出 `.ply/.spz` 可以最大化复用现有模型图库和查看器。

**备选方案**

- 新增第三个主视图“重建中心”：空间更大，但会让用户先导入/选择视频两次，和当前 `models/photos` 视图结构不一致。
- 分成“物品扫描”和“环境扫描”两个按钮：概念更清晰，但按钮膨胀，移动端选择栏会拥挤。
- 完全隐藏模式选择：交互最简单，但自动判断失败时用户缺少纠错入口。

### 决策：默认稳定路线采用优化式 3DGS 管线，实验路线只做增强

稳定默认路线：

```text
视频
  → ffprobe/ffmpeg 读取元数据和抽帧
  → 关键帧筛选和质量过滤
  → Nerfstudio ns-process-data video 数据处理
  → Nerfstudio ns-train splatfacto 优化
  → Nerfstudio ns-export gaussian-splat 导出 Gaussian Splat .ply
  → 现有 ply_to_spz 压缩
  → 模型图库刷新
```

首版稳定实现目标已确定为 Nerfstudio/Splatfacto CLI 路线：`ns-process-data video`、`ns-train splatfacto`、`ns-export gaussian-splat`。COLMAP/hloc 作为 Nerfstudio 数据处理链路中的底层能力或后续替代方案，不作为首版单独 UI 选项暴露。

实验增强路线：

```text
视频关键帧
  → VGGT / VGGT-Omega 等前馈几何模型估计相机、深度或点云
  → 作为初始化或预处理结果进入 3DGS 优化
```

**原因**

- “效果好且基本可用”更依赖逐场景优化，而不是纯一次前馈。
- Nerfstudio/Splatfacto/gsplat 类路线能导出标准 `.ply`，和当前项目契约贴合。
- VGGT-Omega 等方法很前沿，但可能涉及 gated checkpoint、非商业许可或安装复杂度，不适合作为公开默认必需依赖。

**备选方案**

- 纯前馈视频到 3D：速度快、体验好，但当前更适合预览/初始化，最终质量和稳定性难以覆盖用户要求。
- Mesh-first photogrammetry：成熟但和当前 Gaussian Splat Viewer/分享链路不一致，还会引入网格纹理和查看器适配问题。
- 继续用 SHARP 逐帧生成再融合：SHARP 是单图近视角合成模型，不是多视角视频重建框架，无法直接得到一致的大场景 3DGS。

### 决策：任务系统增加 task kind，而不是新建完全独立队列

当前 `TaskManager` 假设每个任务都有 `input_path`、`filename`，并固定调用 `sharp predict`。视频任务需要引入 `kind`，例如：

```text
image_sharp    现有图片/照片转 3D
video_3dgs     新增视频重建
```

任务数据需要兼容现有前端字段：

```text
id
filename
status
progress
stage
error
created_at
```

同时新增可选字段：

```text
kind
source_media_id
mode
quality
engine
output_name
details
```

**原因**

- 复用现有任务轮询、取消、完成后刷新图库、内存保留清理。
- 单队列默认串行，适合保护 12GB 显存机器，避免多个 GPU-heavy 任务同时 OOM。
- 将任务分发抽象出来后，后续可继续支持其他生成引擎。

**备选方案**

- 新建 `VideoTaskManager`：隔离更强，但重复队列、取消、状态 API 和前端轮询逻辑。
- 在现有 worker 里用文件扩展名判断视频：实现快但脆弱，无法表达模式、质量、引擎和依赖错误。

### 决策：中间文件只放 workspace 派生目录，最终文件仍进 outputs

建议新增 workspace 派生目录：

```text
{workspace}/.video-reconstruction/
  jobs/<task_id>/
    source/
    frames/
    masks/
    poses/
    nerfstudio/
    logs/
```

最终输出：

```text
{workspace}/outputs/<safe-output-name>.ply
{workspace}/outputs/<safe-output-name>.spz
```

**原因**

- 不污染用户原始相册目录。
- 中间文件可按任务清理，不影响最终模型。
- 模型图库无需理解视频任务，只扫描现有 `outputs/*.ply`。

**备选方案**

- 把中间文件放 `inputs/`：会污染现有图片输入目录，并可能被误认为 SHARP 输入。
- 把输出放单独 `video_outputs/`：会迫使模型图库、下载、导出、分享路径全部改造。

### 决策：视频生成结果写入来源元数据，并默认使用源视频同名输出

视频生成结果仍然输出到现有 `outputs/`，但额外写入轻量 sidecar：

```text
outputs/<model-id>.ply
outputs/<model-id>.spz
outputs/<model-id>.meta.json
inputs/.thumbnails/<model-id>.jpg
```

`meta.json` 记录来源类型、来源媒体 ID（如果来自本地相册）、源视频缓存路径（如果来自拖拽上传）、源文件名、模式、质量和引擎。前端只接收安全 URL，例如 `/api/gallery/<id>/source-video`，不得看到绝对磁盘路径。

默认命名策略和图片生成保持一致：从源视频文件名去掉扩展名得到模型名，不自动追加 `high180`、`focused` 或质量后缀；只有与已有 `.ply/.spz` 冲突时才追加 `-2`、`-3` 这类唯一化后缀。这样模型列表里的视频结果和图片结果一样可读，不把实现细节暴露给用户。

**原因**

- 模型图库继续扫描 `outputs/*.ply`，无需引入新表或新输出目录。
- 缩略图继续复用现有 `inputs/.thumbnails/` 路径，列表 UI 不需要特殊分支。
- 原视频预览使用受控 API 解析 sidecar，既能支持本地相册视频，也能支持用户直接拖入的视频。
- 删除拖入视频生成的模型时，可以根据 sidecar 清理受控上传缓存；来自本地相册的原视频仍保持只读，绝不随模型删除。

**备选方案**

- 把源视频复制到 `inputs/` 并按图片输入处理：会污染图片生成目录，也容易让现有 SHARP 图片任务误判。
- 把视频输出放入 `video_outputs/`：会割裂模型图库和下载/分享路径，用户也需要理解两套模型来源。
- 只在前端按文件名前缀推断源视频：无法覆盖用户改名、输出名冲突和拖入视频缓存，也无法安全支持原视频预览。

### 决策：Viewer reset 对明显离轴的视频重建模型使用包围盒中心

Nerfstudio/Splatfacto 导出的 3DGS 坐标系不一定像 ml-sharp 单图模型一样围绕现有 Viewer 默认视轴。若继续把 OrbitControls 目标点固定在默认前方位置，模型可能出现在相机正下方或正上方，初始画面会朝向空区域，左右拖拽也会表现得像围绕错误中心倾斜旋转。

修复策略：

```text
模型加载完成
  → 从 Spark SplatMesh 读取 world-space bounding box
  → 先计算旧版 reset 的默认 lookAt
  → 如果模型中心相对默认 lookAt 的横向偏移足够大
       camera.position = bbox.center + front-view fit distance
       controls.target = bbox.center
     否则
       保持旧版 reset 逻辑
```

**原因**

- OrbitControls 的旋转中心是 `controls.target`，目标点错误会直接导致拖拽手感错误。
- 只在偏移明显时启用包围盒居中，可以修复视频重建模型的坐标偏移，同时避免改变已居中的 ml-sharp 单图模型预览行为。
- 同时移动 camera position 和 target，而不是只改 lookAt，可以让初始画面和后续左右拖拽都围绕主体中心。

**备选方案**

- 改写视频输出 PLY 坐标使其居中：会改变下载/分享模型数据，且无法修复已经生成的旧结果。
- 按文件名识别视频模型：实现简单但脆弱，用户自定义输出名或导入外部视频模型时容易失效。
- 全部模型都用包围盒中心 reset：会改变旧单图模型已验证的预览手感。

调试补充：由于同一视频重建模型在第三方高斯预览器中也出现初始朝向和交互轴向异常，后续需要同时排查导出坐标系和 Viewer 坐标适配。为便于校准，Quick Controls 临时显示实时相机/模型姿态读数，包括 camera position/rotation/up/forward、OrbitControls target、orbit azimuth/polar、模型 world 轴向、包围盒 center/size 以及 target 到包围盒中心的偏差，并提供复制按钮便于反馈。

2026-06-12 最终校准补充：实时读数确认 `targetDelta=0` 后，进一步排查发现问题不是 pivot 仍偏离，而是 Nerfstudio/Splatfacto 视频模型的主体正面落在 Viewer 默认 `Y-up / -Z forward` 轨道体系的侧向轴上。相机侧强行切换 `+Y` 正面或 `+Z` up 虽能让画面短暂看正，但会让 OrbitControls 初始状态靠近极点，造成左右拖拽像 roll，且切换“正面视角”时容易触发不必要的重置/重载感。最终采用模型侧隐藏坐标适配：仅对符合视频重建形态的 Y-front 模型，在 `SplatMesh` 的用户变换之前预乘 `RotX(+90°)` orientation quaternion，把模型正面映射回 Viewer 的默认 `-Z` 观察轴；camera/controls 继续保持干净的默认 `Y-up`、`polar≈90°`、`rotation≈0` 状态。普通 ml-sharp 单图模型仍走原有 reset 和交互路径，不受该适配影响。Quick Controls 的实时调试读数保留为长期排查工具。

2026-06-16 当前实现约束补充：

- 视频模型预览已以用户实测为准初步稳定，后续不要再通过相机侧极角、camera up 或 front-view clamp 去“修正画面”。如果新视频模型仍朝向异常，优先检查 sidecar 来源、模型包围盒、隐藏 orientation 判定和 Quick Controls 调试读数。
- 模型列表中的视频来源操作必须贴合既有模型 item 交互：下载、删除、原视频预览等图标按钮在 hover/focus 或触控可达时出现；不要因为视频模型增加常驻大按钮。
- 视频生成模型的用户可见名称默认等同源视频 stem；质量档、帧数、focused cleanup 等实现细节只记录在任务详情或 sidecar 中，不写进默认文件名。
- 后端日志分层：普通 INFO 面向用户排查，只保留阶段、命令名、return code 和失败摘要；DEBUG/verbose 才面向开发排查，包含完整命令、外部工具逐行输出和 traceback。
- README 和规则文档只把 Windows + NVIDIA RTX 5070 Ti Laptop GPU 12GB 写为视频推理已验证平台；其他平台需要真实验证后再更新。

### 决策：物品模式引入自动前景处理，但首版允许分阶段落地

物品模式应优先支持自动前景隔离：

```text
物品视频
  → 抽帧
  → 自动主体分割或显著区域估计
  → 前景 mask 参与几何初始化/训练
  → 输出居中、尺度归一化的 splat
```

如果 SAM2 或等价视频分割依赖不可用，首版可以降级为“无 mask 物品重建”，但 UI/任务错误必须说明效果可能受背景影响。

**原因**

- 用户明确不希望手动修剪模型，背景噪声必须由系统尽量自动处理。
- 转台/桌面物品视频的失败模式和环境视频不同，不能只靠同一套全画面 SfM。
- 分阶段实现可以先打通稳定路线，再提升物品模式效果。

**备选方案**

- 首版不做物品模式，只做环境：不能满足“物品和环境都想重建”的需求。
- 强制 SAM2 为必需依赖：安装和显存压力变大，可能阻塞环境视频的基础可用性。

### 决策：设置页只放默认值和诊断，不承担主流程

Settings 中新增“视频重建”区域：

```text
默认质量：快速预览 / 高质量 / 极致
默认引擎：自动 / 稳定 / 实验
显存预算：自动 / 8GB / 12GB / 自定义
保留中间文件：开关
依赖状态：ffmpeg、COLMAP/hloc、Nerfstudio/Splatfacto、VGGT/VGGT-Omega
```

**原因**

- Settings 是配置和排障位置，不是创建任务入口。
- 用户第一次使用应从视频本身出发。
- 依赖状态放设置页能避免任务失败后才知道没装工具。

**备选方案**

- 所有选项都放开始弹窗：信息密度过高，破坏快速创建体验。
- 不提供设置项：高级用户无法调校 5070 Ti Laptop 的质量/显存取舍。

### 决策：依赖诊断使用进程级异步缓存，不在每次创建任务时重复扫描

视频重建依赖检测包含 `ffmpeg/ffprobe`、Nerfstudio/Splatfacto、COLMAP/hloc、可选实验初始化工具等外部命令探测。它们的结果在一次应用进程生命周期内通常不会频繁变化，因此不应在首页加载、打开弹窗或每次提交任务时同步重扫。

当前策略：

```text
后端应用启动
  → 后台线程异步扫描视频重建依赖
  → 状态 API 返回缓存；若尚未完成则返回 checking
  → Settings 手动刷新用 ?refresh=1 触发后台重扫
  → 创建任务读取同一份缓存；检测中时返回可本地化错误
```

**原因**

- 首页和模型视图不应被本地工具探测阻塞，尤其是在 Windows PATH、conda 环境或外部命令响应较慢时。
- Settings 是诊断和手动刷新位置；普通生成弹窗只需要复用已有结果。
- 依赖状态在同一进程中足够稳定，缓存能避免重复启动多个外部命令，也减少用户点击“生成”后的等待。
- `checking` 状态比同步阻塞更可解释：用户知道系统正在准备诊断，而不是界面卡住。

**备选方案**

- 每次任务创建前同步检查：实现直接，但会让每次视频推理都重复探测重建工具，点击后容易长时间无响应。
- 只在 Settings 打开时检查：能减少开销，但用户从拖拽或视频预览直接生成时可能没有诊断结果。
- 完全信任环境变量不检查：最快，但缺依赖时会退化成难读的进程错误。

### 决策：视频生成弹窗延续 Settings 玻璃态，而不是独立白底表单

视频重建弹窗承载的选项比普通上传更多，但仍属于 Sharp GUI 的主工作流入口。它需要和 Settings、侧栏、媒体预览保持同一视觉语言：

- 使用项目现有玻璃态变量、半透明层、柔和边框和阴影。
- 文本层级优先可读性，状态提示使用低饱和玻璃卡片，不使用突兀实心白底。
- 分段控件展示模式、质量和引擎，档位小标题解释资源差异。
- 使用 `prefers-color-scheme` 兼容浅色/深色系统模式。
- 移动端自动降为单列选项，避免横向溢出。

**原因**

- 视频重建是高价值入口，视觉割裂会降低用户对功能成熟度的信任。
- 设置页已经建立了本项目的玻璃态密度和层级，弹窗应复用这套语言。
- 浅色和深色模式都要可读，不能只在当前深色背景下“看起来能用”。

**备选方案**

- 使用浏览器默认表单或普通白底弹窗：实现快，但在当前深色玻璃主界面中割裂明显，浅色/深色可读性也难统一。
- 将所有说明移到 Settings：弹窗会更短，但用户在创建任务时看不到当前档位和引擎差异。

### 决策：UI 延续本地媒体图库风格，不做新的视觉体系

新增 UI 组件遵守：

- CSS Modules + CSS Variables。
- 玻璃态面板：`var(--glass-bg)`、`var(--glass-blur)`、`var(--glass-border)`。
- 图标使用现有 `Icons` 或项目图标组件，不使用 emoji 作为功能图标。
- 用户可见文案全部 i18n，`en.json` 和 `zh.json` 同步。
- 移动端入口不能只依赖 hover；视频预览控制不能互相遮挡。

**原因**

- 用户已经习惯本地媒体图库的选择栏、预览层、设置弹窗。
- 新功能复杂度高，视觉上更需要克制，避免像独立外部工具。

**备选方案**

- 做一个完整向导页：可解释更多信息，但会打断“选中视频 → 生成”的短路径。
- 用浏览器原生 select/prompt/confirm：实现快，但与项目玻璃态风格明显割裂。

## 2026-06-12 本机校准与实测结论

本轮在 Windows + NVIDIA GeForce RTX 5070 Ti Laptop GPU 12GB 上完成了稳定路线的真实端到端验证，源视频为 `C:\Users\dddd\Downloads\VID_20260612_091523.mp4`。

### 环境落地

- 本地视频重建环境使用仓库内 `.video-reconstruction-env`，避免污染主 Python 环境。
- 已验证 CUDA Toolkit 12.8、PyTorch CUDA、Nerfstudio 1.1.5、Splatfacto、gsplat 1.5.3 CUDA extension、COLMAP CUDA 和 `ffmpeg/ffprobe` 可用。
- `install.bat` 现在会调用 `tools/install_video_reconstruction.py`，用于自动安装或复用 VS Build Tools、CUDA Toolkit、PyTorch CUDA、Nerfstudio/gsplat 和 COLMAP。
- `run.bat` 会在检测到本地 `.video-reconstruction-env` 时自动把 Nerfstudio Scripts 和 COLMAP bin 加入运行时路径。

### 当前质量档参数

| 档位 | 当前用途 | 关键参数 |
| --- | --- | --- |
| 快速预览 | 快速检查相机路径、主体范围和 focused cleanup 效果 | 约 90 帧、7k 迭代、4x 输入下采样 |
| 高质量 | 当前推荐的可交付结果档 | 约 180 帧、30k 迭代、2x 输入下采样、FPS 相机采样、SO3xR3 相机优化、focused cleanup |
| 极致 | 离线追求上限，预计耗时和资源压力更高 | 约 360 帧、50k 迭代、更高分辨率预算；会按显存预算自动收紧 |

曾尝试 240 帧高质量方案，但 COLMAP 几何阶段耗时过高，性价比不如 180 帧 + 2x 输入分辨率 + 30k 训练迭代。因此 12GB 机器上的高质量默认应优先保留 180 帧方案。

### Focused cleanup 后处理

视频 3DGS 原始导出容易包含大范围游离 splat，造成模型文件看似完整但 viewer 中出现碎片、相机中心偏移和交互别扭。当前后处理策略：

- `auto` / `object` 模式默认应用 focused cleanup。
- `environment` 模式不应用主体裁剪，保留完整环境语义。
- focused cleanup 使用位置分位数、透明度和异常尺度共同筛选：默认位置分位数 5%-95%、alpha 下限 0.12、scale 98.5 分位上限。
- 为避免误删，若保留顶点数低于最小阈值或保留比例低于 25%，自动退回原始导出。
- 任务详情记录 cleanup 统计，便于排查输出为何变小或是否退回 raw export。

### 实测产物

| 输出 | PLY 大小 | SPZ 大小 | splat 数量 | 备注 |
| --- | ---: | ---: | ---: | --- |
| `VID_20260612_091523_preview_final_clean_focused.ply` | 72.96 MB | 约 4.97 MB | 308,469 | 用户确认主体纯净、可作为 focused cleanup 基准 |
| `VID_20260612_091523_high180_focused.ply` | 135.39 MB | 8.58 MB | 572,457 | 用户确认细节明显提升且仍保持纯净 |
| high180 raw export | 202.47 MB | N/A | 856,055 | focused cleanup 前的原始导出，仍包含外围碎片 |

`high180_focused` 任务 ID：`f9af3d22-796c-40a8-b3e4-ca27f5625e42`。端到端耗时约 52 分 17 秒，其中 COLMAP/抽帧约 8 分多，Splatfacto 30k 训练约 42 分多，导出和 SPZ 压缩约 1 分。

### 引擎策略结论

- `stable` 路线已经能产生可用结果，当前由 COLMAP + Nerfstudio Splatfacto 负责。
- `auto` 应作为推荐默认；实验初始化未配置时自动回退稳定路线。
- `experimental` 暂时保留为可选增强入口，定位为 VGGT/VGGT-Omega 类几何初始化。它可能帮助后续减少相机失败和提升初始化质量，但不应作为当前必需依赖，也不应自动下载 gated 或许可受限模型。
- UI 中应明确实验引擎未就绪不代表视频重建不可用，并在未配置时禁用强制实验选择。

## 风险 / 取舍

- [显存不足导致 OOM] -> 默认串行执行 GPU-heavy 任务；质量档绑定帧预算；检测 OOM 文本并给出降低质量/帧数建议；Settings 提供显存预算。
- [外部依赖安装复杂] -> 依赖检测前置；稳定依赖和实验依赖分开展示；缺少实验依赖时 Auto 回退稳定路线。
- [物品背景噪声导致模型脏] -> 物品模式预留自动 mask；缺少分割依赖时明确提示“降级重建”；不让用户手工修剪作为首版方案。
- [转台视频无法按普通环境 SfM 成功] -> 自动/物品模式识别并按 object-centric 路线处理；文案避免承诺所有转台视频都能完美。
- [长任务缺少反馈] -> 任务阶段必须覆盖抽帧、几何、训练、导出、压缩；失败时保留摘要而不是只给 process return code。
- [任务取消不彻底] -> 记录子进程并在取消时 terminate/kill；清理临时目录遵循保留中间文件设置。
- [输出覆盖已有模型] -> 统一安全命名并自动追加后缀，永不覆盖现有 `.ply/.spz`。
- [UI 入口过多造成拥挤] -> 主入口只放选择栏和视频预览；卡片级入口必须移动端可达且不影响瀑布流密度，否则延后。
- [实验模型许可风险] -> 不随项目默认打包，不自动下载 gated/non-commercial checkpoint；只作为用户自行配置的实验增强。

## 迁移计划

1. **任务基础迁移**
   - 为任务增加 `kind` 可选字段。
   - 保证没有 `kind` 的历史/测试任务仍按图片 SHARP 路径处理。
   - 保持 `/api/tasks` 响应向后兼容。

2. **视频服务落地**
   - 增加重建 job 目录。
   - 先打通稳定路线的依赖检测和命令编排。
   - 成功后写入 `outputs/<name>.ply` 并调用现有 `.spz` 转换。

3. **API 与权限**
   - 从本地相册 video id 创建任务。
   - 复用现有 owner/remote generation 权限规则。
   - 增加依赖状态和默认配置 API。

4. **前端入口**
   - 增加重建弹窗。
   - 在视频选择栏和视频预览层接入。
   - 任务创建后沿用现有任务轮询和图库刷新。

5. **设置与诊断**
   - 增加 Settings 中的视频重建区域。
   - 显示依赖状态、默认质量、引擎策略、显存预算和中间文件保留开关。

6. **验证和回归**
   - 回归图片上传、照片转 3D、视频预览、模型图库刷新。
   - 验证缺依赖、无权限、非法 video id、取消和 OOM 失败文案。

回退策略：

- 可以先隐藏或禁用视频重建入口和 API，保留已有图片生成与视频播放。
- 已生成的 `.ply/.spz` 是普通模型图库资产，即使关闭创建能力也仍可浏览。
- 如果任务类型改造引入问题，可将默认 `image_sharp` 路径恢复为唯一 dispatch 分支。

验证点：

- 现有 `/api/generate` 上传图片仍创建 SHARP 任务。
- 现有照片转 3D 仍复制照片并创建 SHARP 任务。
- 现有视频预览、下载、seek、全屏、关闭不受影响。
- 支持视频可以创建 `video_3dgs` 任务并显示阶段进度。
- 成功任务生成 `.ply`，并生成或尝试生成 `.spz`。
- 完成后模型图库能看到新模型并用 Spark 打开。
- 新增 UI 文案在中英文语言切换下完整显示。

## 待确认问题

- 稳定路线第一版已落定为 Nerfstudio `ns-process-data video` 管理 COLMAP 数据处理，并由 `ns-train splatfacto` / `ns-export gaussian-splat` 训练导出。
- 物品模式首版是否强依赖 SAM2，还是先实现无 mask 降级，再把 SAM2 作为后续增强？
- `高质量` 档已在 RTX 5070 Ti Laptop 12GB 上完成一次本机 benchmark，当前推荐默认是 180 帧、2x 输入下采样、30k 迭代。
- 中间文件默认是否删除：用户体验上应默认清理，但排障阶段可能需要保留日志和抽帧样本。
- 是否需要为任务详情增加“查看日志摘要”入口，避免长任务失败时用户只能看到一句错误。
- focused cleanup 的阈值是否需要暴露为高级设置；当前不建议暴露，先作为安全默认并记录统计。


## 2026-06-16 代码审查加固

本轮在不改变既有产品行为的前提下，对视频重建实现做了一组加固，覆盖审查中发现的健壮性、资源回收、可移植性和测试缺口：

- **取消时按进程树终止**：`run_command` 现在以独立进程组（Windows `CREATE_NEW_PROCESS_GROUP`、POSIX `start_new_session`）启动外部命令；取消时通过 `terminate_process_tree` 杀掉整棵进程树（Windows `taskkill /F /T`，POSIX `killpg`），避免 `ns-train` 的子进程/viewer 成为孤儿继续占用显存导致下一个任务 OOM。`TaskManager.cancel_task` 对视频任务复用同一进程树终止逻辑，且终止动作移到 `task_lock` 之外，避免阻塞状态读取；图片任务保持原有单进程 `terminate()`，因为它与服务进程同组，按组终止会误伤服务本身。
- **训练阶段进度反馈**：`video_optimize` 阶段会解析 Nerfstudio 的 `step/total` 输出，仅当分母等于配置的训练迭代数时才信任，把进度在 `video_optimize`（58）到 `video_export`（86）之间线性推进，避免长训练任务进度条长时间停在 58%。
- **实验依赖探测使用视频环境解释器**：VGGT 探测改为优先使用 `.video-reconstruction-env` 的 Python，而不是裸 `python`，让设置页实验依赖诊断更准确。
- **删除原图扩展名一致性**：模型删除复用 `ALLOWED_IMAGE_EXTENSIONS`，修复大写 `.JPEG/.WEBP` 原图在删除模型后残留的问题。
- **遗留命名回填注释化**：`legacy_video_match_stems` 中针对早期本机产物命名后缀（`_high180_focused` 等）的兼容逻辑已加注释，明确它只服务于 sidecar 缺失且唯一同名相册视频的旧输出，新输出直接使用源视频 stem。

### 非 Windows 平台行为说明

视频重建的端到端验证平台仍仅限 Windows + NVIDIA RTX 5070 Ti Laptop GPU 12GB。代码在非 Windows 平台上安全降级而非报错：`read_vcvars_environment` 返回空、`find_cuda_home`/`find_vcvars64` 返回 `None`、进程组改用 `start_new_session`。这意味着在 macOS/Linux 上，只要用户自行把 `ffmpeg`、`ns-*`、`colmap` 放入 PATH，稳定路线依赖检测和命令编排仍可工作，但项目不会为这些平台做自动 PATH 注入或一键安装，README 也不把它们列入已验证矩阵。


## 2026-06-16 鲁棒性与进度可观测性补充

本轮在审查与实测反馈后，对视频重建做了一组聚焦的鲁棒性、可观测性与体验改进，均不改变相机充足、配准正常时的既有行为：

### 决策：COLMAP 特征匹配策略按质量档绑定

`ns-process-data video` 此前对所有质量档固定使用 `sequential` 匹配。对长视频或环绕/回看素材，sequential 只匹配相邻帧、缺少回环能力，COLMAP 容易断裂成多个 sparse 子模型，而 Nerfstudio 默认只取 `sparse/0`，导致只重建前半段视角，甚至注册相机过少触发训练期 FPS 采样断言崩溃。

按质量档分流：

```text
preview (90 帧)   sequential   最快，快速预览可接受偶尔断链
high    (180 帧)  exhaustive   两两匹配（~1.6 万对）最大化注册率，最稳，且不依赖联网
extreme (360 帧)  vocab_tree   O(n^2) 过慢，改用词汇树检索（Nerfstudio 首次自动下载词表，需联网一次）
```

**原因**：匹配只影响 COLMAP 阶段中的“特征匹配”子步骤，不影响占总耗时约 80% 的训练；实测 high 档总耗时约 52 分钟、COLMAP 阶段约 8 分钟，换 exhaustive 预计总时长增加约 5~10%，换取显著更高的配准成功率与完整性，性价比高。extreme 帧数翻倍会让 exhaustive 的匹配对数翻 4 倍，故改用 vocab_tree。

**备选**：全部档统一 exhaustive（extreme 太慢）；统一 vocab_tree（依赖联网下载词表，离线环境会卡住）；暴露为用户高级选项（更灵活，但默认仍需一个稳妥值）。

### 决策：相机注册过少时回退相机采样策略

高质量档使用 Nerfstudio 的 FPS 相机采样（fpsample `bucket_fps_kdline_sampling`，h=3，要求相机数 ≥8）。当 COLMAP 仅注册极少相机时训练会直接因 `2**h should be <= n_pts` 断言失败。现在训练前统计 `transforms.json` 的注册相机数，低于保守阈值时自动从 FPS 回退到 random 采样，并在任务详情与日志记录降级原因。这是兜底，匹配策略改进才是减少“相机过少”根因的主手段。

### 决策：暴露训练实时进度入口并修正进度推进

- 训练阶段抓取底层训练框架（Nerfstudio/viser）的实时查看器链接，在 INFO 日志级别打印（无需调高日志级别），并在任务详情中安全暴露查看器的 `viewer_url`（可读）与 `viewer_port`（端口）。前端任务队列以与项目一致的玻璃态圆角矩形标签（非胶囊）展示可点击的实时进度入口。
- **跨设备可访问**：后端不把查看器 host 写死成 `localhost`，而是上报端口；前端用“用户当前访问 Sharp GUI 的 hostname”重建链接（本机即 localhost，局域网客户端即重建主机的局域网 IP）。因为 viser 查看器默认监听 `0.0.0.0`（所有网卡），所以局域网内发起或查看任务的其他设备也能打开实时进度，而不再被本机 `localhost` 限制。无端口信息时回退到可读的 `viewer_url`。
- 进度解析优先识别 Nerfstudio 的百分比输出、回退 `step/total`，让优化阶段进度真实推进，不再长期停在固定值。
- **安全注意**：viser 查看器在 `0.0.0.0:7007` 上无认证，局域网内任意设备只要知道 `主机IP:端口` 即可访问该实时查看器。这是 Nerfstudio 查看器的固有行为，不是本项目引入；它只在训练期间存在、训练结束即关闭，且不暴露源视频或工作区的绝对路径。如需收紧，应在 Nerfstudio 侧限制查看器监听地址。

### 决策：取消任务按进程树终止

外部重建命令以独立进程组/会话启动，取消时终止整棵进程树（Windows `taskkill /F /T`、POSIX `killpg`），避免 `ns-train` 的子进程/查看器成为孤儿继续占用显存导致后续任务 OOM；图片任务因与服务同进程组仍用单进程终止。

### 决策：物品模式按相机环绕几何聚焦主体（C1）

物体视频常把主体放在桌面/地面中央并环绕拍摄，背景（桌布、地面、远墙）成片、稠密且位于场景分布内部，因此现有的“统计清理”（位置分位 + 透明度 + 尺度）只能去掉离群飞溅碎片，去不掉成片环境——这是统计后处理的原理局限，用户实测也确认 `auto` 输出仍保留大量环境。

C1 仅对**用户显式选择的 `object` 模式**生效：

```text
object 模式：统计清理 → 相机环绕几何估计主体中心/半径 → 球形裁剪去掉范围外环境
auto 模式：仅统计清理（不做半径裁剪，避免把环境素材误裁）
environment 模式：完全不裁（保留完整场景）
```

主体定位用相机几何而非点云统计：环绕视频的所有相机 look-at 射线汇聚于主体，对这些射线做最小二乘求交得到主体中心，半径取相机到中心距离中位数 × 系数。相机位姿来自 `transforms.json`（原始 COLMAP 坐标），经训练输出的 `dataparser_transforms.json`（transform + scale）映射到导出 PLY 所在的训练坐标系，保证与点云对齐。

**安全回退**：相机数不足、缺少 `dataparser_transforms.json`、射线求交奇异、中心落在相机云之外、或球裁后保留比例过低，任一条件触发即跳过半径裁剪、退回统计清理结果；最坏情况等于改动前行为，绝不产出空模型或误裁。

**原因**：把有损的“主体聚焦”绑定到用户的显式 `object` 选择，语义清晰且零误伤环境/自动模式；相机几何是区分主体与环境的可靠信号，纯点云统计做不到。

**局限与后续**：C1 能去掉远处环境（墙、远景、地面外围），但紧贴主体底部的桌面仍可能残留——彻底“只留主体”需要 C2（前景分割 mask，如 rembg/U²-Net 或 SAM2，在训练阶段排除背景），作为后续增强。

**备选**：让 `auto` 也自动判断是否环绕主体再裁（误判会误裁环境，风险高，未采用）；读 `dataparser_transforms` 做坐标对齐之外改为纯点云中心估计（环境点多时中心被拉偏，不可靠，未采用）。

### 关联的全局体验改进（非视频重建专属）

- 全局玻璃态悬浮提示：模型名、任务队列文件名/阶段/错误等截断文本悬浮显示完整内容，统一替换原生 title，遵循 styling-guide 禁止胶囊徽标的约束。
- 模型删除复用 `ALLOWED_IMAGE_EXTENSIONS`，修复大写扩展名原图残留。
