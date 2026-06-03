# 后端开发规范

## 架构概述

后端是一个 **单文件 Flask 应用**（`app.py`，约 2,000 行），承担以下职责：

1. **REST API 服务** — 处理前端请求，返回 JSON
2. **静态文件服务** — 提供图片和模型文件
3. **任务队列** — `queue.Queue` + 后台 Worker 线程调用 `sharp predict` 推理
4. **文件管理** — 图片上传、模型存储、缩略图生成、本地照片图库索引/缩略图、PLY→SPZ 自动转换、历史 PLY→Splat 导出兼容
5. **配置管理** — `config.json` 读写
6. **安全** — CORS、HTTPS、局域网门禁、仅本机可修改设置

---

## API 端点清单

### LAN access-control tiers

- **Public**: `/`, React assets/root static files, `/api/auth/status`, `/api/auth/login`.
- **Unlocked**: valid HttpOnly access session or localhost owner. Covers gallery/task reads, model/photo previews, downloads, exports, photo album reads, and `/files/*`.
- **Owner**: real localhost request with allowed Host. Covers settings writes, folder management, deletes, restart, batch conversion, task cancel, and access-control management.
- **Conditional**: `/api/generate` and `/api/photo-conversions` are Owner by default; when `access_control.enabled=true` and `access_control.allow_remote_generation=true`, Unlocked remote devices may submit them.

When `access_control.enabled=false`, private read resources fall back to the old open LAN browsing behavior, but Owner endpoints must still enforce real localhost access. Disabling the gate must not make delete, settings, restart, folder management, batch conversion, or task cancellation remote-accessible.

