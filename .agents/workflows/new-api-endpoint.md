# 工作流：添加新 API 端点

## 概述

添加一个新的 API 端点需要同时修改 **后端（Flask routes/services/security）** 和 **前端（React api/types）** 的多个文件。`app.py` 只是兼容入口，新增业务端点不要写回 `app.py`。

---

## 步骤

### 1. 后端：选择 route 模块

在 `backend/routes/` 中选择对应业务域：

| 业务域 | Route 模块 |
|------|------------|
| 认证/门禁 | `auth.py` |
| 模型图库/上传生成 | `gallery.py` |
| 本地照片图库/相册上传/照片转 3D | `photo_gallery.py` |
| 任务队列 | `tasks.py` |
| 设置/重启/文件夹选择 | `settings.py` |
| `/files/*` 静态文件 | `files.py` |
| 独立 HTML 导出 | `export.py` |
| React/Legacy 入口与 assets | `frontend.py` |

```python
@bp.route('/api/my-endpoint', methods=['POST'])
def api_my_endpoint():
    """端点功能描述（中文）"""
    data = request.get_json() or {}
    result = my_service.process_data(data)
    return jsonify({"success": True, "data": result})
```

**规则**：
- 路由必须以 `/api/` 开头
- 函数名使用 `snake_case`
- 返回 JSON（`jsonify()`）
- 错误返回 `{"error": "msg"}` + 对应状态码
- 添加中文 docstring
- route 层只处理 HTTP 输入输出，不写大段业务流程

### 2. 后端：必要时添加 service

可复用业务逻辑放到 `backend/services/`：

```python
def process_data(data):
    """服务逻辑描述。"""
    return {"value": data.get("value")}
```

照片相册上传、路径解析、文件写入、任务队列、导出、模型转换等高风险逻辑必须在 service 层保持可测试。

### 3. 后端：同步权限矩阵

在 `backend/security/access_control.py` 的 `get_required_access_level()` 中明确新端点访问级别：

- Public：无需访问码，如 `/api/auth/status`
- Unlocked：本机 owner 或已解锁远程设备可访问
- Owner：真实 localhost 且 Host 允许
- Conditional：根据门禁配置切换，如 `/api/generate`

owner 判断只能使用真实 `request.remote_addr` + 允许的 Host，不能相信 `X-Forwarded-For`、`Forwarded`、`X-Real-IP` 等客户端可控头。

### 4. 后端：补充 pytest

根据风险补充 `tests/`：

- route map：端点注册完整
- 安全：Public / Unlocked / Owner / Conditional 矩阵
- 服务：路径归一化、文件名净化、任务状态、纯函数
- API contract：关键响应字段和状态码

运行：

```bash
python -m pytest -q
```

### 5. 前端：定义类型

在 `frontend/src/types/` 对应文件中添加（或创建新文件）：

```typescript
export interface MyRequest {
  param1: string;
  param2: number;
}

export interface MyResponse {
  success: boolean;
  data: MyData;
}
```

如创建了新的类型文件，需在 `types/index.ts` 中添加导出。

### 6. 前端：添加 API 调用函数

在 `frontend/src/api/` 对应模块中添加（或创建新模块文件）：

```typescript
import { apiPost } from './client';
import type { MyRequest, MyResponse } from '@/types';

export async function myEndpoint(data: MyRequest): Promise<MyResponse> {
  return apiPost<MyResponse>('/api/my-endpoint', data);
}
```

**使用正确的 HTTP 方法对应函数**：

| 后端方法 | 前端函数 |
|----------|----------|
| GET | `apiGet<T>()` |
| POST (JSON) | `apiPost<T>()` |
| POST (文件) | `apiPostFormData<T>()` |
| DELETE | `apiDelete<T>()` |

如创建了新的 API 模块文件，需在 `api/index.ts` 中添加导出。

### 7. 前端：在组件/Hook 中调用

```typescript
import { myEndpoint } from '@/api';
import type { MyRequest } from '@/types';

const handleSubmit = async () => {
  try {
    const result = await myEndpoint({ param1: 'value', param2: 42 });
  } catch (error) {
    // 错误处理
  }
};
```

---

## 检查清单

- [ ] 后端 route 放在 `backend/routes/` 对应模块
- [ ] 可复用业务逻辑放在 `backend/services/`
- [ ] 后端路由以 `/api/` 开头
- [ ] 后端函数有中文 docstring
- [ ] 后端返回统一的 JSON 格式
- [ ] 后端错误处理使用明确状态码
- [ ] `backend/security/access_control.py` 权限矩阵已确认
- [ ] 如涉及文件/路径/权限/任务，已补 pytest
- [ ] 前端类型定义在 `types/` 中，并在 `index.ts` 中导出
- [ ] 前端 API 函数使用 `client.ts` 的封装方法
- [ ] 前端 API 函数在 `api/index.ts` 中导出
- [ ] 使用 `import type` 导入纯类型
- [ ] 如有用户可见的错误/提示文本，已添加 i18n

---

## 现有端点参考

| 方法 | 路径 | 前端函数 | 类型 |
|------|------|----------|------|
| GET | `/api/gallery` | `fetchGallery()` | `GalleryListResponse` |
| POST | `/api/generate` | `generateFromImages()` | `GenerateResponse` |
| GET | `/api/tasks` | `fetchTasks()` | `TasksResponse` |
| POST | `/api/task/<id>/cancel` | `cancelTask()` | — |
| DELETE | `/api/delete/<id>` | `deleteGalleryItem()` | — |
| GET | `/api/download/<id>` | `downloadModel()` | Blob |
| GET | `/api/export/<id>` | `exportModel()` | Blob |
| GET | `/api/settings` | `fetchSettings()` | `SettingsData` |
| POST | `/api/settings` | `saveSettings()` | — |
| POST | `/api/browse-folder` | `browseFolder()` | `{ path }` |
| POST | `/api/restart` | `restartServer()` | — |
| GET | `/api/photo-albums` | `fetchPhotoAlbums()` | `PhotoAlbumListResponse` |
| POST | `/api/photo-albums/<id>/uploads` | `uploadPhotosToAlbum()` | `PhotoUploadResponse` |
