> 当前进度（2026-06-16）：85/94 已完成。剩余项主要是现有图片/照片回归、视频播放控件回归、失败路径完整覆盖、响应式视觉检查、语言切换实测、Windows 一键安装验收、视频生成模型缩略图/原视频预览/拖拽生成入口和新视频重建弹窗视觉的实际页面回归。

## 1. 现状梳理与任务模型基础

- [x] 1.1 梳理当前 `TaskManager` 的任务字段、worker 调度、取消逻辑、完成检查和 SPZ 自动转换流程，记录哪些字段必须保持前端兼容。
- [x] 1.2 为任务状态增加可选 `kind` 字段，并确保未指定 `kind` 的现有任务按图片 SHARP 任务处理。
- [x] 1.3 将现有固定 `sharp predict` 执行逻辑拆成图片任务分支，例如 `image_sharp` handler，保持命令、进度解析和完成检查行为不变。
- [x] 1.4 增加视频任务分支入口，例如 `video_3dgs` handler，占位阶段先能安全失败并返回“依赖/管线未配置”的明确错误。
- [x] 1.5 保证 `/api/tasks` 响应仍包含现有前端依赖字段：`id`、`filename`、`status`、`progress`、`stage`、`error`、`created_at`。
- [x] 1.6 增加或更新后端测试，覆盖图片任务默认兼容、任务类型序列化、pending 取消、running 取消和 failed/completed 终态。

## 2. 视频重建配置与路径管理

- [x] 2.1 在配置读取/保存层加入视频重建默认配置：默认质量、引擎策略、显存预算、是否保留中间文件。
- [x] 2.2 在 `PathContext` 或视频服务内部定义 workspace 派生中间目录，例如 `.video-reconstruction/jobs/<task_id>/`。
- [x] 2.3 实现安全输出名称生成：从视频名或用户输入派生可读文件名，过滤非法字符，并在冲突时自动追加后缀。
- [x] 2.4 确保中间目录创建、清理和保留策略不会修改原始相册目录，也不会污染 `inputs/`。
- [x] 2.5 增加针对中文文件名、空格文件名、重复输出名、跨平台路径比较的后端检查。

## 3. 依赖检测与引擎策略

- [x] 3.1 实现视频重建依赖检测结构，区分 `required`、`stable`、`experimental`、`available`、`missing`、`message` 等状态。
- [x] 3.2 检测视频基础工具可用性，例如 `ffmpeg` 和 `ffprobe`，并返回版本或缺失原因。
- [x] 3.3 检测稳定路线依赖，例如 COLMAP/hloc 或 Nerfstudio/Splatfacto/gsplat，先选择一个首版稳定实现目标并在设计备注中确认。
- [x] 3.4 检测实验路线依赖，例如 VGGT/VGGT-Omega 的本地配置状态，但不得默认下载 gated 或许可受限 checkpoint。
- [x] 3.5 实现引擎策略解析：`auto` 缺实验依赖时回退稳定路线，`stable` 只走稳定路线，`experimental` 缺依赖时拒绝创建任务。
- [x] 3.6 为依赖缺失、实验路线不可用、稳定路线不可用分别提供可本地化的错误码或错误类型。

## 4. 视频重建后端服务

- [x] 4.1 新增视频重建服务模块，封装任务配置、源视频解析、job 目录、子进程执行、日志收集和结果检查。
- [x] 4.2 通过现有相册索引解析 video media id，并再次校验实际路径位于配置相册 root 内。
- [x] 4.3 实现抽帧阶段：按质量档应用帧预算、分辨率上限或采样策略，并写入 job 目录。
- [x] 4.4 实现任务阶段更新：抽帧、前景处理、几何/位姿估计、高斯优化、导出、SPZ 压缩、完成/失败。
- [x] 4.5 实现稳定路线命令编排，输出标准 Gaussian Splat `.ply` 到最终 `outputs/` 目录。
- [x] 4.6 为物品模式预留自动前景处理接口；若分割依赖不可用，任务应记录降级说明而不是静默当作环境模式。
- [x] 4.7 调用现有 `ply_to_spz` 转换成功 `.ply`，并在 SPZ 转换失败时保留 `.ply` 和清晰错误详情。
- [x] 4.8 实现 OOM/显存不足识别：捕获常见 CUDA out-of-memory 文本并转换为建议降低质量或帧预算的错误。
- [x] 4.9 实现取消处理：取消时终止子进程，设置 cancelled 状态，并按保留中间文件配置处理 job 目录。
- [x] 4.10 增加后端测试或最小可运行假命令测试，覆盖成功输出、缺依赖、OOM 文本、输出冲突、取消和 SPZ 失败。

