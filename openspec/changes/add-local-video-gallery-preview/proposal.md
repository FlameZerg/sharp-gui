## Why

现有本地图库已经能优雅浏览和预览照片，但用户的相册目录通常也包含视频；如果视频只能被忽略，图库体验会割裂，也无法承担“本地/NAS 媒体浏览”的完整场景。

这次变更希望在保持现有 Apple 毛玻璃视觉风格和大相册流畅性的前提下，让图库支持常见视频文件的加载、筛选、预览和下载。

## What Changes

- 将现有照片图库扩展为图片与视频都可浏览的本地媒体图库，保留照片浏览、下载、选择和转 3D 的既有体验。
- 新增图库类型筛选：全部、照片、视频；筛选状态应影响列表内容、总数展示和空状态文案。
- 新增视频卡片表现：视频封面、播放标识、时长、分辨率/规格信息，并与现有瀑布流和密度控制保持一致。
- 新增视频预览界面：支持播放/暂停、拖动进度、移动端长按拖动画面精细控制进度、音量/静音、全屏/退出、下载、关闭和前后媒体切换。
- 支持常见 SDR 视频的浏览与预览，优先使用浏览器原生硬件解码能力；对无法播放的视频提供清晰的错误提示和下载入口。
- 支持 PC 与移动端适配，包含鼠标、触控、键盘和小屏布局。
- 新增 UI 设计图作为方案参考，展示 PC 端图库、PC 端视频预览、移动端图库与移动端视频预览。
- 不包含视频转 3D、视频剪辑、字幕编辑、云端同步、多用户协作、DRM、HDR 色彩管理或默认生成多码率流媒体服务。

## Capabilities

### New Capabilities

- `local-video-gallery-preview`: 覆盖本地视频文件扫描、元数据展示、封面、预览播放、下载、播放失败提示和跨端交互。

### Modified Capabilities

- `local-photo-album-gallery`: 将照片图库的浏览要求扩展为混合媒体浏览，并新增全部/照片/视频类型筛选；照片既有转换、下载和预览行为保持兼容。

## Impact

- 后端服务与路由：`backend/services/photo_gallery.py`、`backend/routes/photo_gallery.py`，可能新增媒体相关服务模块或端点。
- 后端路径与缓存：`backend/paths.py` 中的 `.photo-gallery-cache` 索引、缩略图/封面缓存策略需要扩展。
- 权限与安全：`backend/security/access_control.py` 需要覆盖新增媒体预览、封面、下载和可选处理端点。
- 前端 API 与类型：`frontend/src/api/photoGallery.ts`、`frontend/src/types/photoGallery.ts` 需要表达媒体类型、视频元数据和筛选参数。
- 前端状态与组件：`frontend/src/store/useAppStore.ts`、`frontend/src/components/photoGallery/*`、`frontend/src/components/common/ImageViewer/*` 需要支持媒体预览和视频播放器。
- 样式与国际化：新增 CSS Modules、`frontend/src/i18n/en.json`、`frontend/src/i18n/zh.json` 文案。
- 可选依赖/工具：评估是否引入 FFmpeg/ffprobe 用于视频元数据读取和封面抽帧；前端播放器库优先避免重依赖。
- 测试：需要覆盖媒体扫描、路径安全、Range/下载、筛选、权限矩阵、API 契约和前端基础交互。
