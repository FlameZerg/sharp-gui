## ADDED Requirements

### Requirement: 系统 SHALL 从本地视频创建重建任务
系统 SHALL 允许具备生成权限的用户从已配置本地相册中的受支持视频创建静态 3DGS 重建任务，并且不得向前端暴露源视频的绝对文件系统路径。

#### Scenario: 用户从视频创建重建任务
- **WHEN** 具备生成权限的用户提交一个受支持的本地相册视频用于 3D 重建
- **THEN** 系统 SHALL 为该视频创建一个重建任务
- **AND** 该任务 SHALL 出现在现有任务队列响应中
- **AND** 响应 SHALL 使用稳定媒体 ID 或安全文件名引用来源
- **AND** 响应 MUST NOT 暴露源视频的绝对文件系统路径

#### Scenario: 用户提交照片或未知媒体
- **WHEN** 用户向视频重建入口提交照片、未知媒体 ID 或非视频媒体
- **THEN** 系统 MUST 拒绝该请求
- **AND** 系统 SHALL 不创建任务
- **AND** 前端 SHALL 显示本地化错误原因

#### Scenario: 源视频不再存在
- **WHEN** 用户提交的视频 ID 曾经存在但源文件已被移动、删除或相册索引过期
- **THEN** 系统 MUST 拒绝创建重建任务
- **AND** 系统 SHALL 返回可理解的源文件不可用错误
- **AND** 系统 MUST NOT 尝试访问相册根目录之外的路径

#### Scenario: 远程用户没有生成权限
- **WHEN** 未获得远程生成权限的远程客户端尝试创建视频重建任务
- **THEN** 系统 MUST 拒绝请求
- **AND** 系统 MUST NOT 创建任务或复制媒体到工作区
- **AND** UI SHALL 以和现有生成权限一致的方式提示权限不足

### Requirement: 视频重建任务 SHALL 支持模式和质量选择
系统 SHALL 在任务创建前支持 `自动`、`物品`、`环境` 三种重建模式，以及 `快速预览`、`高质量`、`极致` 三种质量档位。

#### Scenario: 用户接受默认选项
- **WHEN** 用户不修改重建弹窗中的模式和质量
- **THEN** 任务 SHALL 使用 `自动` 模式
- **AND** 任务 SHALL 使用设置中配置的默认质量档位
- **AND** 弹窗 SHALL 在提交前显示即将使用的默认值

#### Scenario: 用户选择物品模式
- **WHEN** 用户选择 `物品` 模式并提交任务
- **THEN** 任务 SHALL 记录为 object-centric 重建
- **AND** UI SHALL 在提交前显示所选模式
- **AND** 任务阶段或详情 SHALL 能表达是否使用了前景处理或降级路径

#### Scenario: 用户选择环境模式
- **WHEN** 用户选择 `环境` 模式并提交任务
- **THEN** 任务 SHALL 记录为 environment-centric 重建
- **AND** UI SHALL 在提交前显示所选模式

#### Scenario: 请求包含非法选项
- **WHEN** 请求中包含不受支持的模式、质量档位、引擎策略或帧预算
- **THEN** 系统 MUST 拒绝请求
- **AND** 任务队列 SHALL 保持不变
- **AND** 前端 SHALL 显示本地化校验错误

### Requirement: 重建管线 SHALL 生成现有模型图库兼容的产物
成功的视频重建任务 SHALL 在现有模型输出目录生成 `.ply` 模型，并尽可能生成同名 `.spz` 紧凑模型，使现有模型图库、查看器、下载和导出流程可以复用。

#### Scenario: 视频重建成功完成
- **WHEN** 视频重建任务成功完成
- **THEN** workspace `outputs/` 目录 SHALL 存在一个 `.ply` 模型
- **AND** 系统 SHALL 尝试生成同名 `.spz` 模型
- **AND** 生成的模型 SHALL 在模型图库刷新后可见
- **AND** 任务 SHALL 进入 completed 状态

#### Scenario: SPZ 压缩失败但 PLY 已生成
- **WHEN** 视频重建已成功生成 `.ply`，但 `.spz` 压缩失败
- **THEN** 任务 SHALL 记录清晰的 SPZ 压缩失败详情
- **AND** `.ply` 产物 SHALL 保留
- **AND** 模型图库 SHALL 仍可显示和打开 `.ply` 模型

#### Scenario: 用户打开生成结果
- **WHEN** 用户从模型图库选择视频重建生成的模型
- **THEN** 现有 Spark Viewer SHALL 按当前模型源选择规则加载该模型
- **AND** 用户 SHALL 能继续使用现有查看、下载和导出操作

#### Scenario: 输出名称与已有模型冲突
- **WHEN** 用户指定的输出名称或从视频派生的输出名称与已有模型冲突
- **THEN** 系统 SHALL 自动生成安全唯一的输出名称
- **AND** 系统 MUST NOT 覆盖已有 `.ply` 或 `.spz` 文件

#### Scenario: 输出名称包含特殊字符
- **WHEN** 视频文件名或用户输入的输出名称包含空格、中文或不适合作为文件名的字符
- **THEN** 系统 SHALL 生成安全且可识别的输出文件名
- **AND** 任务和图库 SHALL 显示可读名称

### Requirement: 任务队列 SHALL 展示视频重建阶段
任务队列 SHALL 为长时间运行的视频重建任务暴露清晰阶段，使用户无需阅读日志即可理解当前进度。

#### Scenario: 任务正在准备和抽帧
- **WHEN** 视频重建任务正在读取视频、抽取关键帧或过滤模糊帧
- **THEN** 任务 SHALL 报告抽帧或帧准备阶段
- **AND** 任务 SHALL 保持可取消

