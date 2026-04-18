# 前端开发规范

## 组件规范

### 三件套结构

每个新组件 **必须** 遵循以下文件结构：

```
ComponentName/
├── ComponentName.tsx        # 组件实现
├── ComponentName.module.css # 样式（CSS Modules）
└── index.ts                 # 桶导出
```

`index.ts` 内容：
```typescript
export { ComponentName } from './ComponentName';
```

### 组件声明模式

**新代码统一使用命名导出的函数声明**（不使用 `React.FC`、不使用 `export default`）：

```typescript
// ✅ 正确 — 新组件必须使用此模式
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import styles from './MyButton.module.css';

interface MyButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  icon?: ReactNode;
}

export function MyButton({ variant = 'primary', icon, children, ...props }: MyButtonProps) {
  return (
    <button className={styles[variant]} {...props}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {children}
    </button>
  );
}
```

```typescript
// ❌ 错误 — 新代码不要使用
export default function MyButton() { ... }     // 禁止 default export
export const MyButton: React.FC = () => { ... } // 新代码不用 React.FC
```

> **⚠️ 历史遗留**：`ViewerCanvas`、`Settings`、`ControlsBar`、`ParticleBackground`、`TaskQueue` 等组件使用了 `React.FC`；`ControlsBar/`、`Help/`、`ViewerCanvas/` 缺少 `index.ts`。`useVR.ts` 已重构为 `useXR.ts`（统一 VR + AR）。现有代码不强制修改。

### Props 定义

- 使用 `interface XxxProps` 定义 Props
- 尽可能 `extends` 原生 HTML attributes（如 `ButtonHTMLAttributes<HTMLButtonElement>`）
- 使用解构赋值接收 Props，支持 `...rest` 透传

### CSS class 组合模式

使用数组 + `filter(Boolean).join(' ')` 模式：

```typescript
const classes = [
  styles.button,
  styles[variant],
  disabled && styles.disabled,
  className,
].filter(Boolean).join(' ');
```

### 组件分类

| 目录 | 用途 | 示例 |
|------|------|------|
| `components/common/` | 通用 UI 组件，不含业务逻辑 | Button, Modal, Loading, Icons |
| `components/gallery/` | 图库相关组件 | GalleryItem, GalleryList |
| `components/layout/` | 页面布局与导航组件 | Sidebar, ControlsBar, Settings, Help |
| `components/viewer/` | 3D 查看器相关组件 | ViewerCanvas, GyroIndicator, VirtualJoystick |

---

## 状态管理

### Zustand Store

项目使用 **单一扁平 Store**（`frontend/src/store/useAppStore.ts`）：

```typescript
import { create } from 'zustand';

interface AppState {
  // 状态字段
  isLoading: boolean;
  galleryItems: GalleryItem[];
  // ... 其他状态

  // Actions
  setLoading: (loading: boolean, text?: string) => void;
  setGalleryItems: (items: GalleryItem[]) => void;
  // ... 其他 actions
}

export const useAppStore = create<AppState>((set) => ({
  isLoading: false,
  galleryItems: [],

  setLoading: (loading, text) => set({ isLoading: loading, loadingText: text }),
  setGalleryItems: (items) => set({ galleryItems: items }),
}));
```

### Store 规则

- **单一 Store**：所有全局状态放在 `useAppStore` 中，不创建多个 Store
- **无中间件**：不使用 `persist` / `devtools` / `immer`
- **扁平结构**：状态字段直接放在顶层，不嵌套
- **Action 是箭头函数**：在 `create` 内部用 `set()` 修改状态
- **桶导出**：通过 `store/index.ts` re-export

### 使用方式

```typescript
// 组件中使用
const { isLoading, setLoading, galleryItems } = useAppStore();

// 或选择性订阅（性能优化）
const isLoading = useAppStore(state => state.isLoading);
```

---

## API 层

### 架构

```
api/
├── client.ts    # 底层 fetch 封装（apiGet, apiPost, apiPostFormData, apiDelete）
├── gallery.ts   # 图库相关 API
├── tasks.ts     # 任务相关 API
├── settings.ts  # 设置相关 API
└── index.ts     # 桶导出（export * from 各模块）
```

### 底层客户端

`client.ts` 提供四个泛型函数：

