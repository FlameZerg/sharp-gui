## 1. 依赖迁移与安装基线

- [x] 1.1 将前端 `@sparkjsdev/spark` 依赖从历史 Git 引用改为 npm 正式版 2.0.x 语义版本。
- [x] 1.2 重建前端 lock 文件并验证 Spark `resolved` 来源为 npm registry（非 git+ssh）。
- [x] 1.3 执行一次干净安装并记录 Spark 实际安装版本与 peer 依赖校验结果。

## 2. API 对齐与兼容路径收敛

- [x] 2.1 盘点并移除历史遗留内部字段依赖（含 stochastic 相关路径）。
- [x] 2.2 对齐 SparkRenderer/SplatMesh 参数到正式版公开 API，并补充必要注释说明迁移意图。
- [x] 2.3 完成 XR 更新路径校准（默认路径与手动更新策略）并保留可回退配置开关。

## 3. LoD Quick Wins 集成

- [x] 3.1 在状态层定义 LoD 快速预设（性能优先/平衡/细节优先）及参数映射。
- [x] 3.2 在 viewer 侧接入预设切换逻辑，确保切换即时生效且无需重载。
- [x] 3.3 为具备 nonLoD 数据的场景接入 LoD/nonLoD 对比开关。
- [x] 3.4 验证预设与对比开关不会破坏现有交互（相机重置、orbit、点击聚焦、模型变换）。

## 4. RAD + Paged 可选加载链路

- [x] 4.1 在加载流程中新增 RAD 模式配置入口（含是否启用 paged）。
- [x] 4.2 实现 RAD 模式下的 SplatMesh 初始化分支，并保留现有 SPZ/PLY/SPLAT 回退分支。
- [x] 4.3 定义并补充离线 `build-lod` 到 RAD 产物的操作规范（命令、输入输出、命名约定）。

## 5. 迁移验证矩阵与文档完善

- [x] 5.1 建立迁移验收清单（构建、加载、LoD、XR 生命周期、关键交互）。
- [x] 5.2 输出迁移前后基线对比记录模板（加载时延、FPS、内存峰值、稳定性备注）。
- [x] 5.3 更新项目规范与 OpenSpec 文档中 Spark 版本与迁移说明，消除历史预发术语表述。

## 6. 最终自检与变更就绪

- [x] 6.1 运行 lint/build 并修复与本变更相关的问题。
- [x] 6.2 对照 specs 中所有 requirement/scenario 进行覆盖性自检并补齐遗漏。
- [x] 6.3 确认 OpenSpec 状态达到 apply-ready（tasks 工件完成）。