## 5. API、权限与设置接口

- [x] 5.1 新增创建视频重建任务 API，例如 `POST /api/video-reconstructions`，参数包含 `video_id`、`mode`、`quality`、`engine`、`output_name`。
- [x] 5.2 在 API 层校验模式、质量、引擎策略、输出名称长度和 media id 类型，非法请求不得创建任务。
- [x] 5.3 将视频重建 API 纳入现有生成权限矩阵：owner 可用，远程用户需满足门禁和 `allow_remote_generation`。
- [x] 5.4 新增依赖诊断 API 或扩展 settings 响应，返回视频重建依赖状态和当前默认配置。
- [x] 5.5 扩展 settings 保存接口，允许本机 owner 更新视频重建默认配置，远程非 owner 请求必须拒绝。
- [x] 5.6 增加 API 测试或手动验证脚本，覆盖无权限、非法 video id、照片 id、缺依赖、非法选项和正常入队。

## 6. 前端类型、API 与状态

- [x] 6.1 新增 TypeScript 类型：重建模式、质量档位、引擎策略、依赖状态、视频重建请求/响应、扩展任务 kind/stage。
- [x] 6.2 新增前端 API 函数，使用现有 `apiGet`/`apiPost` 封装，不引入 axios。
- [x] 6.3 更新任务队列展示逻辑，让视频重建阶段能显示本地化文本，同时保留现有图片任务阶段。
- [x] 6.4 在 Zustand 中只添加必要状态：重建弹窗打开状态、目标视频、依赖状态、默认配置、提交中状态。
- [x] 6.5 确认新增类型通过 `types/index.ts` 桶导出，并对纯类型导入使用 `import type`。

## 7. 前端重建弹窗

- [x] 7.1 新建视频重建弹窗组件，遵循三件套结构：`ComponentName.tsx`、`ComponentName.module.css`、`index.ts`。
- [x] 7.2 弹窗提供模式选择：自动、物品、环境，并用分段控制样式呈现。
- [x] 7.3 弹窗提供质量选择：快速预览、高质量、极致，并清晰显示推荐默认值。
- [x] 7.4 弹窗提供输出名称输入，默认从视频名派生，提交前处理空值和过长值。
- [x] 7.5 弹窗提供折叠高级项：引擎策略、保留中间文件、帧预算或显存提示。
- [x] 7.6 弹窗在依赖缺失或权限不足时显示玻璃态错误/禁用状态，不使用原生 `alert`。
- [x] 7.7 弹窗移动端布局不得横向溢出，按钮和文本不得互相遮挡。

## 8. 本地媒体图库入口

- [x] 8.1 更新 `PhotoSelectionBar` 或相关选择栏逻辑，区分已选照片数量和已选视频数量。
- [x] 8.2 当只选中视频或包含视频时，提供“生成 3D”入口，并避免把视频传给现有照片转换 API。
- [x] 8.3 如果首版只支持一次一个视频，选择多个视频时明确提示限制或要求用户只选择一个。
- [x] 8.4 在视频预览层增加“生成 3D”操作，位置不能遮挡播放、seek、音量、下载、全屏、关闭和前后导航。
- [x] 8.5 确保触控设备上入口常驻或可达，不依赖 hover 才出现。
- [x] 8.6 创建任务成功后刷新任务队列，并沿用现有任务完成后刷新模型图库的模式。

## 9. 设置页与诊断 UI

- [x] 9.1 在 Settings 中新增“视频重建”区域，视觉上延续现有设置页玻璃态和密度。
- [x] 9.2 显示默认质量、默认引擎策略、显存预算、保留中间文件等配置项。
- [x] 9.3 显示依赖诊断：基础视频工具、稳定重建工具、实验初始化工具。
- [x] 9.4 缺依赖时显示本地化说明和建议，不把原始堆栈作为主要 UI 文案。
- [x] 9.5 本机 owner 可以保存默认配置；非本机用户按现有权限规则禁用或隐藏保存能力。

## 10. 国际化与样式一致性

- [x] 10.1 在 `frontend/src/i18n/en.json` 和 `zh.json` 同步添加所有新增 key，使用 camelCase。
- [x] 10.2 覆盖入口、弹窗、设置、依赖状态、任务阶段、权限错误、失败建议和成功提示文案。
- [x] 10.3 新增样式全部使用 CSS Modules；新增设计 token 只放 `variables.css`。
- [x] 10.4 使用现有图标组件或补充项目 Icons，不使用 emoji 作为功能图标。
- [x] 10.5 检查浅色/深色模式、focus-visible、hover、触控布局和 `prefers-reduced-motion`。