#### Scenario: 任务正在估计几何
- **WHEN** 视频重建任务正在估计相机位姿、稀疏点云、深度或初始化几何
- **THEN** 任务 SHALL 报告几何或位姿估计阶段

#### Scenario: 任务正在处理物品前景
- **WHEN** 物品模式任务正在生成或应用前景 mask
- **THEN** 任务 SHALL 报告前景处理阶段
- **AND** 如果前景依赖不可用导致降级，任务 SHALL 记录降级说明

#### Scenario: 任务正在优化高斯
- **WHEN** 视频重建任务正在训练或优化 Gaussian Splats
- **THEN** 任务 SHALL 报告高斯优化阶段
- **AND** 任务 SHALL 提供可显示的进度或阶段状态

#### Scenario: 任务正在导出和压缩
- **WHEN** 视频重建任务正在写出 `.ply` 或压缩 `.spz`
- **THEN** 任务 SHALL 报告导出或压缩阶段

#### Scenario: 用户取消重建任务
- **WHEN** 用户取消 pending 或 running 的视频重建任务
- **THEN** 系统 SHALL 在存在运行中子进程时请求终止该进程
- **AND** 任务 SHALL 到达 cancelled 状态
- **AND** 临时文件清理 SHALL 遵守保留中间文件设置

### Requirement: 系统 SHALL 检测重建依赖可用性
系统 SHALL 在用户运行视频重建前暴露必需和可选依赖的可用状态，并在依赖缺失时给出明确提示。

#### Scenario: 必需依赖缺失
- **WHEN** 视频抽帧、稳定重建或导出所需的必需依赖不可用
- **THEN** UI SHALL 显示视频重建不可用或处于降级状态
- **AND** 任务创建 SHALL 以明确依赖错误失败，而不是产生含糊的进程失败

#### Scenario: 可选实验依赖缺失
- **WHEN** VGGT、VGGT-Omega 或其他实验初始化依赖不可用
- **THEN** 自动引擎策略 SHALL 回退到稳定路线
- **AND** UI SHALL 显示实验路线不可用但稳定路线仍可尝试

#### Scenario: 用户强制选择不可用实验引擎
- **WHEN** 用户选择实验引擎但对应依赖不可用
- **THEN** 系统 MUST 拒绝创建任务
- **AND** UI SHALL 指出缺失的实验依赖

#### Scenario: 用户查看设置页诊断
- **WHEN** 用户打开设置页的视频重建诊断区域
- **THEN** 系统 SHALL 显示稳定依赖和实验依赖的可用状态
- **AND** 诊断信息 SHALL 使用本地化文案
- **AND** 诊断信息 MUST NOT 显示未处理的 Python 堆栈作为主要用户提示

### Requirement: 系统 SHALL 提供适合本地 GPU 的安全质量默认值
系统 SHALL 提供受控质量档位，限制关键帧数量、分辨率或训练资源，避免默认配置轻易耗尽笔记本 GPU 显存。

#### Scenario: 用户选择质量档位
- **WHEN** 用户选择 `快速预览`、`高质量` 或 `极致`
- **THEN** 任务 SHALL 记录所选档位
- **AND** 管线 SHALL 应用与该档位关联的资源边界

#### Scenario: 检测到 GPU 显存不足
- **WHEN** 重建任务因 GPU 显存不足失败
- **THEN** 任务 SHALL 失败并给出建议降低质量档位、减少关键帧或降低分辨率的用户可见提示
- **AND** 已存在的模型产物 MUST NOT 被删除

#### Scenario: 多个 GPU 重任务同时提交
- **WHEN** 用户提交多个图片生成或视频重建任务
- **THEN** 系统 SHALL 默认串行处理这些 GPU-heavy 任务
- **AND** UI SHALL 保留队列顺序和各任务状态

#### Scenario: 用户配置显存预算
- **WHEN** 本机 owner 在设置中配置显存预算
- **THEN** 后续视频重建任务 SHALL 使用该预算选择默认资源边界
- **AND** 非本机用户 SHALL 不能修改该全局默认配置

### Requirement: 视频重建 UI MUST 本地化
系统 MUST 为视频重建动作、弹窗、选项、依赖状态、任务阶段、权限提示、失败原因和设置项提供中英文文本。

#### Scenario: 语言切换时重建 UI 可见
- **WHEN** 用户在视频重建弹窗、任务队列或设置诊断可见时切换语言
- **THEN** 所有可见视频重建文本 SHALL 从当前语言资源渲染
- **AND** 英文和中文 locale 文件 SHALL 包含匹配 key

### Requirement: 系统 SHALL 保持现有图片生成和视频播放行为
新增视频重建 SHALL NOT 破坏现有图片生成、照片转 3D 或本地视频预览能力。

#### Scenario: 用户上传图片生成 3D
- **WHEN** 用户通过现有上传入口提交图片文件
- **THEN** 系统 SHALL 创建与当前行为一致的 SHARP 图片生成任务
- **AND** 完成的图片任务 SHALL 继续生成模型图库兼容的 `.ply` 和 `.spz` 产物

#### Scenario: 用户从相册照片转 3D
- **WHEN** 用户从本地相册选择照片并执行转 3D
- **THEN** 系统 SHALL 继续创建现有照片转换任务
- **AND** 视频 SHALL NOT 被错误提交到照片转换流程

#### Scenario: 用户预览本地视频
- **WHEN** 用户从媒体图库打开本地视频
- **THEN** 播放、下载、seek、音量、全屏、导航和关闭控制 SHALL 保持可用
- **AND** 新增重建操作 MUST NOT 阻塞或遮挡核心播放控制
