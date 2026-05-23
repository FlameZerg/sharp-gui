## 1. 基础方案与数据契约

- [x] 1.1 定义 `photo_gallery_roots` 配置结构，兼容旧 `config.json` 缺省字段。
- [x] 1.2 定义后端相册、照片条目、分页响应、扫描状态和转换响应的数据结构。
- [x] 1.3 定义前端 `PhotoAlbum`、`PhotoItem`、`PhotoListResponse`、`PhotoConversionResponse` 类型，并从 `types/index.ts` 导出。
- [x] 1.4 明确照片 ID 生成与解析规则，确保 API 不暴露绝对路径。

## 2. 后端目录、扫描与安全

- [x] 2.1 在 `app.py` 中新增照片图库配置读取/保存逻辑，目录新增/删除仅允许 localhost。
- [x] 2.2 新增路径归一化与 root 校验工具，覆盖 Windows 跨盘符、大小写、POSIX 路径、符号链接和路径遍历。
- [x] 2.3 新增相册扫描逻辑，支持允许的图片扩展名、递归选项、错误隔离和更新时间统计。
- [x] 2.4 新增轻量索引/缓存文件，记录照片相对路径、mtime、size、尺寸和缩略图版本。
- [x] 2.5 新增相册列表 API：`GET /api/photo-albums`。
- [x] 2.6 新增相册配置 API：`POST /api/photo-albums`、`DELETE /api/photo-albums/<album_id>`、`POST /api/photo-albums/<album_id>/scan`。

## 3. 后端缩略图、预览、下载与转换

- [x] 3.1 新增照片列表分页 API：`GET /api/photo-albums/<album_id>/photos`，支持 cursor、limit、sort。
- [x] 3.2 新增照片缩略图缓存生成与服务 API：`GET /api/photo-thumbnail/<photo_id>`。
- [x] 3.3 新增照片原图预览/下载 API：`GET /api/photo-original/<photo_id>?download=1`。
- [x] 3.4 新增照片转 3D API：`POST /api/photo-conversions`，接收单张或多张 photo id。
- [x] 3.5 转换 API 复用现有任务队列：复制源图到 `inputs/`，生成安全唯一文件名，创建任务并返回任务列表。
- [x] 3.6 给缩略图与原图响应设置合适的缓存、Content-Disposition 和错误响应。

## 4. 前端 API、状态与入口

- [x] 4.1 新增 `frontend/src/api/photoGallery.ts`，使用项目 `apiGet` / `apiPost` / `apiDelete` 封装新增端点。
- [x] 4.2 在 `frontend/src/api/index.ts` 导出照片图库 API。
- [x] 4.3 扩展 Zustand store：新增 `activeView`、相册列表、当前相册、照片分页、多选集合、扫描状态。
- [x] 4.4 在 Sidebar 中新增 `模型 / 照片` 分段入口，保持现有模型视图默认行为。
- [x] 4.5 在 `App.tsx` 中按 `activeView` 切换主区域：模型查看器或照片图库工作区。

## 5. 前端照片图库 UI

- [x] 5.1 新增 `components/photoGallery/PhotoGalleryView` 三件套，承载照片图库主工作区。
- [x] 5.2 新增 `PhotoAlbumList` 三件套，展示相册封面、数量、扫描状态和添加目录入口。
- [x] 5.3 新增 `PhotoMasonryGrid` 三件套，支持响应式列数、稳定 aspect ratio、懒加载、空态和错误态。
- [x] 5.4 新增 `PhotoToolbar` 三件套，支持排序、选择模式、刷新扫描和当前相册信息。
- [x] 5.5 新增 `PhotoSelectionBar` 三件套，支持选中数量、批量转换为 3D 和清空选择。
- [x] 5.6 UI 使用 CSS Modules、现有 CSS Variables、玻璃态面板和项目图标风格，不引入新样式框架。

## 6. 图片预览增强与 3D 转换体验

- [x] 6.1 将现有 `ImageViewer` 扩展为支持模型图库图片和照片图库图片两种来源，或抽取通用预览组件。
- [x] 6.2 照片预览支持下载、上一张/下一张、生成 3D、文件信息和关闭。
- [x] 6.3 照片卡片支持单张快捷生成 3D，预览层支持一键生成 3D。
- [x] 6.4 批量转换提交成功后同步任务队列状态，并提示用户可切换到 `模型` 视图查看进度。
- [x] 6.5 转换错误需要显示可理解的错误反馈，不吞掉部分成功任务。

## 7. 国际化、可访问性与响应式

- [x] 7.1 在 `frontend/src/i18n/en.json` 和 `frontend/src/i18n/zh.json` 同步新增所有用户可见文案，key 使用 camelCase。
- [x] 7.2 所有按钮、图标按钮、相册卡片、照片选择控件提供 aria-label/title/focus-visible 状态。
- [x] 7.3 移动端触控设备不依赖 hover 才能发现关键操作。
- [ ] 7.4 验证 375、768、1024、1440 宽度下无横向滚动、文字不溢出、浮层不遮挡关键操作。
- [x] 7.5 明显动画遵循 `prefers-reduced-motion`。

## 8. 性能与跨平台验证

- [ ] 8.1 用包含至少 1000 张图片的测试目录验证分页、缩略图缓存和瀑布流滚动性能。
- [x] 8.2 验证列表请求不加载原图，只有预览/下载时请求原图。
- [ ] 8.3 验证 Windows 路径、Linux/macOS POSIX 路径、中文文件名、空格文件名和网络/挂载目录错误状态。
- [ ] 8.4 验证构造非法 photo id、相对路径逃逸和 root 外路径访问均被拒绝。
- [ ] 8.5 运行前端 lint/build 和可用的后端测试或 smoke test。
- [ ] 8.6 回归现有模型上传、任务队列、模型图库、原图预览、模型下载和 3D 查看器不受影响。

## 9. 文档与归档准备

- [x] 9.1 将 OpenSpec proposal/design/spec 更新到当前实现，包括原图预览、非原生控件、排序、图库密度和移动端捏合细节。
- [x] 9.2 更新 Agent 入口与规则文档，记录照片图库 API、前端结构、样式约束、i18n 和验证清单。
- [x] 9.3 更新 README / README.en，补充本地照片图库能力、使用说明、配置与截图占位。
- [x] 9.4 更新 `docs/index.html` 产品介绍主页，新增照片图库展示区并预留共用截图占位。

## 10. 归档前待人工确认

- [ ] 10.1 用户补充并确认共用截图：`docs/images/photo-gallery.png`。
- [ ] 10.2 用户确认当前 UI 与交互效果满意后，再执行 OpenSpec 归档。

## 验证记录

- 已验证：照片列表返回缩略图 URL，预览/下载使用原图 URL；中文和空格文件名可返回原图与缩略图；非法 photo id 返回 404；前端生产构建与 `app.py` py_compile 曾通过。
- 待补：完整 `npm run lint` 仍受现有 legacy lint 问题影响；1000+ 图片目录、Linux/macOS 路径、完整路径逃逸用例和现有模型主流程回归仍需人工或目标环境验证。
