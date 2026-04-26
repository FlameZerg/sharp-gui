# 工作流：创建新自定义 Hook

## 前置条件

- 确定 Hook 的职责（UI 状态管理 / 3D 操作 / 数据获取 / 浏览器 API 封装）
- 确定 Hook 名称：`useXxx`（camelCase，`use` 前缀）

---

## 步骤

### 1. 创建 Hook 文件

在 `frontend/src/hooks/` 下创建 `useXxx.ts`：

```typescript
// hooks/useMyFeature.ts
import { useEffect, useRef, useCallback, useState } from 'react';
import { useAppStore } from '@/store';

interface UseMyFeatureOptions {
  // Hook 参数（如有）
  enabled?: boolean;
}

interface UseMyFeatureReturn {
  // Hook 返回值
  isActive: boolean;
  toggle: () => void;
}

export const useMyFeature = (options: UseMyFeatureOptions = {}): UseMyFeatureReturn => {
  const { enabled = true } = options;
  const [isActive, setIsActive] = useState(false);

  const toggle = useCallback(() => {
    setIsActive(prev => !prev);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    // 初始化逻辑
    return () => {
      // 清理逻辑
    };
  }, [enabled]);

  return { isActive, toggle };
};
```

**关键要求**：
- 使用 `export const useXxx = (...) => { ... }` 箭头函数导出
- 定义参数和返回值的类型（`interface` 或内联）
- 清理副作用（`useEffect` return cleanup）

### 2. 3D Viewer 相关 Hook 模式

如果 Hook 需要操作 3D Viewer：

```typescript
import { useEffect, useRef } from 'react';

export const useMyViewerFeature = (viewerRef: React.RefObject<any>) => {
  const animationFrameRef = useRef<number>();

  useEffect(() => {
    if (!viewerRef.current) return;

    const animate = () => {
      // 操作 viewerRef.current
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [viewerRef]);

  return { /* 返回值 */ };
};
```

**特殊规则**：
- 接收 `viewerRef` 参数（`React.RefObject<any>`）
- 使用 `useRef` 管理动画帧 ID、不触发重渲染的状态
- 使用 `requestAnimationFrame` 循环驱动动画
- cleanup 中取消动画帧

### 3. 在组件中使用

```typescript
import { useMyFeature } from '@/hooks/useMyFeature';

export function MyComponent() {
  const { isActive, toggle } = useMyFeature({ enabled: true });
  // ...
}
```

---

## 现有 Hooks 参考

| Hook | 职责 | 接收参数 |
|------|------|----------|
| `useViewer` | 核心：初始化 Spark Viewer、加载模型、相机控制、Reveal Effects | `containerRef` |
| `useKeyboard` | WASD+QE 键盘移动，Shift/Alt 变速 | `viewerRef` |
| `useGyroscope` | 设备陀螺仪控制相机 | `{ viewerRef }` |
| `useJoystick` | 虚拟摇杆触控移动 | `{ viewerRef }` |
| `useXR` | WebXR VR / AR 会话管理 | `{ viewerRef }` |
| `useGalleryVirtualizer` | 图库虚拟滚动与稳定高度计算 | 参数对象 |
| `useGalleryThumbnail` | 缩略图加载状态管理 | `src`, `enabled` |
| `useTaskQueue` | 轮询任务状态，完成时刷新画廊 | 无 |

---

## 组合模式

`useViewer` 是主 Hook，内部组合调用子 Hooks：

```typescript
export const useViewer = (containerRef) => {
  const { speedMode } = useKeyboard(viewerRef);
  const gyroscope = useGyroscope({ viewerRef });
  const joystick = useJoystick({ viewerRef });
  const xr = useXR({ viewerRef });

  return { ...gyroscope, ...joystick, ...xr, speedMode };
};
```

新增 Viewer 相关功能时，优先在子 Hook 中实现，然后在 `useViewer` 中组合。

---

## 检查清单

- [ ] 文件位于 `frontend/src/hooks/` 目录
- [ ] 文件名 `useXxx.ts`（camelCase）
- [ ] 使用 `export const useXxx = () => { ... }` 导出
- [ ] 定义了参数和返回值类型
- [ ] `useEffect` 有 cleanup 函数（如有副作用）
- [ ] 导入使用 `@/` 路径别名
- [ ] 纯类型导入使用 `import type`
