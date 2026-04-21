## Why

当前预览界面已有基础控制条与操作指南，但缺少“模型展示参数”的高频快速调节入口。实际使用中，不同来源模型的朝向和坐标系并不一致，用户经常遇到模型上下颠倒、方向错误、初始位置偏移等问题，只能通过手动拖拽反复修正，成本高且不可复现。

Spark 2.0 官方文档与 editor 示例已经验证了交互方向、姿态与位置参数控制模式的可行性。引入与现有玻璃态风格一致的右下角快捷控制面板，可以显著降低模型校正成本，并提升预览的一致性与可解释性。

## What Changes

- 新增右下角“快捷控制按钮”，按钮尺寸与 Help 保持一致；按钮锚定在底部 ControlsBar 上边界之上，点击后面板向上展开。
- 新增“模型姿态校正”控制组：
  - 统一缩放（uniform scale）
  - 位置偏移（X/Y/Z）
  - 旋转（X/Y/Z）
  - 一键翻转/纠正预设（默认、绕 Z 轴旋转 180°、OpenGL、Z-Up）
- 新增“视角与交互方向”控制组：
  - 指针旋转方向反转（reverse pointer direction）
  - 指针平移/滑动方向反转（reverse pointer slide）
  - 重置当前姿态与交互参数
- 取消“显示质量快捷项”分组：
  - 质量相关设置继续使用原有设置面板入口，避免与 LoD 设置重复和语义混淆
- 新增参数持久化策略：
  - 支持当前模型会话记忆
  - 可选保存为该模型的本地覆盖（不影响全局默认）
- 完整补齐 i18n 文案（zh/en）与键盘/触控可访问交互（focus-visible、ARIA、触屏可达）。

## Capabilities

### New Capabilities
- `viewer-transform-quick-controls`: 在预览界面提供右下角展开式快捷控制面板，支持模型姿态校正、交互方向反转，并保持参数可重置与可持久化。

### Modified Capabilities
- (none)

## Impact

- Affected frontend areas:
  - viewer 渲染层与控制层（ViewerCanvas / useViewer / ControlsBar / Help）
  - 全局状态（useAppStore）与参数持久化键
  - i18n 资源（en.json / zh.json）
  - 局部样式（CSS Modules）与必要的全局层级协调
- No backend API changes required in first phase.
- 与 Spark 2.0 已有能力保持一致：基于 SplatMesh 的 position/rotation/scale 与控制方向参数映射，不引入额外渲染依赖。