# 后端开发规范

## 架构概述

后端是一个 **单文件 Flask 应用**（`app.py`，约 1,340 行），承担以下职责：

1. **REST API 服务** — 处理前端请求，返回 JSON
2. **静态文件服务** — 提供图片和模型文件
3. **任务队列** — `queue.Queue` + 后台 Worker 线程调用 `sharp predict` 推理
4. **文件管理** — 图片上传、模型存储、缩略图生成、PLY→SPZ 自动转换、历史 PLY→Splat 导出兼容
5. **配置管理** — `config.json` 读写
6. **安全** — CORS、HTTPS、仅本机可修改设置

---

## API 端点清单

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/api/gallery` | 获取作品列表 | 全部 |
| POST | `/api/generate` | 上传图片生成模型 | 全部 |
| GET | `/api/tasks` | 获取任务队列状态 | 全部 |
| POST | `/api/task/<id>/cancel` | 取消任务 | 全部 |
| DELETE | `/api/delete/<id>` | 删除作品 | 全部 |
| GET | `/api/download/<id>` | 下载模型文件（支持 `?format=spz|ply`） | 全部 |
| GET | `/api/original/<id>` | 获取上传原图（inline 预览或附件下载） | 全部 |
| GET | `/api/thumbnail/<id>` | 获取或按需修复缩略图 | 全部 |
| POST | `/api/convert-all` | 批量将既有 PLY 转换为 SPZ | 仅 localhost |
| GET | `/api/settings` | 读取设置 | 全部 |
| POST | `/api/settings` | 写入设置 | 仅 localhost |
| POST | `/api/restart` | 重启服务器 | 仅 localhost |
| POST | `/api/browse-folder` | 原生文件夹选择 | 仅 localhost |
| GET | `/api/export/<id>` | 导出为 Spark 2.0 独立 HTML（支持 `?format=spz|ply`） | 全部 |

### 新增端点规则

1. **路由前缀**：必须使用 `/api/` 前缀
2. **返回格式**：统一返回 JSON（`jsonify()`）
3. **错误响应**：返回 `{"error": "描述"}` + 对应 HTTP 状态码
4. **权限控制**：敏感操作（修改配置、重启）需验证 `request.remote_addr` 是否为本机

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
```

### 规则

- 使用 `os.path` 构造绝对路径，不使用字符串拼接
- `secure_filename()` 处理用户上传的文件名
- 缩略图存储在 `{workspace}/inputs/.thumbnails/`
- 输出目录同时保留 `.ply` 原始模型和自动生成的 `.spz` 紧凑模型
- 配置文件 `config.json` 位于项目根目录（`BASE_DIR`）

---

## 配置管理

### config.json 结构

```json
{
  "workspace_folder": "/path/to/workspace",
  "model_format": "spz"
}
```

### 兼容性

代码需兼容旧配置格式（`input_folder` / `output_folder`）到新格式（`workspace_folder`）的自动迁移。

`model_format` 控制前端默认查看和下载格式，当前有效值为 `spz` / `ply`。

---

## CORS 处理

通过 `after_request` 钩子手动添加：

```python
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
    return response
```

不使用 `flask-cors` 扩展。

---

## HTTPS

- 自动检测项目根目录下的 `cert.pem` / `key.pem`
- 有证书时使用 `ssl_context`；无证书时 fallback 到 HTTP
- 证书由 `tools/generate_cert.py` 生成

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

### 其他

- **仅 localhost 可写入**的端点需检查 `request.remote_addr`
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
