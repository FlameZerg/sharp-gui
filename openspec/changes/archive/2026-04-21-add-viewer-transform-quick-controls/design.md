## Context

当前预览体验由 `ViewerCanvas + ControlsBar + Help + useViewer + useAppStore` 组成：

- `ViewerCanvas` 负责渲染主场景与叠加控制组件。
- `ControlsBar` 提供底部主要操作（视角、重置、全屏、XR、分享）。
- `Help` 提供右下角帮助按钮与说明面板。
- `useViewer` 持有 Spark/Three 运行时对象，当前已具备模型加载、重置相机、LoD 应用、XR 模式切换等能力。
- `useAppStore` 已持有 LoD、XR、质量模式等状态，并负责跨组件状态同步。

现状问题：

- 缺少针对“模型朝向/位置/缩放”的直接 UI，用户只能手动拖动相机补偿，不能真正修正模型姿态。
- 缺少“交互方向反转”快捷入口，用户在不同触控习惯下学习成本较高。
- 缺少可复用的“每模型局部参数”机制，模型切换后无法恢复个性化校正。

约束与输入：

- 必须遵循现有 CSS Modules + CSS Variables 玻璃态视觉语言。
- 新增用户可见文案必须维护中英文 i18n。
- Spark 2.0 已支持 `SplatMesh` 的 `position/rotation/quaternion/scale`（其中 scale 为统一缩放语义）以及渲染侧 LoD/foveation 参数。
- 现有项目已有 Help 右下角按钮与底部 ControlsBar，新增入口需避免遮挡与层级冲突。

## Goals / Non-Goals

**Goals:**

- 提供一个右下角可展开的快捷控制入口，符合现有玻璃态设计语言。
- 支持高频且稳定的模型展示参数控制：位置、旋转、统一缩放、常见朝向预设、反向交互。
- 支持每模型本地化记忆与一键重置，降低重复校正成本。
- 保证移动端与桌面端可达性（触控、键盘、focus-visible、ARIA）。

**Non-Goals:**

- 不新增后端 API、数据库或服务端配置项。
- 不引入新状态管理框架或替换现有 `useViewer` 架构。
- 不暴露 Spark 全量调试参数（例如 editor 中全部 debug 字段）。
- 不在第一阶段实现多模型批量编辑、时间轴动画编辑、导出变换写回原文件。

## Decisions

### 1) 入口与布局层决策

**Decision:** 新增 `QuickControls` 组件并挂载在 `ViewerCanvas` 的 overlay 层，与 `Help` 同级，固定在右下角区域。

**Rationale:**

- `ViewerCanvas` 是所有 viewer 叠层控件（Help、Gyro、Joystick、SpeedTooltip、ControlsBar）的统一容器，放在这里可以统一 z-index 与 pointer 行为。
- 与 `Help` 同级便于形成“帮助 + 快捷调参”双按钮分区，避免入侵底部主控制条信息密度。

**Alternatives considered:**

- 放入 `ControlsBar`：会导致底部条过长，移动端拥挤，且与“右下角浮动按钮”目标不一致。
- 放入 `Settings`：入口路径太深，不符合“高频校正”场景。

### 2) 状态建模与持久化策略

**Decision:** 在 `useAppStore` 新增扁平状态字段与 action，并增加“按模型 ID 存储覆盖值”的本地持久化结构。

建议结构（逻辑层面）：

- 当前编辑态：`viewerTransformDraft`（position/rotation/scale、reverse flags、quality quick fields）
- 当前模型已应用态：`viewerTransformApplied`
- 本地覆盖集合：`modelViewerOverrides[modelId]`

**Rationale:**

- 符合项目“单一扁平 store”约束。
- 可在模型切换时恢复每模型参数，减少重复操作。
- 通过 localStorage 仅保存前端体验偏好，不影响服务端。

**Alternatives considered:**

- 仅 useState 局部组件态：切模型会丢失，且无法被 `useViewer`/`ControlsBar` 共享。
- 服务端持久化：需要新增 API，不符合当前范围。

### 3) 运行时应用路径

**Decision:** 由 `useViewer` 在 active `SplatMesh` 生命周期内统一应用变换与渲染参数，UI 只改 store，不直接碰 Three 对象。

