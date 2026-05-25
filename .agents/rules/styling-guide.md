# 样式规范（2026-04 现状校准版）

## 样式方案概述

项目采用 **CSS Modules + CSS Variables 设计系统**，当前前端视觉语言为：

- Apple 风格玻璃态（Glassmorphism）
- 渐变/径向背景氛围（主场景层）
- 轻量过渡与微动效（0.15s~0.4s）
- Light-first + Dark override（`prefers-color-scheme`）
- 桌面与触控差异化交互（`pointer: coarse`）
- 本地照片图库采用克制的沉浸式瀑布流：照片是视觉主角，控件保持玻璃态、轻量、可扫描

**不使用**：CSS-in-JS、Tailwind、Sass/Less。

> 🎨 进行 UI 设计或界面改进时，可调用 Skill：[.agents/skills/ui-ux-pro-max/SKILL.md](../skills/ui-ux-pro-max/SKILL.md) 获取设计系统推荐（配色、字体、布局模式等）。

---

## 样式架构与文件职责

当前样式入口链路：

1. `main.tsx` 引入 `styles/global.css`
2. `global.css` 再 `@import` `variables.css` + `animations.css`
3. `App.css` 负责页面级布局（主容器、启动屏、空态、全局遮罩）
4. 各组件使用 `*.module.css` 维护局部样式

| 文件 | 职责 | 规则 |
|------|------|------|
| `frontend/src/styles/variables.css` | 全局设计 Token（颜色、间距、圆角、过渡、玻璃、布局） | 新变量必须加在这里 |
| `frontend/src/styles/animations.css` | 可复用全局关键帧 | 跨组件复用动画优先放这里 |
| `frontend/src/styles/global.css` | Reset、基础标签样式、全局辅助类 | 保持轻量，避免业务样式堆积 |
| `frontend/src/App.css` | 页面级布局与场景样式 | 仅放全局页面结构与状态样式 |
| `frontend/src/components/**/**.module.css` | 组件局部样式 | 不污染全局命名空间 |

照片图库和局域网门禁相关控件应优先复用 `components/common/SelectMenu`、`ConfirmDialog`、`TextInputDialog` 等通用玻璃态组件，避免浏览器原生 `select` / `prompt` / `confirm` / `alert` 造成视觉割裂。

> `frontend/src/index.css` 中仍有历史遗留变量定义；新增变量不要放在 `index.css`。

---

## CSS Modules 与命名约定

每个组件样式文件使用 `.module.css`。

| 范围 | 命名规范 | 示例 |
|------|----------|------|
| CSS Modules class | camelCase | `.actionBtn`, `.sectionTitle`, `.statusIcon` |
| 全局 class（`App.css` / `global.css`） | kebab-case | `.boot-screen`, `.empty-state` |
| CSS 变量 | kebab-case + `--` 前缀 | `--accent-blue`, `--glass-bg` |

推荐 className 组合模式：

```typescript
const classes = [
  styles.button,
  styles[variant],
  disabled && styles.disabled,
  className,
].filter(Boolean).join(' ');
```

---

## 设计 Token 规范

### 必须 Token 化的维度

- 间距：使用 `--space-*`
- 圆角：使用 `--radius-*`
- 过渡：使用 `--transition-*`
- 常用文本与语义色：使用 `--text-*`、`--accent-*`、`--success|warning|danger|error`
- 布局关键尺寸：使用 `--sidebar-width`、`--controls-height`

### 可以局部硬编码的维度

以下值允许在组件中按视觉需要局部硬编码（常见于玻璃态层）：

- 半透明层 `rgba(...)`
- 特定阴影 `box-shadow`
- 局部渐变背景

但同一数值在 3 处以上重复时，应提炼为变量并迁移到 `variables.css`。

### 玻璃态标准写法

```css
.panel {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
}
```

---

## 字体与排版

当前项目使用 Apple 系统字体栈：

```css
font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
             "Helvetica Neue", Arial, sans-serif;
```

规范建议：

- 页面级字号优先 12/13/14/16/18 的层级节奏
- 文本颜色优先使用 `--text-primary` / `--text-secondary` / `--text-muted`
- 保证正文与背景对比度至少 4.5:1

---

## 动画与过渡

### 时长与缓动

- 交互反馈：0.15s~0.3s
- 面板/遮罩进出场：0.25s~0.4s
- 优先使用 `cubic-bezier(0.16, 1, 0.3, 1)` 或 Token 中既有过渡

