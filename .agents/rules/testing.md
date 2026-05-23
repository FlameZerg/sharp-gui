# 测试规范

## 现状

项目当前 **无测试覆盖**：

- 无测试文件（`.test.*`、`.spec.*`、`test_*.py`）
- 无测试框架依赖（package.json 中无 jest/vitest/testing-library；无 pytest 安装）
- ml-sharp 子项目的 `pyproject.toml` 配置了 pytest 路径，但未创建实际测试

---

## 测试目标

鼓励为新功能添加测试，优先覆盖以下关键路径：

| 优先级 | 覆盖范围 | 说明 |
|--------|----------|------|
| 🔴 高 | 后端 API 端点 | 确保 `/api/*` 请求/响应正确 |
| 🔴 高 | 工具函数 | `utils/format.ts`, `utils/camera.ts`, `ply_to_splat()` 等纯函数 |
| 🟡 中 | 前端组件 | 关键交互组件（Button, Modal, GalleryItem） |
| 🟡 中 | Zustand Store | Action 逻辑正确性 |
| 🟢 低 | 自定义 Hooks | 需要模拟 3D 环境，复杂度较高 |

### 本地照片图库 smoke checklist

照片图库属于大功能，当前若暂不引入测试框架，至少应手动或脚本化验证：

- `GET/POST/DELETE /api/photo-albums`、`POST /scan`、`GET /photos`、`GET /photo-thumbnail`、`GET /photo-original`、`POST /api/photo-conversions` 的成功与错误路径。
- 列表返回 `thumb_url`，预览/下载使用 `full_url` 或 `preview_url` 原图地址，不能把缩略图放大当原图。
- 中文、空格、大小写混合文件名可以生成缩略图、打开原图、下载和加入 3D 队列。
- 构造非法 photo id、相对路径逃逸和 root 外路径访问会被拒绝。
- 至少一个 1000+ 图片目录验证分页、缩略图缓存和瀑布流滚动性能。
- Windows、Linux、macOS 或挂载/NAS 路径至少做路径配置与不可用目录错误状态验证。

---

## 推荐框架

### 前端

| 工具 | 用途 |
|------|------|
| **Vitest** | 测试运行器（与 Vite 生态一致） |
| **@testing-library/react** | React 组件测试 |
| **@testing-library/jest-dom** | DOM 断言增强 |
| **happy-dom** 或 **jsdom** | DOM 环境模拟 |

安装命令（若需添加）：
```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom happy-dom
```

### 后端

| 工具 | 用途 |
|------|------|
| **pytest** | 测试运行器 |
| **pytest-flask** | Flask 应用测试辅助 |

---

## 文件命名约定

| 平台 | 命名模式 | 位置 |
|------|----------|------|
| 前端组件测试 | `ComponentName.test.tsx` | 组件目录内 |
| 前端工具函数 | `format.test.ts` | `utils/` 目录内（与源文件同级） |
| 前端 Hook | `useViewer.test.ts` | `hooks/` 目录内 |
| 后端 API | `test_api.py` | 项目根目录 `tests/` |
| 后端工具 | `test_ply_to_splat.py` | 项目根目录 `tests/` |

### 文件结构示例

```
frontend/src/
├── utils/
│   ├── format.ts
│   └── format.test.ts          # 工具函数测试
├── components/common/Button/
│   ├── Button.tsx
│   ├── Button.module.css
│   ├── Button.test.tsx          # 组件测试
│   └── index.ts

tests/                            # 后端测试（项目根目录）
├── test_api.py
├── test_ply_to_splat.py
└── conftest.py                   # pytest fixtures
```

---

## 测试编写指南

### 前端工具函数测试示例

```typescript
// utils/format.test.ts
import { describe, it, expect } from 'vitest';
import { formatFileSize, debounce } from './format';

describe('formatFileSize', () => {
  it('formats bytes correctly', () => {
    expect(formatFileSize(0)).toBe('0 B');
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1048576)).toBe('1.0 MB');
  });
});
```

### 前端组件测试示例

```typescript
// Button/Button.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick handler', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);
    fireEvent.click(screen.getByText('Click'));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
```

### 后端 API 测试示例

```python
# tests/test_api.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_gallery_returns_json(client):
    """图库 API 应返回 JSON 列表"""
    response = client.get('/api/gallery')
    assert response.status_code == 200
    data = response.get_json()
    assert 'items' in data
```
