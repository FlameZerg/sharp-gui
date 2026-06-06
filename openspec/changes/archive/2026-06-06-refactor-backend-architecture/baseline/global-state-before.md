## app.py 重构前全局状态与副作用清单

### 路径与配置

- `BASE_DIR`: 项目根目录。
- `CONFIG_FILE`: `BASE_DIR/config.json`。
- `DEFAULT_WORKSPACE_FOLDER`: 默认工作区为项目根目录。
- `WORKSPACE_FOLDER`: 从 `config.json` 的 `workspace_folder` 派生。
- `INPUT_FOLDER`: `{workspace}/inputs`。
- `OUTPUT_FOLDER`: `{workspace}/outputs`。
- `THUMBNAIL_FOLDER`: `{workspace}/inputs/.thumbnails`。
- `PHOTO_GALLERY_CACHE_FOLDER`: `{workspace}/.photo-gallery-cache`。
- `PHOTO_THUMBNAIL_FOLDER`: `{workspace}/.photo-gallery-cache/thumbnails`。
- `PHOTO_INDEX_FILE`: `{workspace}/.photo-gallery-cache/index.json`。
- `ALLOWED_FILE_SERVE_ROOTS`: `OUTPUT_FOLDER` 与 `THUMBNAIL_FOLDER`。

### 运行时环境变量

- `SHARP_FRONTEND_MODE`: `react` 或 `legacy`。
- `SHARP_VERBOSE`: 开启详细日志。
- `SHARP_LOG_LEVEL`: verbose 时默认 `DEBUG`，否则 `INFO`。
- `SHARP_LOG_FILE`: verbose tee 日志文件。
- `SHARP_DEBUG`: 控制 Flask debugger/reloader/debug。
- `SHARP_DEVICE`: 覆盖推理设备。
- `SHARP_LAN_IP`: 覆盖启动日志展示的局域网 IP。
- `SHARP_BIND_HOST`: 覆盖监听地址。

### 安全与门禁状态

- `ACCESS_COOKIE_NAME`: `sharp_gui_access`。
- `ACCESS_PUBLIC` / `ACCESS_UNLOCKED` / `ACCESS_OWNER`: 访问级别常量。
- `login_failure_lock`: 登录失败节流锁。
- `login_failures`: 按远端地址记录登录失败时间戳。
- `get_required_access_level()`: 集中权限矩阵，包含照片相册上传条件权限。

### 照片图库状态

- `photo_index_lock`: 保护照片索引读写。
- `PHOTO_MAX_UPLOAD_BATCH`: 照片相册上传批量上限，当前为 `100`。
- `PHOTO_MAX_CONVERSION_BATCH`: 照片转 3D 批量上限，当前为 `100`。
- `PHOTO_MAX_DOWNLOAD_BATCH`: 照片下载 ZIP 批量上限，当前为 `200`。

### 任务队列状态

- `task_queue`: `queue.Queue()`。
- `task_status`: 任务 ID 到状态对象的字典。
- `task_lock`: 保护 `task_status` 与 `running_processes`。
- `running_processes`: 任务 ID 到运行中 subprocess 的字典。
- `TASK_RETENTION_SECONDS`: 完成/失败任务保留 3600 秒。
- `CLEANUP_INTERVAL`: 清理线程每 300 秒运行。

### 导入时副作用

- 导入 `app.py` 时创建 Flask app。
- 导入时读取并可能写回 `config.json`，补齐 access-control 默认值和 session secret。
- 导入时创建 workspace、inputs、outputs、缩略图、照片缓存目录。
- 导入时启用 verbose tee 日志文件。
- 导入时启动 worker 线程。
- 导入时启动任务清理线程。

### 重构后目标

- `from app import app` 仍可用，但不启动 worker/cleanup 线程。
- `python app.py` 或现有启动脚本运行服务时，由 `run_server(app)` 显式启动后台线程。
- 路径、配置、安全、任务和照片索引状态都收敛到 `backend/` 模块中的单一来源。