### 动画放置规则

- 跨组件通用动画：放 `styles/animations.css`
- 强业务耦合动画：可放组件 `.module.css`
- 避免在多个组件重复声明同名 `@keyframes`（当前存在历史重复，后续逐步收敛）

### 可访问性

- 新增较明显动画时，需支持 `prefers-reduced-motion`
- 不要使用高频闪烁或大幅位移动画

---

## 响应式与输入设备策略

### 断点（按当前实现）

| 区间 | 规则 |
|------|------|
| `<= 768px` | 移动端：侧栏抽屉化、按钮与面板尺寸收紧 |
| `>= 769px` | 桌面端：侧栏浮动布局、主视图偏移补偿 |

### 输入方式适配

- 触控设备使用 `@media (pointer: coarse)` 做交互特化
- 仅 hover 可见的操作按钮在触控设备上应改为常驻或可达
- 全屏/主容器优先使用 `100dvh`，并保留 `100vh` fallback
- 照片图库移动端默认不应只有单列；展示密度需要可调，且可保留双指捏合调整列数。
- 图库列数/密度浮层应以触发按钮为中心定位，并在窄屏下限制最大宽度，避免贴边或遮挡关键内容。

### 照片图库视觉细节

- 瀑布流卡片标题默认使用白色文字 + 阴影，hover/focus 时再出现半透明背景，不要让标题条常驻占据小缩略图的大面积空间。
- 排序标签需要同时保留字段名和方向提示，例如 `修改时间↓`、`名称 A-Z`；不要为了极简牺牲可读性。
- 图库密度控制使用图标触发、滑块调节和当前档位提示；避免多个 `+` / `-` 文本按钮堆在工具栏里。
- 主要动作如 `转换为 3D` 保持项目蓝色强调；次级图标使用当前文本色，不单独引入割裂的高饱和色。

### 局域网门禁视觉细节

- 门禁页、启动提醒和设置页门禁区域必须延续现有 Apple 玻璃态：柔和半透明背景、清晰层级、克制边框和足够圆角；不要使用浏览器原生弹窗或临时拼装的提示块。
- 启动提醒应是轻量 modal：标题、风险说明、2-3 个主要动作即可，按钮间距和卡片内边距要匹配现有 Settings / Modal 视觉密度。
- 设置页门禁关闭时只显示总开关、风险提示和保存动作；开启后再展开访问码、会话天数、远程生成和撤销会话，并用明显留白分隔开关卡片与详细表单。
- 安全警告可以使用暖色强调，但面积要克制；不要让警告色压过主操作，也不要用大块高饱和纯色破坏整体质感。

---

## 深色模式策略

统一使用 `@media (prefers-color-scheme: dark)` 覆盖：

- 背景透明度与边框强度
- 阴影强度
- 文本可读性

建议采用“最小覆盖原则”：只覆盖在深色下确实需要变化的属性，避免整段样式重复。

---

## 层级（z-index）约定

当前项目存在多层浮层叠加，建议遵循以下区间：

- 0~10：背景与主内容层
- 15~35：侧栏、帮助面板、查看器特效轨道、导航辅助层
- 50~100：加载遮罩、控制面板、快捷控制、设置弹窗
- 1000：全局最高优先级查看器（如图片灯箱）

新增浮层前先确认是否会与现有 `Help`、`Settings`、`ImageViewer` 发生遮挡冲突。

---

## 反模式（新增代码禁止）

- 用 emoji 充当功能图标（应使用 SVG 图标组件）
- 用内联样式承载长期视觉规则（动态计算样式除外）
- 在组件中新增全局选择器污染（除 `:global(...)` 明确必要场景）
- 新增硬编码魔法值且无注释/无 token 归属
- 新增 Tailwind、Sass、CSS-in-JS

---

## 交付前检查清单

- [ ] 组件样式是否全部使用 CSS Modules
- [ ] 新 token 是否仅添加在 `variables.css`
- [ ] 深色模式下文本与边框可读性是否达标
- [ ] 关键交互是否有 hover + focus-visible 状态
- [ ] 触控设备下可操作元素是否可达
- [ ] 是否避免了 emoji 图标与重复关键帧
- [ ] 375 / 768 / 1024 / 1440 宽度下无布局溢出
