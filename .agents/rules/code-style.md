# 代码风格规范

> 本规范仅约束新代码。现有代码中的不一致为历史遗留，不要求修改，但鼓励在修改相关文件时顺带统一。

---

## 文件与目录命名

| 类别 | 命名规范 | 示例 |
|------|----------|------|
| React 组件目录 | PascalCase | `Button/`, `GalleryItem/`, `ViewerCanvas/` |
| React 组件文件 | PascalCase | `Button.tsx`, `GalleryItem.tsx` |
| CSS Modules 文件 | PascalCase.module.css | `Button.module.css` |
| 自定义 Hooks | camelCase, `use` 前缀 | `useViewer.ts`, `useGyroscope.ts` |
| API 模块 | camelCase | `client.ts`, `gallery.ts`, `tasks.ts` |
| 工具函数 | camelCase | `camera.ts`, `format.ts` |
| 类型定义 | camelCase | `gallery.ts`, `task.ts`, `viewer.ts` |
| 桶导出 | `index.ts` | 各目录下 |
| i18n 语言文件 | 语言代码 | `en.json`, `zh.json` |
| 全局样式 | camelCase | `variables.css`, `animations.css` |
| Python 文件 | snake_case | `app.py`, `detect_cuda.py` |
| Shell 脚本 | kebab/snake_case | `install.sh`, `run.bat` |

## TypeScript 命名约定

| 元素 | 命名规范 | 示例 |
|------|----------|------|
| 变量 | camelCase | `currentModelUrl`, `isLoading` |
| 函数 | camelCase | `fetchGallery`, `handleUpload` |
| React 组件 | PascalCase（函数名） | `function GalleryItem()` |
| 接口 (interface) | PascalCase | `GalleryItem`, `TasksResponse` |
| 类型别名 (type) | PascalCase | `TaskStatus`, `SpeedMode` |
| Props 接口 | PascalCase + `Props` 后缀 | `ButtonProps`, `SidebarProps` |
| 常量 | camelCase 或 UPPER_CASE | `DEFAULT_CAMERA_CONFIG` |
| CSS Modules class | camelCase | `.actionBtn`, `.sectionTitle` |
| 全局 CSS class | kebab-case | `.boot-screen`, `.empty-state` |
| CSS 变量 | kebab-case, `--` 前缀 | `--accent-blue`, `--glass-bg` |
| i18n key | camelCase | `appTitle`, `generateNew` |

> **⚠️ 历史遗留**：部分 i18n key 使用了 `snake_case`（如 `controls_view_front`），新 key 统一使用 `camelCase`。

## Python 命名约定

| 元素 | 命名规范 | 示例 |
|------|----------|------|
| 变量 | snake_case | `task_status`, `model_path` |
| 函数 | snake_case | `load_config`, `ply_to_splat` |
| 常量 | UPPER_CASE | `TASK_RETENTION_SECONDS`, `CLEANUP_INTERVAL` |
| 类 | PascalCase | `ApiError`（如有） |

## 导入排序（TypeScript）

严格按以下顺序组织导入，各组之间用空行分隔：

```typescript
// 1. React 核心
import { useEffect, useRef, useState } from 'react';

// 2. 三方库
import { useTranslation } from 'react-i18next';
import * as THREE from 'three';

// 3. 内部 Store
import { useAppStore } from '@/store';

// 4. 内部 API
import { fetchGallery, deleteGalleryItem } from '@/api';

// 5. 内部组件
import { Button } from '@/components/common';
import { GalleryItem } from '@/components/gallery';

// 6. 内部 Hooks
import { useViewer } from '@/hooks/useViewer';

// 7. 内部工具函数
import { formatFileSize, debounce } from '@/utils';

// 8. 类型导入（必须使用 import type）
import type { GalleryItem as GalleryItemType } from '@/types';

// 9. 样式（始终放最后）
import styles from './MyComponent.module.css';
```

### 关键规则

- **必须使用 `@/` 路径别名**（如 `@/store`、`@/api`），不允许 `../../../` 相对路径
- **纯类型导入必须使用 `import type`**（项目启用了 `verbatimModuleSyntax`）
- 同类导入可合并到一行（如 `import { fetchGallery, deleteGalleryItem } from '@/api'`）
- CSS Module 导入命名为 `styles`

## Python 导入排序

```python
# 1. 标准库
import os, sys, json, threading, queue, time

# 2. 三方库
import numpy as np
from flask import Flask, request, jsonify
from PIL import Image

# 3. 项目内部（如有）
from sharp.utils import ...
```

## 格式化工具

项目当前**无统一格式化工具**配置（无 Prettier / EditorConfig / Black / Ruff for GUI）。

- 前端代码检查：ESLint 9 flat config（`frontend/eslint.config.js`）
- TypeScript：strict mode + `noUnusedLocals` + `noUnusedParameters`
- ml-sharp 子项目（不可修改）：Ruff（行宽 100，Google docstring）

### 建议

- 缩进：2 空格（TypeScript/CSS/JSON）、4 空格（Python）
- 行宽：无硬性限制，建议 100~120 字符
- 引号：TypeScript 使用单引号 `'`，Python 使用单引号 `'`（字符串）
- 分号：TypeScript 文件末尾加分号
- 尾逗号：多行数组/对象使用尾逗号

## 注释语言

| 上下文 | 语言 |
|--------|------|
| Python docstring | 中文 |
| Python 行内注释 | 中文 |
| Python 日志消息 | 英文 + emoji（如 `🔄 Processing task`） |
| TypeScript 注释 | 中文或英文均可，保持与周围代码一致 |
| Commit message | 中文，遵循 Conventional Commits 规范 |

> 📝 **Commit Message 格式详细规范**请参考 Skill：[.agents/skills/commit-and-release/SKILL.md](../skills/commit-and-release/SKILL.md)