Do not grant owner permissions from `X-Forwarded-For`, `Forwarded`, `X-Real-IP`, or other client-controlled headers. New private endpoints must be added to `get_required_access_level()` in `app.py`; unknown `/api/*` and `/files/*` requests should remain Unlocked by default.

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/auth/status` | 认证状态、owner 状态和门禁配置摘要 | Public |
| POST | `/api/auth/login` | 使用访问码创建 HttpOnly Cookie 会话 | Public |
| POST | `/api/auth/logout` | 清除当前设备会话 | Unlocked |
| POST | `/api/auth/access-code` | 设置或修改访问码 | Owner |
| POST | `/api/auth/revoke` | 撤销所有远程会话 | Owner |
| POST | `/api/auth/settings` | 更新门禁启用状态、会话天数、远程生成等配置 | Owner |
| GET | `/api/gallery` | 获取作品列表 | Unlocked |
| POST | `/api/generate` | 上传图片生成模型 | Owner / Conditional |
| GET | `/api/tasks` | 获取任务队列状态 | Unlocked |
| POST | `/api/task/<id>/cancel` | 取消任务 | Owner |
| DELETE | `/api/delete/<id>` | 删除作品 | Owner |
| GET | `/api/download/<id>` | 下载模型文件（支持 `?format=spz|ply`） | Unlocked |
| GET | `/api/original/<id>` | 获取上传原图（inline 预览或附件下载） | Unlocked |
| GET | `/api/thumbnail/<id>` | 获取或按需修复缩略图 | Unlocked |
| POST | `/api/convert-all` | 批量将既有 PLY 转换为 SPZ | Owner |
| GET | `/api/settings` | 读取设置 | Unlocked |
| POST | `/api/settings` | 写入设置 | Owner |
| POST | `/api/restart` | 重启服务器 | Owner |
| POST | `/api/browse-folder` | 原生文件夹选择 | Owner |
| GET | `/api/export/<id>` | 导出为 Spark 2.0 独立 HTML（支持 `?format=spz|ply`） | Unlocked |
| GET | `/api/photo-albums` | 获取本地照片相册列表 | Unlocked |
| POST | `/api/photo-albums` | 新增照片相册目录配置 | Owner |
| DELETE | `/api/photo-albums/<album_id>` | 移除照片相册配置，不删除原图 | Owner |
| POST | `/api/photo-albums/<album_id>/scan` | 重新扫描照片相册 | Owner |
| GET | `/api/photo-albums/<album_id>/photos` | 分页获取照片，支持时间/名称/大小排序 | Unlocked |
| GET | `/api/photo-thumbnail/<photo_id>` | 获取或按需生成照片图库缩略图 | Unlocked |
| GET | `/api/photo-original/<photo_id>` | 获取照片原图（inline 或 `?download=1` 附件） | Unlocked |
| POST | `/api/photo-conversions` | 将单张/多张照片加入现有 3D 生成队列 | Owner / Conditional |

### 新增端点规则

1. **路由前缀**：必须使用 `/api/` 前缀
2. **返回格式**：统一返回 JSON（`jsonify()`）
3. **错误响应**：返回 `{"error": "描述"}` + 对应 HTTP 状态码
4. **权限控制**：在 `get_required_access_level()` 中明确 Public / Unlocked / Owner / Conditional；owner 判断只能使用真实 `request.remote_addr` + 允许的 Host，不能相信转发头

```python
# ✅ 标准路由模式
@app.route('/api/my-endpoint', methods=['GET'])
def api_my_endpoint():
    """获取某某数据"""
    try:
        result = do_something()
        return jsonify({"data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

## 任务队列系统

### 架构

```python
task_queue = queue.Queue()       # FIFO 任务队列
task_status = {}                 # 任务ID → 状态对象 (dict)
task_lock = threading.Lock()     # 线程安全锁
```

### 任务生命周期

```
pending → running → processing → completed
                  ↘ failed
                  ↘ cancelled
```

### 关键实现

- **Worker 线程**：后台线程从队列取任务，用 `subprocess` 调用 `sharp predict`
- **进度解析**：实时读取 subprocess 的 stdout，解析进度阶段（downloading → loading → preprocessing → inference → postprocessing → saving）
- **取消机制**：`process.terminate()` 终止子进程
- **自动清理**：已完成任务 1 小时后自动从内存中移除（`TASK_RETENTION_SECONDS`）

### 线程安全

修改 `task_status` 时 **必须** 使用 `task_lock`：

```python
with task_lock:
    task_status[task_id] = {
        'status': 'running',
        'progress': 0,
        'stage': 'loading'
    }
```

---

## 文件路径处理

### 工作目录结构

```python
workspace_folder = config.get('workspace_folder', BASE_DIR)
input_folder = os.path.join(workspace_folder, 'inputs')
output_folder = os.path.join(workspace_folder, 'outputs')
thumbnail_folder = os.path.join(input_folder, '.thumbnails')
photo_gallery_cache_folder = os.path.join(workspace_folder, '.photo-gallery-cache')
photo_thumbnail_folder = os.path.join(photo_gallery_cache_folder, 'thumbnails')
```

### 规则

- 使用 `os.path` 构造绝对路径，不使用字符串拼接
- `secure_filename()` 处理用户上传的文件名
- 缩略图存储在 `{workspace}/inputs/.thumbnails/`
- 本地照片图库索引与缩略图缓存存储在 `{workspace}/.photo-gallery-cache/`
- 输出目录同时保留 `.ply` 原始模型和自动生成的 `.spz` 紧凑模型
- 配置文件 `config.json` 位于项目根目录（`BASE_DIR`）
- 照片图库 API 只接受 photo id，不接受任意绝对路径；后端必须从索引反查原图并再次校验 root

---

## 配置管理

### config.json 结构

```json
{
  "workspace_folder": "/path/to/workspace",
  "model_format": "spz",
  "photo_gallery_roots": [
    {
      "id": "stable-root-id",
      "name": "Screenshots",
      "path": "D:/Pictures/Screenshots",
      "recursive": true,
      "enabled": true
    }
  ],
  "access_control": {
    "enabled": false,
    "session_days": 30,
    "allow_remote_generation": false,
    "lan_bind_enabled": true
  }
}
```

### 兼容性

代码需兼容旧配置格式（`input_folder` / `output_folder`）到新格式（`workspace_folder`）的自动迁移。

`model_format` 控制前端默认查看和下载格式，当前有效值为 `spz` / `ply`。

`photo_gallery_roots` 控制本地照片图库相册目录；缺省时按空数组处理，不影响旧配置启动。

`access_control` 控制可选局域网门禁；缺省或 `enabled=false` 时读取资源保持旧的局域网开放行为，但 owner-only 端点仍必须限制真实 localhost。`lan_bind_enabled`（缺省 `true`）决定服务监听 `0.0.0.0`（局域网共享）还是 `127.0.0.1`（仅本机），修改后需重启生效。

---

## CORS 处理

通过 `after_request` 钩子手动添加。启用 Cookie 会话后，不允许继续对凭证请求返回 `Access-Control-Allow-Origin: *`；只能回显通过 `is_origin_allowed()` 校验的 origin，并设置 `Access-Control-Allow-Credentials: true`：

```python
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin and is_origin_allowed(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers.add('Vary', 'Origin')
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response
```

不使用 `flask-cors` 扩展。

---

## HTTPS 与监听绑定

- 自动检测项目根目录下的 `cert.pem` / `key.pem`
- 有证书时使用 `ssl_context`；无证书时 fallback 到 HTTP（此时访问码/会话明文传输，前端会提示）
- 证书由 `tools/generate_cert.py` 生成
- **监听地址**由 `access_control.lan_bind_enabled` 决定：`true` → `0.0.0.0`（局域网共享），`false` → `127.0.0.1`（仅本机）。环境变量 `SHARP_BIND_HOST` 可覆盖。修改该开关需重启服务生效（前端保存后自动重启）。
- **调试模式默认关闭**：`app.run` 默认 `debug=False`、`use_debugger=False`、`use_reloader=False`，避免向客户端泄露堆栈与 RCE 风险，并防止 Werkzeug reloader 的 socket 继承机制干扰 `/api/restart` 的重新绑定（见下方重启说明）。仅 `SHARP_DEBUG=1` 时三者同时开启，且只应在本机排障使用。
- **`/api/restart` 的重新绑定机制**：`do_restart` 使用 `os.execv` 替换进程映像来实现重启，这样可以读取最新的 `config.json`（包括切换后的 `lan_bind_enabled`）。重启前必须调用 `os.closerange(3, max_fds)` 关闭所有继承的 FD（尤其是监听 socket），否则 execv 后新映像尝试重新 bind 时会遇到 `Address already in use` 而崩溃，导致绑定"假切换"。`use_reloader=False` 也是必要条件：reloader 开启时父进程持有 socket 并通过 `WERKZEUG_SERVER_FD` 传给子进程，无法通过 `closerange` 干净释放。

## 静态文件服务（/files/*）

`/files/<path>` 由 `serve_files` 提供，**收敛到白名单服务根**，不再以 `BASE_DIR` 为默认根：

- 仅允许 `ALLOWED_FILE_SERVE_ROOTS`（`outputs/` 模型与 `inputs/.thumbnails/` 历史缩略图）内的文件。
- 解析后的真实路径用 `is_real_path_inside` 校验（基于 `realpath` + `commonpath`），落在白名单外、相对穿越、绝对路径或符号链接逃逸一律 404。
- 命中敏感清单（`config.json`、`*.pem`、`*.key`、`app.py`、`.env` 等）一律 404，**不区分“不存在”与“被禁”**以避免信息泄露。
- 该校验独立于门禁开关：即便 `access_control.enabled=false`，敏感系统文件也不会通过 `/files/*` 暴露。
- 新增需要对外提供的静态目录时，必须显式加入 `ALLOWED_FILE_SERVE_ROOTS`，不要放宽回 `BASE_DIR`。

---

## 外部工具脚本

| 文件 | 功能 | 调用方式 |
|------|------|----------|
| `tools/detect_cuda.py` | 解析 `nvidia-smi` 获取 CUDA 版本 | 安装阶段 |
| `tools/download_model.py` | 多源下载模型（HF → HF 镜像 → Apple CDN）| 安装阶段 |
| `tools/generate_cert.py` | 跨平台生成自签名 SSL 证书 | 安装阶段 / 手动 |
| `tools/install_torch.py` | 根据 CPU/CUDA 环境安装兼容 PyTorch | 安装阶段 |
| `tools/update.py` | GitHub Releases 自动更新（避免 rate limit）| update.sh |

---

## 安全要点

> 虽然是个人项目 + 局域网使用场景，但以下基础防线仍需遵守：

### 文件上传

- **必须** 使用 `secure_filename()` 清理用户上传的文件名
- **必须** 校验文件扩展名白名单（`.jpg`, `.jpeg`, `.png`, `.webp`）
- **禁止** 直接拼接用户输入到文件路径（防路径遍历）

```python
# ✅ 正确
from werkzeug.utils import secure_filename
filename = secure_filename(uploaded_file.filename)
full_path = os.path.join(input_folder, filename)

# ❌ 危险 — 用户可构造 ../../etc/passwd
full_path = os.path.join(input_folder, request.form['filename'])
```

### 路径构造

- 使用 `os.path.join()` 而非字符串拼接
- 涉及用户输入的路径，用 `os.path.abspath()` + `startswith()` 验证不会逃逸工作目录：

```python
resolved = os.path.abspath(os.path.join(workspace, user_input))
if not resolved.startswith(os.path.abspath(workspace)):
    return jsonify({"error": "Invalid path"}), 403
```

### 本地照片图库路径安全

- 照片相册新增、删除、重新扫描这类配置写操作必须仅允许 localhost。
- 原图、缩略图、下载、转换接口必须通过 photo id 解析，不能接受前端传来的绝对路径。
- 解析 photo id 后必须使用 `os.path.abspath()`、`os.path.realpath()`、`os.path.commonpath()` 和平台大小写归一化确认文件仍在配置 root 内。
- Windows 需要避免跨盘符 `commonpath` 抛错导致接口 500；Linux/macOS 需要避免符号链接逃逸相册 root。
- 原图响应优先使用 `send_from_directory(..., download_name=...)` 交给 Werkzeug 生成兼容的 `Content-Disposition`，不要手写包含中文的 header。

### 其他

- **仅 localhost 可写入**的端点需检查 `request.remote_addr`
- **局域网门禁**关闭时只放开私有读取资源，不得放开设置、删除、重启、目录管理、取消任务等 owner-only 操作
- **Owner 判断**只能信任真实连接地址和允许的 Host，不得使用 `X-Forwarded-For`、`Forwarded`、`X-Real-IP` 等客户端可控头
- **静态文件服务**只能从 `ALLOWED_FILE_SERVE_ROOTS` 白名单根提供，敏感文件（`config.json`、证书私钥、`app.py` 等）必须拒绝；该限制不随门禁开关放宽
- **调试模式**默认关闭，不向客户端返回堆栈、不暴露交互式调试器；仅 `SHARP_DEBUG=1` 本机排障时开启
- **反向代理**：若本机前置反向代理，所有请求 `remote_addr` 会变成 `127.0.0.1` 导致全员被判 owner；文档需提示用户在反代场景关闭 `allow_localhost_bypass`（需先设访问码）
- **subprocess 调用**使用列表参数（非字符串拼接），避免命令注入
- **不要**在 JSON 响应中暴露服务器绝对路径或堆栈信息

---

## 编码风格

- **函数命名**：`snake_case`（如 `load_config`, `ply_to_splat`）
- **常量命名**：`UPPER_CASE`（如 `TASK_RETENTION_SECONDS`）
- **注释语言**：中文 docstring + 中文行内注释
- **日志**：`print()` + emoji 前缀（如 `🔄 Processing task`、`✅ Task completed`）
- **错误处理**：`try/except Exception as e`，避免裸 `except:`
- **类型注解**：当前无强制要求，鼓励在新代码中添加
- **导入风格**：标准库可合并一行（`import os, sys, json`），三方库分开导入
