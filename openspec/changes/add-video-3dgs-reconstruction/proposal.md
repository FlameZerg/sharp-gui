## 为什么

Sharp GUI 已经具备单图生成 3D Gaussian Splatting 模型、本地媒体相册、视频预览和 Spark 查看能力，但视频目前只能播放，不能进入 3D 生成工作流。对于拥有 RTX 5070 Ti Laptop 这类 12GB 显存独显的用户，最有价值的新能力是：选中一个物品或环境视频，一次性自动重建出可直接浏览的 `.ply/.spz` 3DGS 模型，而不是让用户导出帧、跑外部命令、再手工整理模型。

这个变更要解决的是“从本地视频到可用 3D 模型”的完整产品闭环：入口在现有媒体图库，执行在现有任务队列，产物进入现有模型图库，查看继续使用现有 Spark Viewer。用户不需要理解 COLMAP、Nerfstudio、抽帧、位姿估计、训练步数或 SPZ 压缩这些细节。

## 变更内容

- 新增“视频生成 3D 模型”的能力：从本地相册中的视频创建静态 3DGS 重建任务。
- 新增统一入口：在本地媒体图库的视频选择栏和视频预览层中提供“生成 3D”操作，保持现有 Apple 玻璃态视觉风格。
- 新增重建模式：`自动`、`物品`、`环境`。入口保持简单，但后端允许按不同场景选择不同处理策略。
- 新增质量档位：`快速预览`、`高质量`、`极致`。默认面向 12GB 显存笔记本 GPU 控制帧预算和训练资源。
- 扩展任务队列：支持视频重建任务阶段，例如抽帧、几何/位姿估计、高斯优化、导出、SPZ 压缩、失败诊断和取消。
- 新增依赖检测：识别视频重建所需工具是否可用，并在设置页和任务错误中给出明确状态。
- 输出仍然使用现有模型图库契约：成功任务生成 `.ply`，并尽可能自动生成 `.spz`，最终出现在 `outputs/` 和模型图库中。
- 保留当前单图 SHARP 流程，不改变已有图片上传、照片转 3D、模型查看、下载和分享行为。

首版明确不做：

- 不做动态 4DGS、时间序列播放或动态人物/车辆建模。
- 不做点云编辑、模型裁剪、手工抠图、网格修补、重拓扑或建模编辑器。
- 不修改 `ml-sharp/` 上游子项目。
- 不修改 legacy `templates/index.html` 和 `static/lib/`。
- 不做云端任务、远程 GPU 调度、多机队列或账号体系。
- 不承诺透明、镜面、纯白墙、强运动模糊、快速移动主体等困难视频一定成功。

## 能力范围

### 新增能力
- `video-3dgs-reconstruction`: 定义从单个本地视频一键创建静态 3DGS/SPZ 模型的完整能力，包括任务创建、模式/质量选择、依赖检测、阶段进度、输出产物、失败处理、取消和模型图库集成。

### 修改能力
- `local-video-gallery-preview`: 在现有本地视频浏览和预览体验中增加视频重建入口，同时保持现有播放、下载、全屏、导航、移动端交互和可访问性行为。

## 影响范围

后端影响：

- `backend/services/task_queue.py`：需要支持任务类型分发，避免所有任务都被当成 `sharp predict`。
- 新增或扩展视频重建服务模块：负责依赖检测、抽帧、稳定引擎策略、进程执行、阶段解析、输出检查和清理策略。
- `backend/routes/photo_gallery.py` 或新增 route：从相册视频 ID 创建视频重建任务。
- `backend/security/access_control.py`：视频重建应遵守现有生成权限和远程生成开关。
- `backend/config.py` / `backend/routes/settings.py`：保存视频重建默认配置和依赖诊断结果。
- `backend/paths.py`：如需中间目录，应在 workspace 下派生，避免污染源视频目录。

前端影响：

- `frontend/src/api/`：新增视频重建 API 调用，继续使用项目 `fetch` 封装。
- `frontend/src/types/`：新增重建模式、质量档位、依赖状态、任务阶段等类型。
- `frontend/src/store/useAppStore.ts`：仅添加必要的重建弹窗、默认配置和依赖状态。
- `frontend/src/components/photoGallery/`：在选择栏、网格/卡片可达位置加入视频生成入口。
- `frontend/src/components/common/ImageViewer/`：视频预览层增加“生成 3D”操作，但不干扰播放控制。
- `frontend/src/components/layout/Settings/`：新增视频重建默认配置和依赖检测区域。
- `frontend/src/i18n/en.json` / `zh.json`：所有新增用户可见文本必须中英同步。