## 11. 回归与验收验证

- [x] 11.1 运行后端测试或针对性 pytest，覆盖任务 dispatch、API 校验、权限、依赖状态和路径安全。
- [x] 11.2 运行前端 type-check、lint 和 build。
- [ ] 11.3 手动验证现有图片上传生成仍调用 SHARP，并生成 `.ply/.spz`。
- [ ] 11.4 手动验证本地相册照片转 3D 仍可用，视频不会进入照片转换流程。
- [ ] 11.5 手动验证本地视频预览、下载、seek、音量、全屏、关闭和前后导航不回归。
- [x] 11.6 手动验证受支持视频能创建视频重建任务，展示阶段，取消后进入 cancelled。
- [x] 11.7 在依赖可用环境下手动验证视频任务成功生成 `.ply`，并生成或尝试生成 `.spz`，模型图库刷新后可打开。
- [ ] 11.8 手动验证缺依赖、无权限、非法 video id、非法选项、输出名冲突、OOM 文本等失败路径。
- [ ] 11.9 在 375px、768px、1024px、1440px 视口检查选择栏、视频预览操作、重建弹窗和设置诊断无溢出或遮挡。
- [ ] 11.10 切换中英文语言，确认所有新增 UI 文案、任务阶段和错误提示都来自 i18n。
- [ ] 11.11 手动验证 Settings 视频重建说明：质量档小标题、当前档位说明、引擎说明、实验未就绪禁用/提示在中英文下可读且无溢出。
- [x] 11.12 手动验证 focused cleanup 行为：`auto`/`object` 默认输出聚焦主体，任务详情记录清理统计；`environment` 模式不裁剪完整场景。
- [ ] 11.13 在干净或半干净 Windows 环境验证一键安装脚本：可安装/复用 `.video-reconstruction-env`、CUDA/VS Build Tools、Nerfstudio/gsplat 和 COLMAP wrapper。

## 12. 模型查看器相机兼容性

- [x] 12.1 调查 Viewer 当前 reset 逻辑、OrbitControls 目标点行为和 Spark `SplatMesh.getBoundingBox()` 可用性，确认视频重建模型手感问题来自模型中心偏离默认视轴后仍围绕旧 target 旋转。
- [x] 12.2 为 Spark Viewer 增加 bounds-aware reset 分支：当模型包围盒中心相对默认 lookAt 横向偏移明显时，同时将 camera position 和 `controls.target` 对齐到模型中心。
- [x] 12.3 保持兼容保护：模型已居中、包围盒不可用或 RAD/分页源无 CPU splat 数据时继续使用旧 reset 算法，避免影响现有 ml-sharp 单图模型。
- [x] 12.4 运行前端 `npm run lint` 和 `npm run build`，确认 viewer 相机修改通过静态检查和生产构建。
- [x] 12.5 在 Quick Controls 中增加临时实时调试读数：相机位置/旋转/up/forward、OrbitControls target、orbit 方位/极角、模型 world 姿态轴、包围盒 center/size、target 偏差。
- [x] 12.6 为临时调试读数增加中英文 i18n、复制调试信息按钮，并保持面板样式可读。
- [x] 12.7 手动验证 `VID_20260612_091523_high180_focused.ply/.spz` 或同类视频重建模型：初始画面朝向主体，左右拖拽为围绕主体 yaw，且旧 ml-sharp 单图模型预览手感不回归。
- [x] 12.8 根据调试读数将视频重建模型适配从相机侧修正改为模型侧隐藏 orientation：对符合视频重建形态的 Y-front 模型在用户姿态变换前预乘 `RotX(+90°)`，让 camera/OrbitControls 继续保持默认 `Y-up / -Z forward / polar≈90°` 的干净初始状态，避免 roll 手感，并保护 ml-sharp 单图模型行为。

## 13. 视频生成模型图库来源体验

- [x] 13.1 为视频重建完成结果写入 `outputs/<model-id>.meta.json`，记录源视频、模式、质量、引擎等来源元数据，且前端响应不暴露绝对路径。
- [x] 13.2 视频重建完成后从源视频抽帧生成模型图库缩略图，复用现有 `/api/thumbnail/<id>` 和列表缩略图显示路径。
- [x] 13.3 为视频生成模型提供原视频预览入口：模型列表小眼睛按钮可打开同一套视频预览层，支持播放、进度、音量、下载和全屏。
- [x] 13.4 统一模型视图拖拽/生成入口：模型文件直接预览，图片走现有 SHARP 生成，单个视频走视频重建上传 API；多个视频或混合拖入给出明确提示。
- [x] 13.5 更新首页/空状态/侧栏生成入口文案和中英文 i18n，明确图片、视频和模型文件三类入口。