```typescript
export async function apiGet<T>(url: string): Promise<T>;
export async function apiPost<T>(url: string, data?: unknown, options?: FetchOptions): Promise<T>;
export async function apiPostFormData<T>(url: string, formData: FormData): Promise<T>;
export async function apiDelete<T>(url: string): Promise<T>;
```

特性：
- **原生 fetch**，不使用 axios
- **30 秒超时**（AbortController）
- **自定义错误类** `ApiError`（携带 `status` 和 `data`）
- **泛型返回值** `Promise<T>`

### 新增 API 规则

1. 在对应的功能模块文件中添加函数（或创建新模块文件）
2. 使用泛型指定返回类型：`apiGet<MyResponse>('/api/my-endpoint')`
3. 在 `api/index.ts` 中确保 `export *` 导出
4. 对应的类型定义放在 `types/` 目录

---

## 自定义 Hooks

### 命名与导出

```typescript
// ✅ 标准模式
export const useMyHook = (param: ParamType) => {
  // hook 实现
  return { value, action };
};
```

### 常见模式

| 模式 | 说明 | 示例 |
|------|------|------|
| Viewer 操作 | 接收 `viewerRef` 参数操作 3D viewer | `useKeyboard(viewerRef)` |
| 动画循环 | 使用 `requestAnimationFrame` + `useRef` | `useGyroscope`, `useJoystick` |
| 状态引用 | 使用 `useRef` 管理不触发重渲染的状态 | 各 3D 相关 hook |
| 组合模式 | 主 hook 内部调用子 hook | `useViewer` 组合 `useKeyboard` + `useGyroscope` + `useJoystick` + `useXR` |

### 位置

所有自定义 Hooks 放在 `frontend/src/hooks/` 目录，一个文件一个 Hook。

---

## TypeScript 类型系统

### interface vs type

| 场景 | 用哪个 | 示例 |
|------|--------|------|
| 对象结构、API 响应、组件 Props、Store 状态 | `interface` | `interface GalleryItem { ... }` |
| 联合类型、字面量类型 | `type` | `type TaskStatus = 'pending' \| 'running'` |
| 类型别名 | `type` | `type IconProps = SVGProps<SVGSVGElement>` |

### 类型位置

| 类型 | 位置 |
|------|------|
| API 响应 / 业务实体 | `types/` 目录下对应文件 |
| 组件 Props | 组件文件内（与组件同文件） |
| Store 状态 | `store/useAppStore.ts` 内 |
| 工具函数参数/返回值 | 工具函数文件内 |

### 类型导出

```typescript
// types/index.ts — 桶导出
export type { GalleryItem, GalleryListResponse } from './gallery';
export type { Task, TaskStatus, TasksResponse } from './task';
export type { CameraConfig } from './viewer';
```

### TypeScript 配置要点

- `strict: true` — 严格模式
- `verbatimModuleSyntax: true` — 必须使用 `import type` 导入纯类型
- `noUnusedLocals: true` — 不允许未使用的局部变量
- `noUnusedParameters: true` — 不允许未使用的参数
- 路径别名：`@/*` → `src/*`

---

## 性能优化

> 不要过度优化，以下是需要关注的场景：

### 何时使用 `React.memo`

- 组件接收 **大列表中的单项** 数据（如 `GalleryItem`）
- 父组件频繁重渲染但当前组件 props 不变
- **不要**默认给所有组件加 `memo`，先用 React DevTools 确认存在性能问题

### 何时使用 `useMemo` / `useCallback`

- 传递回调给 `memo` 化的子组件时
- 计算开销大的派生数据（如过滤/排序长列表）
- **不要**对简单计算使用 `useMemo`（anti-pattern）

### 3D 渲染注意事项

- 动画循环已在 `useViewer` 中通过 `requestAnimationFrame` 管理，不要创建额外的渲染循环
- Three.js 对象（Geometry、Material、Texture）手动创建时需在 cleanup 中 `.dispose()`
- 避免在 React render 中创建 Three.js 对象（应该在 `useEffect` 或 `useRef` 中）

### 懒加载

对大型页面级组件可使用 `React.lazy` + `Suspense`（当前项目为单页应用，暂无需要）。

---

## 错误处理

### API 调用

所有 API 调用必须在组件/Hook 中 try-catch：

