## Why / 为什么

Sharp GUI 已经迁移到 Spark 2.0.0，但当前查看器仍然主要暴露相机与模型变换控制，没有把 Spark 新增的内置 reveal effects 转化成用户可直接操作的预览体验。现在补上一个专用的效果切换入口，可以让项目真正吃到 Spark 2.0 升级红利，同时不需要把用户引导到设置面板或独立演示页。

## What Changes / 变更内容

- 在查看器右侧新增专用的 reveal effects 切换 rail，位置放在 Help 触发器与 Quick Controls 触发器之间，让三者保持同一条右侧垂直基线。
- 桌面端 rail 采用更克制的极简样式：静止状态仅保留线条、选中态与上下切换 affordance，不常驻效果名称；名称仅在 hover / focus 时通过提示气泡出现。
- 接入参考 Spark 官方 `splat-reveal-effects` 示例的精选效果集；在未配置本地偏好时，`Magic` 仍作为每次新查看器会话的默认效果。
- 提供查看器内的 replay 交互，让用户无需重新加载模型、无需离开预览界面即可重放当前效果。
- 新 rail 沿用项目现有的玻璃拟态语言，包括高斯模糊背景、轻边框、悬浮层阴影，以及与现有浮层一致的 hover / focus 状态。
- 对新标签、tooltip 与可访问性文案做中英文本地化，并保证在无模型、窄屏和 XR 场景下安全降级；其中 XR 下完全隐藏 rail。
- 移动端不保留桌面完整竖向 rail 常驻展示，而是收敛为与 Quick Controls 同尺寸的图标入口；点击后在入口上方锚点弹出一套复用桌面 rail 控件的轻量浮层，并在选择效果后自动收回。
- 在设置中新增“默认渲染特效”选项，支持 `无特效` 与精选效果，并将该偏好保存到当前设备浏览器本地，方便在低性能设备上关闭启动特效；初始默认值仍为 `Magic`。
- 范围限定在查看器预览侧行为，不扩展为通用效果编辑器、自定义 shader 编排 UI，也不改动后端或导出链路。

## Capabilities

### New Capabilities
- `viewer-reveal-effects-rail`：新增右侧 reveal effects 选择器，覆盖默认 effect 启动策略、效果重放、国际化文案，以及与 Help / Quick Controls 共存的浮层布局规则，并定义桌面端极简 rail 样式、移动端图标触发 + 锚点弹出 rail、设备级本地默认特效配置以及 XR 隐藏策略。

### Modified Capabilities
- 无。

## 影响范围

- 受影响前端模块：`frontend/src/hooks/useViewer.ts`、`frontend/src/store/useAppStore.ts`、`frontend/src/components/viewer/*`、`frontend/src/components/layout/Help/*`、`frontend/src/components/layout/Settings/*`。
- 受影响 UI 资源：`frontend/src/i18n/en.json`、`frontend/src/i18n/zh.json`，以及 `frontend/src/styles/variables.css` 中新增的共享浮层布局 / 毛玻璃 token。
- 依赖与运行时影响：继续基于 `@sparkjsdev/spark` 2.0.x 公共 API 完成 viewer-side effect / modifier 集成，不需要改动后端 API 或 `app.py`。
