## 为什么

Sharp GUI 已经具备单图生成 3D Gaussian Splatting 模型、本地媒体相册、视频预览和 Spark 查看能力，但视频目前只能播放，不能进入 3D 生成工作流。对于拥有 RTX 5070 Ti Laptop 这类 12GB 显存独显的用户，最有价值的新能力是：选中一个物品或环境视频，一次性自动重建出可直接浏览的 `.ply/.spz` 3DGS 模型，而不是让用户导出帧、跑外部命令、再手工整理模型。

这个变更要解决的是“从本地视频到可用 3D 模型”的完整产品闭环：入口在现有媒体图库，执行在现有任务队列，产物进入现有模型图库，查看继续使用现有 Spark Viewer。用户不需要理解 COLMAP、Nerfstudio、VGGT、抽帧、位姿估计、训练步数或 SPZ 压缩这些细节。

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
- 新增或扩展视频重建服务模块：负责依赖检测、抽帧、稳定/实验引擎选择、进程执行、阶段解析、输出检查和清理策略。
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

- 稳定路线建议依赖 `ffmpeg/ffprobe`、COLMAP/hloc 或 Nerfstudio/Splatfacto/gsplat。
- 实验路线可选支持 VGGT/VGGT-Omega 等前沿几何初始化工具，但不得作为默认必需依赖。
- 需要在设计和设置中明确区分“稳定可用”和“实验增强”，避免用户误以为缺少实验模型就是功能不可用。

数据与兼容性影响：

- 输入视频来自已配置的本地相册，API 不暴露绝对路径。
- 中间文件应写入 workspace 下可清理目录。
- 最终 `.ply/.spz` 写入现有 `outputs/`，因此现有模型图库、Spark Viewer、下载和导出能力可以复用。
