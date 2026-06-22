## ADDED Requirements

### Requirement: 系统 SHALL 提供前馈重建引擎作为视频重建实验路线
系统 SHALL 支持在视频重建中使用前馈（feed-forward）相机位姿/几何推理作为可选实验引擎，仅替换 COLMAP 几何阶段，并复用现有 Nerfstudio 训练、导出、清理与模型图库后段；该引擎不可用时 MUST NOT 影响稳定 COLMAP 路线。

#### Scenario: 前馈引擎就绪时执行重建
- **WHEN** 前馈引擎及其权重在本机就绪，且用户以允许前馈的引擎策略提交视频重建任务
- **THEN** 系统 SHALL 在抽帧后用前馈推理估计相机位姿
- **AND** 系统 SHALL 将位姿写入训练所需的数据格式并跳过 COLMAP 几何阶段
- **AND** 系统 SHALL 复用现有训练、导出、清理与压缩流程生成模型图库兼容的 `.ply` 与尽可能的 `.spz`

#### Scenario: 前馈引擎未配置
- **WHEN** 前馈引擎或其权重未在本机配置
- **THEN** 稳定 COLMAP 路线 SHALL 保持完全可用
- **AND** UI SHALL 显示前馈引擎为未就绪的可选增强，而不是报告视频重建整体不可用

### Requirement: 引擎策略 SHALL 控制前馈与 COLMAP 的选择与回退
系统 SHALL 通过引擎策略 `自动` / `稳定` / `实验` 控制前馈与 COLMAP 的使用，并在前馈不可用或失败时按策略安全处理。

#### Scenario: 自动策略优先前馈
- **WHEN** 用户使用 `自动` 策略且前馈引擎就绪
- **THEN** 系统 SHALL 优先使用前馈引擎进行几何阶段

#### Scenario: 自动策略在前馈失败时回退
- **WHEN** `自动` 策略下前馈推理失败、产生无效位姿或显存不足
- **THEN** 系统 SHALL 自动回退到 COLMAP 稳定路线重做几何阶段
- **AND** 系统 SHALL 记录回退原因，且任务 SHALL 继续而不是直接失败

#### Scenario: 稳定策略不使用前馈
- **WHEN** 用户使用 `稳定` 策略
- **THEN** 系统 SHALL 始终使用 COLMAP 路线
- **AND** 系统 MUST NOT 调用前馈引擎

#### Scenario: 实验策略强制前馈但不可用
- **WHEN** 用户使用 `实验` 策略但前馈引擎或权重不可用
- **THEN** 系统 MUST 拒绝创建任务
- **AND** 系统 SHALL 返回可本地化的前馈不可用错误并提示如何配置
- **AND** 系统 MUST NOT 静默回退到 COLMAP

### Requirement: 系统 SHALL 检测前馈引擎与权重就绪状态
系统 SHALL 暴露前馈引擎推理环境与模型权重是否就绪的状态，供设置页诊断与任务创建判断使用。

#### Scenario: 用户在设置页查看前馈引擎状态
- **WHEN** 用户打开设置页的视频重建诊断
- **THEN** 系统 SHALL 显示前馈引擎与其权重的就绪或缺失状态
- **AND** 诊断信息 SHALL 使用本地化文案
- **AND** 诊断信息 MUST NOT 将未处理的堆栈作为主要用户提示

#### Scenario: 权重缺失时的状态
- **WHEN** 前馈推理环境存在但模型权重缺失
- **THEN** 系统 SHALL 报告权重未配置并说明这是可选增强
- **AND** 系统 SHALL 提示用户需自行下载配置权重

### Requirement: 前馈引擎权重 MUST NOT 默认打包或自动下载受限权重
为遵守开源许可，系统 MUST NOT 在默认安装中打包前馈模型权重，也 MUST NOT 自动下载受限或非商业许可的权重；权重由用户自行下载配置并接受其许可。

#### Scenario: 默认安装不含权重
- **WHEN** 用户进行默认安装
- **THEN** 安装产物 MUST NOT 包含前馈模型权重
- **AND** 系统 MUST NOT 在未经用户操作时自动下载受限权重

#### Scenario: 用户自行配置权重
- **WHEN** 用户按文档自行下载并放置前馈权重到约定位置
- **THEN** 系统 SHALL 在依赖检测中识别权重已就绪
- **AND** 后续允许前馈的任务 SHALL 可使用该引擎

### Requirement: 前馈路线 SHALL 遵守本地 GPU 的显存与帧预算约束
系统 SHALL 限制前馈推理一次处理的帧数与分辨率，避免在笔记本 GPU 上轻易耗尽显存；超限或显存不足时 SHALL 安全处理而非崩溃。

#### Scenario: 帧预算约束前馈推理
- **WHEN** 待处理帧数或分辨率超过前馈路线的安全上限
- **THEN** 系统 SHALL 通过下采样、分块或限制帧数控制资源使用

#### Scenario: 前馈显存不足
- **WHEN** 前馈推理因 GPU 显存不足失败
- **THEN** 系统 SHALL 在 `自动` 策略下回退 COLMAP，或在 `实验` 策略下以可本地化错误失败并建议降低帧数/分辨率
- **AND** 已存在的模型产物 MUST NOT 被删除

### Requirement: 前馈生成的模型 SHALL 与现有视频模型体验一致
前馈引擎生成的模型 SHALL 与现有 COLMAP 视频重建结果使用相同的输出契约与图库体验。

#### Scenario: 前馈结果进入模型图库
- **WHEN** 前馈路线成功完成视频重建
- **THEN** workspace `outputs/` 目录 SHALL 存在 `.ply` 模型并尽可能生成 `.spz`
- **AND** 模型 SHALL 在模型图库刷新后可见，并复用现有缩略图、原视频预览、下载与分享
- **AND** 响应 MUST NOT 暴露源视频或工作区的绝对文件系统路径

### Requirement: 前馈引擎 SHALL NOT 破坏现有重建与播放行为
引入前馈引擎 SHALL NOT 改变现有图片生成、照片转 3D、本地视频播放、模型查看以及既有 COLMAP 视频重建的行为。

#### Scenario: 既有 COLMAP 视频重建不回归
- **WHEN** 用户使用 `稳定` 策略或前馈不可用
- **THEN** 系统 SHALL 以与引入前馈前一致的行为执行 COLMAP 视频重建

#### Scenario: 其他既有能力不受影响
- **WHEN** 用户进行图片生成、照片转 3D、视频播放或模型查看
- **THEN** 这些能力 SHALL 保持与引入前馈前一致的行为