运行依赖影响：

- 稳定路线依赖 `ffmpeg/ffprobe`、COLMAP 和 Nerfstudio/Splatfacto/gsplat。
- 当前变更只包含已验证稳定路线；其他探索保留在单独的废弃变更记录中。

2026-06-12 实施补充：

- 已在 Windows / RTX 5070 Ti Laptop 12GB 环境中配置并验证稳定路线：本地 `.video-reconstruction-env`、CUDA 12.8、PyTorch CUDA、Nerfstudio/Splatfacto、gsplat CUDA 扩展和 COLMAP CUDA。
- 已新增 Windows 一键安装脚本，用于后续自动安装或复用视频重建环境，并在 `run.bat` 中自动接入本地 Nerfstudio/COLMAP 路径。
- 已将 `auto` / `object` 模式的默认输出改为 focused cleanup 版本，避免生成结果包含大范围游离碎片；`environment` 模式仍保留完整场景语义。
- 已将 12GB 显存机器上的 `高质量` 档校准为更适合最终结果的默认：约 180 帧、2x 输入下采样、30k 训练迭代、FPS 相机采样、SO3xR3 相机优化和更密集 splat 参数。
- 已在设置页增加质量档、引擎策略和显存预算的解释文案；`auto` 当前等价于已验证稳定路线，保留未来策略切换空间。
- 已补充 Spark Viewer 相机重置适配：当视频重建模型的实际包围盒中心明显偏离默认视轴时，按模型中心重置相机位置和 OrbitControls 目标点；已居中的旧单图模型继续沿用原 reset 行为。

2026-06-13 实施补充：

- 视频重建弹窗已按 Settings 页同一套 Apple 玻璃态风格重做，包含半透明面板、玻璃态摘要卡、分段控件、可读状态提示、浅色/深色模式适配和移动端单列布局，避免和主界面割裂。
- 视频重建依赖诊断已调整为后端进程启动后异步预热一次，并在进程内缓存结果；设置页可手动刷新触发后台重扫，普通打开首页或重建弹窗不再同步阻塞扫描工具。
- 任务创建复用缓存依赖状态：若后台检测仍在进行，返回可本地化的“依赖检查中”状态，而不是在用户点击生成时再次长时间阻塞。

2026-06-16 文档补充：

- 当前视频重建能力已初步稳定在 Windows + NVIDIA RTX 5070 Ti Laptop GPU 12GB 环境；README 仅把该平台列为已完成端到端验证的平台，其他平台暂不写入已支持矩阵。
- 视频模型预览的最终方向是“模型侧坐标适配 + 干净相机初始状态”：对视频重建形态模型隐藏预乘 orientation，保持 camera / OrbitControls 仍处于默认 `Y-up / -Z forward / polar≈90°` 轨道，避免左右拖拽 roll；旧 ml-sharp 单图模型继续保护原行为。
- 视频生成模型应和图片模型保持同一图库体验：输出名默认使用源视频同名 stem，缩略图优先使用视频封面，原视频预览入口沿用 hover 后出现的模型操作按钮，不改成常驻按钮。
- 后端日志默认保持可读：INFO 只输出入队、阶段切换、命令开始/结束和失败摘要；HTTP 请求日志与外部工具逐行输出仅在 `SHARP_HTTP_LOGS=1`、`SHARP_LOG_LEVEL=DEBUG` 或 verbose 模式下启用。
- 仍需继续保留未验证项：旧图片/照片生成回归、视频播放控件完整回归、失败路径、响应式/双语实测和干净 Windows 环境一键安装验收。

数据与兼容性影响：

- 输入视频来自已配置的本地相册，API 不暴露绝对路径。
- 中间文件应写入 workspace 下可清理目录。
- 最终 `.ply/.spz` 写入现有 `outputs/`，因此现有模型图库、Spark Viewer、下载和导出能力可以复用。