## 14. 视频重建弹窗视觉与依赖检测缓存

- [x] 14.1 将视频生成弹窗改为与 Settings 一致的 Apple 玻璃态视觉：半透明面板、可读文本层级、玻璃态摘要卡、分段控件、状态提示和高级折叠区。
- [x] 14.2 为视频生成弹窗补齐浅色/深色模式适配、focus-visible、移动端单列分段布局和各档位小标题说明。
- [x] 14.3 将视频重建依赖诊断改为每个后端进程启动后异步预热一次；状态 API 读取缓存或返回 checking 状态，不阻塞首页加载。
- [x] 14.4 让 Settings 手动刷新使用 `?refresh=1` 触发后台重扫；Settings 和视频生成弹窗共享 store 中的依赖状态，普通打开弹窗不再重复同步扫描工具。
- [x] 14.5 任务创建复用 `check_dependencies()` 的进程级缓存；缓存仍在后台检测时返回本地化的 `video_reconstruction_dependencies_checking` 错误，而不是阻塞启动。
- [x] 14.6 运行 `venv\Scripts\python.exe -m pytest tests/test_api_contract.py tests/test_services.py tests/test_security.py tests/test_route_map.py`、`npm run lint`、`npm run build`、`python -m compileall backend tests`、`openspec validate add-video-3dgs-reconstruction --strict` 和 `git diff --check`。
- [ ] 14.7 手动验证视频生成弹窗在真实页面深色/浅色模式下的玻璃态观感、可读性、滚动和移动端布局。

### 2026-06-12 实测记录

- 已完成 Windows 依赖配置：CUDA Toolkit 12.8、PyTorch CUDA、Nerfstudio/Splatfacto、gsplat CUDA extension、COLMAP CUDA、`ffmpeg/ffprobe` 均可用。
- 已完成视频任务创建与取消验证：任务 `82e2325e-0803-4529-97b1-07dd636e4477` 在 COLMAP 阶段取消后进入 `cancelled`。
- 已完成视频任务成功输出验证：任务 `f9af3d22-796c-40a8-b3e4-ca27f5625e42` 生成 `VID_20260612_091523_high180_focused.ply` 和 `.spz`。
- `VID_20260612_091523_high180_focused.ply`：约 135.39 MB、572,457 splats；`.spz`：约 8.58 MB。用户截图确认细节明显提升且保持纯净。
- 高质量档本机端到端耗时约 52 分 17 秒：COLMAP/抽帧约 8 分多，30k 训练约 42 分多，导出和 SPZ 压缩约 1 分。
- 已完成设置页说明增强的静态验证：`npm run lint`、`npm run build` 通过；`git diff --check` 通过。
- 已部分覆盖失败路径：缺 `video_id` 请求返回 `video_reconstruction_invalid_request`；依赖诊断 API 显示稳定路线可用、实验初始化未配置。完整无权限、输出名冲突、OOM 等路径仍待 11.8 验证。
- 已完成 Viewer 相机修复的代码级验证：`frontend/src/hooks/useViewer.ts` 会在模型包围盒明显离轴时按 bounds center 重置 camera/target；`npm run lint`、`npm run build` 和 `git diff --check` 均通过。后续人工反馈显示仅靠 bounds center 不足以修复视频模型轴向问题，因此继续推进到模型侧 orientation 适配。
- 已完成临时 Viewer 调试读数：Quick Controls 可实时显示并复制相机、OrbitControls、模型姿态轴和包围盒偏差数据；`npm run lint`、`npm run build` 和 `git diff --check` 通过。用户确认调试面板位置和内容适合长期保留。
- 根据用户反馈读数确认 `targetDelta=0`，pivot 已正确居中；真正问题来自视频重建模型正面接近世界 `+Y/-Y` 方向，而 OrbitControls 默认 `Y-up` 轨道在该方向附近会接近极点。已放弃相机侧 `+Y/+Z` reset 方案，改为仅对视频形态 Y-front 模型在模型侧隐藏预乘 `RotX(+90°)` orientation quaternion，使画面正向和相机初始读数同时保持干净。用户已确认视角和左右拖拽手感恢复正常，且不会影响旧 ml-sharp 单图模型预览。
- 已完成视频生成模型来源体验的代码级验证：后端新增 sidecar 元数据、视频缩略图抽帧、原视频安全预览路由和拖入视频上传重建 API；前端统一侧栏/主画布拖拽入口并复用视频预览层。`venv\Scripts\python.exe -m pytest tests/test_api_contract.py tests/test_services.py tests/test_security.py tests/test_route_map.py` 通过 50 项；`npm run lint`、`npm run build`、`python -m compileall backend tests`、`openspec validate add-video-3dgs-reconstruction --strict` 通过。实际页面拖拽、缩略图生成和原视频预览仍待浏览器手动回归。

