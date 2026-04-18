## Context

当前项目前端对 Spark 的声明依赖是历史 Git 分支引用，锁文件解析结果与正式版脱节，导致“声明版本”“实际安装版本”“官方文档版本”不一致。

项目中已存在 Spark 2.0 风格用法（SparkRenderer + SplatMesh + LoD），但仍保留少量历史兼容逻辑（例如对 stochastic 内部字段的防御式访问）。这类隐式依赖在正式版演进下存在不稳定风险。

用户目标是优先完成迁移升级，并顺带集成低成本高收益特性；当前阶段不考虑发布流程。

## Goals / Non-Goals

**Goals:**
- 将 Spark 依赖升级并固定到 npm 正式版 2.0.0 语义版本线，消除历史 Git 引用带来的版本漂移。
- 确保现有核心能力（普通浏览、LoD、XR）在正式版下行为稳定并可回归验证。
- 引入“简单但有效”的新特性集成：LoD 快速调优、LoD/非 LoD 对比、RAD paged 流式加载可选路径。
- 形成可执行迁移方案与验证矩阵，供后续实现阶段直接落地。

**Non-Goals:**
- 不包含发布编排、灰度发布、回滚发布流程与上线窗口管理。
- 不进行大规模 UI 重构或渲染架构重写。
- 不一次性引入所有 Spark 2.0 高阶能力（如完整 SparkXr 替换、自定义 shader 全链路改造）。

## Decisions

### 1) 依赖来源切换到 npm 正式版并重建锁文件
- Decision:
  - 将 `@sparkjsdev/spark` 从历史 Git 引用切换为 npm 正式版（`^2.0.0`）。
  - 强制重建 lock 文件，确保 `resolved` 指向 npm tarball，而非 git commit。
- Rationale:
  - 保证可重复安装与版本可追溯，和官方文档、tags、releases 保持一致。
- Alternatives considered:
  - 继续使用历史 Git 分支：会继续承受版本漂移与不可预期差异。
  - 直接固定单一 commit：可重复但无法自然获取稳定补丁，维护成本高。

### 2) 清理历史遗留内部字段依赖，收敛到公开 API
- Decision:
  - 迁移后不再依赖 `defaultView.stochastic` 这类历史内部字段。
  - XR 中保留“可控更新路径”（例如 manual update）的能力，但以正式版公开行为为基线校准。
- Rationale:
  - 降低未来升级 break risk；减少对非稳定内部结构的耦合。
- Alternatives considered:
  - 保留全部兼容分支：短期省事，但长期难维护且容易掩盖问题。

### 3) 快速收益优先：先做参数层能力，再做结构性优化
- Decision:
  - 首批集成以参数/配置层为主：LoD 预设、foveation 组合、LoD 与 nonLoD 对比开关。
  - 设置交互采用“预设优先 + 手动高级”模式：默认展示 performance / balanced / detail 预设，进入 manual 后才暴露高级项。
  - RAD + paged 作为可选加载路径接入，不强制覆盖所有模型源；快速预设不默认强制 RAD（包括 detail）。
- Rationale:
  - 实现成本低、收益明显，可快速验证稳定性与体验提升。
  - 避免普通用户直接暴露复杂参数，同时避免“无 RAD 资源时预设导致加载失败/刷错”的可用性问题。
- Alternatives considered:
  - 直接全面切换为 RAD：收益高但改动面过大，不适合第一阶段迁移。

### 5) 缺失 RAD 与包围盒能力差异的运行时兜底
- Decision:
  - 当 `.rad` 派生路径出现 404 时，记录该 URL 的缺失状态，后续同会话不重复尝试该 RAD 资源，直接走非 RAD 回退路径。
  - 相机重置中的包围盒计算仅在可用数据源（PackedSplats / ExtSplats）下启用，异常时退回默认 offset。
- Rationale:
  - 避免网络层持续 404 重试导致的控制台噪音与渲染线程干扰。
  - 兼容不同 splat 数据路径的能力差异，避免单点运行时异常破坏模型加载流程。
- Alternatives considered:
  - 每次切换都重试 RAD：逻辑简单，但在缺失资源场景会持续制造错误与性能噪声。
  - 对包围盒异常直接中断加载：会放大单项能力缺失带来的用户可见故障。

### 4) 建立“迁移验收矩阵”而非单点冒烟
- Decision:
  - 对普通渲染、LoD、XR、加载性能、内存峰值建立统一检查项。
  - 迁移前后进行同场景对比，形成基线记录。
- Rationale:
  - Spark 升级风险更多体现在运行行为，不仅是编译通过。
- Alternatives considered:
  - 仅做 lint/build：无法覆盖运行时渲染回归。

## Risks / Trade-offs

- [XR 行为差异] 正式版下 XR 更新时序可能与历史实现表现不同
  - Mitigation: 保留可切换更新策略并在 Quest/桌面模拟器双环境回归。

- [参数迁移误配] LoD/foveation 参数组合不当会影响视觉或性能
  - Mitigation: 预设分层（保守/平衡/高细节）+ 基线指标对比。

- [RAD 接入复杂度] 构建链路依赖离线工具，团队初次使用可能有门槛
  - Mitigation: 提供最小可运行 workflow（命令、输入输出约定、回退路径）。

- [RAD 缺失导致的重复请求噪声] 非 RAD 资产派生 URL 不存在时会产生重复 404 与日志噪声
  - Mitigation: 在会话内缓存缺失 RAD URL，优先走非 RAD 回退路径。

- [范围膨胀] “顺便集成新特性”可能引发超范围扩展
  - Mitigation: 明确首批仅纳入 quick wins，其他高级特性进入后续 change。

## Migration Plan

1. 依赖迁移
- 切换 `package.json` Spark 依赖到 npm 正式版。
- 清理并重建 lock，校验安装结果版本与来源。

2. API 对齐
- 清理历史遗留字段访问。
- 对 SparkRenderer/SplatMesh 参数进行正式版映射校准。

3. 回归验证
- 执行构建、渲染、LoD、XR 回归矩阵。
- 记录关键指标（加载时延、FPS、内存峰值）。

4. Quick wins 集成
- 增加 LoD 参数预设与可视化控制。
- 设置层采用“预设优先 + 手动高级”结构，默认隐藏高级参数。
- 增加 LoD/nonLoD 对比开关（当资源同时存在时）。

5. RAD 可选链路
- 增加 RAD + paged 的可选加载入口。
- 快速预设不强制开启 RAD，由 manual 高级设置显式控制。
- 保持原有 SPZ/PLY 等路径可用作为回退。
- 对缺失 RAD 场景增加重试抑制与稳定回退。

## Open Questions

- LoD 预设是否应按设备自动切换，还是默认固定“平衡”并允许手动切换？
- RAD 路径是否只对大模型开启，阈值如何定义（按文件体积还是 splat 数量）？
- LoD/nonLoD 对比开关是仅开发态可见，还是保留在常规调试 UI 中？
