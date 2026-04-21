## ADDED Requirements

### Requirement: 查看器 SHALL 提供专用的 reveal-effects rail
查看器 SHALL 在预览叠加层右侧提供一个专用的 reveal-effects rail，并与现有的 Help 和 Quick Controls 浮层分离。

#### Scenario: 桌面端叠加层垂直对齐
- **WHEN** 查看器在桌面布局下渲染且存在活动模型
- **THEN** Help 触发器、reveal-effects rail 和 Quick Controls 触发器 SHALL 共享相同的右侧内边距
- **AND** reveal-effects rail SHALL 垂直位于 Help 触发器与 Quick Controls 触发器之间

#### Scenario: 窄屏或粗指针设备布局
- **WHEN** 查看器渲染在窄视口或粗指针设备上
- **THEN** reveal-effects rail SHALL 保持可达，同时不阻塞 Help、reset、fullscreen 或 share 等关键预览操作

### Requirement: 查看器 SHALL 暴露精选 Spark reveal effects，并默认使用 Magic
查看器 SHALL 为当前活动模型预览暴露一组精选的 Spark reveal effects，并且在每次新的查看器会话开始时将激活效果初始化为 `Magic`。

#### Scenario: 查看器会话启动时默认效果
- **WHEN** 用户在主查看器中打开一个模型
- **THEN** reveal-effects rail SHALL 默认将 `Magic` 显示为当前选中效果
- **AND** 查看器 SHALL 无需用户打开设置即可直接使用 `Magic` 效果开始播放

#### Scenario: 切换支持的效果
- **WHEN** 用户从 rail 中选择另一个受支持的 reveal effect
- **THEN** 查看器 SHALL 在当前预览会话内切换激活效果
- **AND** 支持的效果集合 SHALL 包含 `Magic`、`Spread`、`Unroll`、`Twister` 和 `Rain`

### Requirement: 效果 replay SHALL 在不重载模型资源的情况下重启动画
查看器 SHALL 允许用户在不替换当前模型源、也不离开当前预览上下文的情况下重放当前 reveal 动画。

#### Scenario: 重放当前激活效果
- **WHEN** 用户触发当前 reveal effect 的 replay 操作
- **THEN** 当前效果的动画时间线 SHALL 从初始状态重新开始
- **AND** 底层模型资源 SHALL NOT 仅因为 replay 而被重新请求

### Requirement: Reveal-effects rail MUST 遵循查看器浮层的视觉与可用性规则
Reveal-effects rail MUST 使用与现有浮动控件一致的查看器浮层设计语言，并且在浮层能力受限时安全降级。

#### Scenario: 浮层视觉一致性
- **WHEN** reveal-effects rail 在查看器浮层中可见
- **THEN** 它 SHALL 使用与项目现有玻璃风格 Help / Quick Controls 浮层一致的半透明模糊背景、边框和交互反馈

#### Scenario: XR 或无可用预览状态
- **WHEN** 查看器处于 XR 模式或当前没有可用的活动模型预览
- **THEN** 系统 SHALL 完全隐藏 reveal-effects rail
- **AND** 现有 Help 与 Quick Controls 行为 SHALL 保持不受影响

#### Scenario: 移动端紧凑展示
- **WHEN** 查看器渲染在移动端或窄屏布局下
- **THEN** 系统 SHALL 不常驻展示桌面版完整竖向 rail
- **AND** 系统 SHALL 提供紧凑入口并以临时展开面板呈现效果选项，以降低对主渲染画面的遮挡

### Requirement: Reveal-effects UI MUST 具备国际化与可访问性
系统 MUST 为 reveal-effects rail 提供本地化的用户可见文本，以及可通过键盘 / 焦点访问的交互。

#### Scenario: 本地化标签与提示文案
- **WHEN** 应用语言在受支持语言之间切换
- **THEN** 所有 reveal-effects 标签、tooltip 和 replay 文案 SHALL 从对应语言资源中渲染

#### Scenario: 键盘可访问的效果切换
- **WHEN** 仅使用键盘的用户导航到 reveal-effects rail
- **THEN** 用户 SHALL 能够识别当前效果、切换效果并触发 replay
- **AND** 所有相关控件 SHALL 提供语义化控件类型与清晰可见的焦点指示