### 2026-06-16 代码审查加固记录

- 取消视频任务改为按进程树终止：`run_command` 以独立进程组/会话启动外部命令，`terminate_process_tree` 用 `taskkill /F /T`（Windows）或 `killpg`（POSIX）杀整棵树；`cancel_task` 对视频任务复用该逻辑并移出 `task_lock`，图片任务保持原单进程终止，避免误伤服务进程。
- `video_optimize` 阶段解析 Nerfstudio 进度输出（优先百分比、回退 step/total），把进度在 58→86 之间真实推进，修复长训练进度条长期停在 58% 的问题。
- 训练阶段抓取并暴露 Nerfstudio/viser 实时查看器链接：INFO 级别日志打印、任务详情安全暴露 `viewer_url`，前端任务队列以玻璃态圆角矩形标签展示可点击的实时进度入口。
- COLMAP 特征匹配策略按质量档绑定：preview=sequential、high=exhaustive、extreme=exhaustive，减少长视频 sequential 断链导致的只重建前半段/相机过少问题；词表检索不再作为极致档默认，也不保留隐藏回退分支，避免部分素材配准过少和实现路径不一致。
- 相机注册过少时把 FPS 相机采样回退为 random，避免训练期 fpsample 断言崩溃，并记录降级与注册相机数。
- 物品（object）模式新增相机环绕几何主体聚焦裁剪（C1）：仅 object 模式生效，auto/environment 不受影响；通过 `dataparser_transforms.json` 对齐坐标，带数据缺失/几何异常/裁剪过激的安全回退。
- 任务进入处理即记录开始时间：前端任务卡片在处理中实时显示已用时长；视频任务后端日志在阶段切换/完成时记录各阶段耗时与总耗时。
- 抽帧/COLMAP 等长时间静默步骤增加后台心跳日志：持续无输出时按间隔打印 INFO 提示仍在运行及已用时长，避免被误判为卡死。
- VGGT 实验依赖探测改用视频重建环境的 Python 解释器。
- 模型删除复用 `ALLOWED_IMAGE_EXTENSIONS`，修复大写 `.JPEG/.WEBP` 原图残留。
- `legacy_video_match_stems` 兼容回填逻辑补充注释，明确只服务旧本机命名产物。
- 新增后端单测：OOM 文案、引擎回退分支、训练进度映射、viewer 链接解析、上传缓存清理、相机采样回退、各档匹配策略。`venv/bin/python -m pytest tests/test_api_contract.py tests/test_services.py tests/test_security.py tests/test_route_map.py` 共 60 项通过；`npm run lint`、`npm run build`、`python -m compileall backend tests` 通过。

### 2026-06-16 文档与人工确认记录

- 用户已确认 focused cleanup 输出方向正确：`VID_20260612_091523_preview_final_clean_focused.ply` 清除了外围杂乱碎片，只保留主体；后续 `auto` / `object` 结果应保持这一类 focused 输出。
- 用户已确认 `VID_20260612_091523_high180_focused.ply` 质量较前一版明显提升，细节清晰且主体纯净；当前 12GB 机器的高质量默认继续按 180 帧、30k 迭代、2x 输入下采样记录。
- 用户已确认视频模型预览交互“初步看下来没什么大问题”：后续应保持模型侧 orientation 适配，不再通过相机侧极角或 up 向量硬修画面，避免重新引入左右拖拽 roll。
- 文档同步范围：OpenSpec proposal/design/spec/tasks、`.agents/rules`、中文/英文 README。README 中视频推理已验证平台仅记录 Windows + NVIDIA RTX 5070 Ti Laptop GPU 12GB。
- 日志策略已在规则中沉淀：默认 INFO 只显示关键阶段和失败摘要，HTTP 请求日志与外部工具逐行输出仅在 `SHARP_HTTP_LOGS=1`、`SHARP_LOG_LEVEL=DEBUG` 或 verbose 模式启用。