**Rationale:**

- `useViewer` 已掌握 `viewerRef`、`sparkRenderer`、`splatMesh`，是最稳定的运行时入口。
- 避免多个组件直接操作 Three 对象造成竞态。

**Alternatives considered:**

- QuickControls 直接调用 mesh 引用：耦合高，难测试，易与加载/卸载时机冲突。

### 4) 参数范围与预设策略

**Decision:** 仅暴露“安全范围”参数，并用预设映射到 Spark 参数。

- 模型姿态：
  - Position X/Y/Z（有限区间）
  - Rotation X/Y/Z（`[-pi, pi]`）
  - Uniform Scale（正数区间，内部 `setScalar`）
  - Orientation Presets（Default/OpenGL/Z-up/Rotate Z 180）
- 交互反向：
  - reverseRotate / reverseScroll
  - reverseSlide / reverseSwipe

补充说明：

- Default 对应当前预览基线（OpenCV 语义），因此不再单独暴露 OpenCV 预设按钮，避免“点击后参数无变化”的误解。
- “上下翻转 180°”按当前实现映射为绕 Z 轴旋转 180°，与用户手动调节 Rot Z 语义一致。

**Rationale:**

- 参考 Spark docs 与 editor 示例的有效参数集合，同时避免把 debug-only 项暴露给普通用户。
- 保持“常用有效”而不是“全量复杂”。

### 5) 交互与视觉规范

**Decision:** 采用“浮动圆形入口 + 玻璃态展开面板 + 分组折叠”的轻量交互模型。

- 默认收起，仅显示图标按钮（右下角）。
- 打开后面板展示两组：姿态校正 / 交互方向。
- 触发按钮锚定在底部 ControlsBar 上边界以上，面板向上展开，关闭时不占据文档流布局。
- 触发按钮尺寸与 Help 按钮保持一致。
- 移动端使用更大点击面积与简化布局；触控设备不依赖 hover。

**Rationale:**

- 与项目现有 Help/ControlsBar 的玻璃态视觉一致。
- 控件密度与学习成本可控。

### 6) 可访问性与 i18n 决策

**Decision:** 所有用户可见文本走 i18n；交互控件提供 `aria-label`、`role`、`focus-visible`，支持键盘关闭和重置。

**Rationale:**

- 满足项目强制 i18n 规范与可访问性最低标准。

## Risks / Trade-offs

- [Risk] 叠层按钮与现有 Help、ControlsBar 发生遮挡或抢占点击
  → Mitigation: 统一 z-index 分层（右下工具层固定区间），并在小屏模式下调整按钮堆叠顺序与间距。

- [Risk] 参数实时滑动触发频繁更新导致帧率波动
  → Mitigation: 对高频输入使用轻量节流；只在值变更时标记 `sparkRenderer.setDirty()`。

- [Risk] 模型切换时覆盖值与默认值混淆
  → Mitigation: UI 明确显示“当前模型覆盖/默认值”状态，并提供“一键恢复默认”。

- [Risk] 坐标系预设命名造成认知混乱
  → Mitigation: 预设命名结合简短说明（如 OpenGL: Y-up, OpenCV: camera-forward），并保留预览前后可回退。

- [Trade-off] 快捷面板不再承载质量参数，牺牲“一处集中调参”的完整性
  → Mitigation: 第一阶段优先稳定性，后续可在高级模式中按需扩展。

## Migration Plan

1. 新增前端组件与样式，不改后端接口。
2. 在 store 增加状态与持久化读写逻辑，保持向后兼容（无旧数据时使用默认值）。
3. 在 `useViewer` 中注入参数应用与模型切换恢复逻辑。
4. 灰度验证：
   - 桌面端与触控端交互可达
   - 常见模型（正向/倒置）可一键校正
   - 切模型后覆盖值恢复符合预期
5. 回滚策略：保留开关位（或保留组件挂载条件），可快速禁用快捷面板，不影响基础预览流程。

## Open Questions

- 每模型覆盖值是否需要“导入/导出”到分享页（当前设计先不做）？
- 快捷面板是否在 XR 会话中显示（建议 XR 中默认隐藏，仅保留退出操作）？
- 未来是否提供“高级模式”重新暴露质量参数（默认保持隐藏）？