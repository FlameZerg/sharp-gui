## Why

当前模型列表在条目数量上来之后会明显变卡，快速滚动时还会出现缩略图短暂消失、重新出现、列表刷新后视觉跳动等问题。现有实现主要依赖图片懒加载，但还没有把“长列表渲染、缩略图稳定性、增量刷新、状态订阅隔离”作为一个完整能力来设计，因此用户在浏览较多模型时很容易感知到不流畅和不稳定。

Sharp GUI 已经进入“生成后反复浏览、切换、对比模型”的高频使用阶段，模型列表的顺滑度正在直接影响主流程体验。现在把这块能力正式规格化，可以让后续优化围绕清晰的行为目标推进，而不是零散止痛。

## What Changes

- 新增一个面向侧边栏模型列表的“流畅浏览与稳定展示”能力，定义模型条目在大量数据场景下的可接受交互行为。
- 明确长列表的渲染目标：
  - 随着模型数量增长，列表浏览体验仍需保持可操作、可预测，不因全量渲染和无关状态更新而显著退化。
  - 列表滚动、选中模型、侧边栏展开/收起、任务完成后图库刷新等关键路径不得引入明显卡顿或跳位。
- 明确缩略图展示目标：
  - 可视区及其邻近区域的缩略图应稳定呈现，快速滚动时不得频繁出现空白闪烁或“消失再出现”的破碎感。
  - 缩略图缺失、加载失败或后台文件状态变化时，系统需提供稳定的降级反馈，而不是直接暴露原始异常体验。
- 明确图库刷新与任务联动目标：
  - 任务完成后，图库更新应尽量采用对滚动位置和可见内容友好的方式，避免破坏用户当前浏览上下文。
  - 与模型格式偏好、预览打开、设置切换等无关的状态变更，不应导致整份列表重复计算与重渲染。
- In scope:
  - `frontend/src/components/gallery`、`frontend/src/components/layout/Sidebar` 内的列表呈现与交互行为
  - `frontend/src/store/useAppStore.ts`、`frontend/src/hooks/useTaskQueue.ts` 相关的状态订阅与刷新策略
  - `frontend/src/api/gallery.ts`、`frontend/src/types/gallery.ts`、后端 `app.py` 中图库与缩略图接口行为
  - 与该能力直接相关的回归验证与性能验收基线
- Out of scope:
  - Three.js / Spark 模型预览渲染链路本身的性能优化
  - 新的搜索、筛选、分组、排序产品功能
  - 侧边栏整体视觉风格重设计
  - 模型生成算法、SPZ/PLY 转换逻辑、Legacy `templates/` 前端重构

## Capabilities

### New Capabilities
- `model-gallery-smoothness`: 为侧边栏模型列表建立可测试的流畅性与稳定性契约，覆盖长列表渲染、缩略图稳定展示、图库增量刷新以及异常降级体验。

### Modified Capabilities
- (none)

## Impact

- Affected frontend areas:
  - `frontend/src/App.tsx`
  - `frontend/src/components/gallery/*`
  - `frontend/src/components/layout/Sidebar/*`
  - `frontend/src/components/layout/TaskQueue/*`
  - `frontend/src/store/useAppStore.ts`
  - `frontend/src/hooks/useTaskQueue.ts`
  - `frontend/src/api/gallery.ts`
  - `frontend/src/types/gallery.ts`
- Affected backend areas:
  - `app.py` 中的 `/api/gallery`、缩略图生成与 `/files/*` 静态文件返回策略
- Possible dependency impact:
  - 可能引入轻量级前端列表虚拟化能力，或采用项目内实现的 windowing 方案；是否新增依赖由设计阶段最终确认
- Validation impact:
  - 需要补充针对大列表滚动、缩略图可见性、任务完成后刷新稳定性和关键路径回归的验证步骤
