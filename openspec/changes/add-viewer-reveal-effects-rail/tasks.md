## 1. 查看器浮层骨架

- [ ] 1.1 创建独立的 `ViewerRevealEffectsRail` 组件模块，并在 `ViewerCanvas` 中挂载，完成本地 `Magic` 默认状态与 replay 操作联动。
- [ ] 1.2 增加共享的查看器浮层对齐样式 / token，让 Help、reveal-effects rail 与 Quick Controls 保持同一条右侧垂直基线，并统一项目的毛玻璃背景风格。
- [ ] 1.3 为 reveal-effects 标签、tooltip 与 replay 文案补齐 `frontend/src/i18n/en.json` 和 `frontend/src/i18n/zh.json` 国际化资源。
- [ ] 1.4 为移动端实现紧凑入口与临时展开面板，避免常驻桌面版完整竖向 rail 对主渲染画面造成遮挡。

## 2. Spark Reveal Effect 集成

- [ ] 2.1 扩展 `useViewer` 以接收当前激活效果与 replay token，并将 Spark `dyno` / `objectModifier` 配置绑定到当前 `SplatMesh` 生命周期。
- [ ] 2.2 实现精选效果集（`Magic`、`Spread`、`Unroll`、`Twister`、`Rain`），并基于当前 mesh 的 bounds 做模型空间归一化，而不是沿用示例资源的硬编码偏移。
- [ ] 2.3 保证效果切换与 replay 只重启动画、不重新获取模型资源，同时保持 transform controls、camera reset 与 LoD 行为在 modifier 生效时仍然正常。
- [ ] 2.4 为无模型、查看器重初始化、窄屏与 XR 状态增加可用性处理，其中 XR 下完全隐藏 rail，且不破坏现有 Help / Quick Controls 浮层行为。

## 3. 回归与验证

- [ ] 3.1 验证键盘 / 焦点行为与响应式布局，确保 rail 或其移动端紧凑入口保持可访问，同时不遮挡 Help、reset、fullscreen、share 等关键操作。
- [ ] 3.2 冒烟测试主查看器路径：新会话默认 `Magic`、切换效果可在原地生效、replay 可重启当前效果、Help / rail / Quick Controls 在桌面端保持对齐。
- [ ] 3.3 额外验证移动端与 XR 路径：移动端只显示紧凑入口并在选择后安全收起，XR 下完全不显示 rail。
- [ ] 3.4 运行项目前端校验命令，并记录构建、类型检查或 viewer 回归问题的后续修复项。
