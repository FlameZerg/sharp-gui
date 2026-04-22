## 1. 查看器浮层骨架

- [x] 1.1 创建独立的 `ViewerRevealEffectsRail` 组件模块，并在 `ViewerCanvas` 中挂载，完成本地 `Magic` 默认状态与 replay 操作联动。
- [x] 1.2 增加共享的查看器浮层对齐样式 / token，让 Help、reveal-effects rail 与 Quick Controls 保持同一条右侧垂直基线，并统一项目的毛玻璃背景风格。
- [x] 1.3 为 reveal-effects 标签、tooltip 与 replay 文案补齐 `frontend/src/i18n/en.json` 和 `frontend/src/i18n/zh.json` 国际化资源。
- [x] 1.4 为移动端实现与 Quick Controls 同尺寸的图标入口和锚点弹出 rail，复用桌面 rail 控件并避免遮挡主渲染画面。
- [x] 1.5 在设置面板中增加“默认渲染特效”选项，支持 `无特效` 与精选效果，并将偏好保存到当前设备浏览器本地。

## 2. Spark Reveal Effect 集成

- [x] 2.1 扩展 `useViewer` 以接收当前激活效果与 replay token，并将 Spark `dyno` / `objectModifier` 配置绑定到当前 `SplatMesh` 生命周期。
- [x] 2.2 实现精选效果集（`Magic`、`Spread`、`Unroll`、`Twister`、`Rain`），并基于当前 mesh 的 bounds 做模型空间归一化，而不是沿用示例资源的硬编码偏移。
- [x] 2.3 保证效果切换与 replay 只重启动画、不重新获取模型资源，同时保持 transform controls、camera reset 与 LoD 行为在 modifier 生效时仍然正常。
- [x] 2.4 为无模型、查看器重初始化、窄屏与 XR 状态增加可用性处理，其中 XR 下完全隐藏 rail，且不破坏现有 Help / Quick Controls 浮层行为。
- [x] 2.5 支持 `无特效` 默认值：在新会话中按设备级默认 effect 初始化，并在 `none` 状态下不为 mesh 挂载 reveal-effect modifier。

## 3. 回归与验证

- [ ] 3.1 验证键盘 / 焦点行为与响应式布局，确保 rail 或其移动端紧凑入口保持可访问，同时不遮挡 Help、reset、fullscreen、share 等关键操作。
- [x] 3.2 冒烟测试主查看器路径：新会话默认 `Magic`、切换效果可在原地生效、replay 可重启当前效果、Help / rail / Quick Controls 在桌面端保持对齐，且桌面静止态不常驻展示效果名称。
- [ ] 3.3 额外验证移动端与 XR 路径：移动端只显示图标入口、点击后弹出复用桌面 rail 的轻量浮层并在选择后安全收起，XR 下完全不显示 rail。
- [x] 3.4 运行项目前端校验命令，并记录构建、类型检查或 viewer 回归问题的后续修复项。
- [ ] 3.5 额外验证设备级默认 effect 偏好：确认 `无特效` / 各 reveal effect 在真实低性能设备上的流畅度与本地持久化行为符合预期。

## 验证备注

- 已用本地 HTTPS 环境 `https://127.0.0.1:5050` 对画廊模型 `1000151644` 做桌面端冒烟：模型加载完成后默认激活第一个 reveal effect（`Magic`），切换到第二个 effect 后状态正确更新，replay 触发路径可执行，且 Help / rail / Quick Controls 的右侧对齐基线一致；桌面 rail 静止态不常驻展示效果名称；Help 面板与 rail 重叠区域的顶层命中结果属于 Help 面板。
- 已对同一模型做移动端仿真冒烟：当前实现已从“文字按钮 + 独立大面板”收敛为“图标入口 + 锚点弹出复用桌面 rail”的方案，入口与 `QuickControls` 共用移动端底部偏移 token 并整体上移。真实设备上的最终视觉 QA 仍待继续完成。
- 已补充设置项“默认渲染特效”，当前实现将其保存在浏览器 `localStorage` 中，并在保存后同步影响当前 viewer 与后续新会话；`none` 会移除 mesh 上的 reveal-effect modifier。
- `npm run build` 通过。
- `npm run lint` 仍失败，但当前 reveal-effects 改动未新增 lint 问题；现存问题位于 `src/components/common/ImageViewer/ImageViewer.tsx`、`src/components/layout/ControlsBar/ControlsBar.tsx`、`src/components/viewer/GyroIndicator/GyroIndicator.tsx`、`src/components/viewer/SpeedTooltip/SpeedTooltip.tsx`、`src/hooks/useGyroscope.ts`、`src/hooks/useJoystick.ts`。
- 待补充：键盘-only 焦点顺序的整链路验证、真实 XR 会话中的“完全隐藏 rail”回归，以及低性能真实设备上的默认 effect / `无特效` 体验验证。