```typescript
import { useAppStore } from '@/store';

const handleAction = async () => {
  try {
    const result = await someApiCall();
    // 处理成功
  } catch (error) {
    // 使用 store 中的通知/loading 机制反馈给用户
    console.error('操作失败:', error);
  }
};
```

### 错误边界（Error Boundary）

如果未来需要添加，推荐在 3D Viewer 区域包裹错误边界，防止渲染崩溃导致整个页面白屏。当前项目未添加，作为改进方向记录。

---

## 构建与分包

Vite 配置了 `manualChunks` 代码分割：

| Chunk | 包含 | 大小参考 |
|-------|------|----------|
| `three` | three.js 核心 | ~493KB |
| `spark` | @sparkjsdev/spark | ~487KB |
| `react-vendor` | react, react-dom | ~4KB |
| `utils` | i18next, zustand | ~20KB |

新增大型三方依赖时，应在 `vite.config.ts` 的 `manualChunks` 中配置独立 chunk。

---

## 3D 渲染引擎

### Spark（替代 Gaussian Splats 3D）

项目已从 `@mkkellogg/gaussian-splats-3d`（已停止维护）迁移至 `@sparkjsdev/spark` 2.0 稳定版：

| 特性 | 说明 |
|------|------|
| **SplatMesh** | 继承 `THREE.Object3D`，可直接 `scene.add(splatMesh)` |
| **SparkRenderer** | 继承 `THREE.Mesh`，作为渲染管线的一部分加入场景 |
| **RAD + paged** | 支持 `.rad` 头文件 + `.radc` 分块流式加载 |
| **WASM Raycaster** | 内置 WASM 加速射线检测，用于点击聚焦（`splatMesh.raycast()`） |

### 关键代码模式

```typescript
// 初始化 Spark 渲染器
const sparkRenderer = new SparkRenderer({ renderer });
scene.add(sparkRenderer); // 必须加入场景

// 加载模型（LoD + nonLoD 对比能力）
const splatMesh = new SplatMesh({
  url,
  fileType: SplatFileType.SPZ,
  lod: true,
  nonLod: true,
});
await splatMesh.initialized;
scene.add(splatMesh);

// 即时切换 LoD 对比源
splatMesh.enableLod = true;
splatMesh.lodScale = 1.0;

// 点击聚焦（WASM Raycaster）
const raycaster = new THREE.Raycaster();
const intersects = raycaster.intersectObject(splatMesh);
```

### 注意事项

- **模型朝向**：加载后需设置 `splatMesh.rotation.x = Math.PI` 纠正模型上下颠倒
- **缩放**：通过 `splatMesh.scale.setScalar(modelScale)` 控制（默认 2.0）
- **清理**：切换模型或组件销毁时调用 `splatMesh.dispose()`，并销毁 `sparkRenderer`
- **listenToKeyEvents**：不可调用 `OrbitControls.listenToKeyEvents()`（Spark 注册的全局 listener 与之冲突）

---

## WebXR（VR / AR）

### 架构

XR 功能由 `useXR` hook 统一管理（替代了原来的 `useVR`），支持双模式：

| 模式 | WebXR Session | 特性 |
|------|--------------|------|
| **VR** | `immersive-vr` | Camera Rig 漫游、手柄摇杆控制、A/X 键重置 |
| **AR** | `immersive-ar` | 透明背景 Passthrough、触摸旋转/升降、双指缩放 |

### Camera Rig 模式

使用 `THREE.Group` 作为相机父级（Camera Rig），移动 rig 而非直接操作相机：

```typescript
const rig = new THREE.Group();
rig.add(camera);
scene.add(rig);

// 移动：修改 rig.position
// 转向：修改 rig.rotation.y
```

### 关键实现细节

- **高度校准**：`local-floor` 参考空间将头部置于 ~1.6m，需 `rig.position.y = -xrCam.position.y` 使模型在眼前
- **Home 位置**：`rigHomeRef` 保存校准后的位置，A/X 重置时恢复到校准位置而非 (0,0,0)
- **Session 结束恢复**：需完整恢复 camera (position, up, rotation, fov, near, far)、renderer (viewport, pixelRatio)、controls (target, update)
- **AR 透明背景**：进入 AR 时 `scene.background = null` + `renderer.setClearColor(0,0,0,0)`
- **AR 缩放恢复**：退出 AR 时需恢复 `splatMesh.scale` 到原始值
