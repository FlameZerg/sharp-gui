## ADDED Requirements

### Requirement: 后端 SHALL 保持现有入口兼容

后端模块化重构后，系统 SHALL 保持现有启动入口和 Flask 应用导入方式可用。

#### Scenario: 使用现有脚本启动

- **WHEN** 用户通过现有 `run.sh`、`run.bat`、`run_verbose.sh`、`run_verbose.bat` 或等效的 `python app.py` 方式启动服务
- **THEN** 系统 SHALL 正常创建 Flask 应用并监听配置决定的地址和端口
- **AND** HTTPS 证书检测、verbose 日志、LAN IP 启动提示和 `SHARP_DEBUG` 行为 SHALL 与重构前保持一致

#### Scenario: 导入 Flask app 对象

- **WHEN** 测试或工具代码从入口模块导入 Flask app 对象
- **THEN** 系统 SHALL 提供可用的 Flask app 实例
- **AND** 导入入口模块 MUST NOT 破坏现有测试或开发工具对 `app` 变量的引用

### Requirement: 后端 SHALL 保持现有 HTTP 契约不变

后端模块化重构后，系统 SHALL 保持现有 `/api/*`、`/files/*`、`/assets/*` 和前端入口路由的 URL、HTTP 方法、请求参数、响应字段和状态码语义。

#### Scenario: React 前端请求现有 API

- **WHEN** React 前端通过 `frontend/src/api/*` 中已有函数请求后端
- **THEN** 后端 SHALL 返回与重构前兼容的响应结构
- **AND** 前端 API 层 MUST NOT 因本次重构被迫修改端点路径或字段名称

#### Scenario: Legacy 前端请求现有 API

- **WHEN** legacy `templates/index.html` 使用现有 API 路径浏览、生成、下载或导出模型
- **THEN** 后端 SHALL 继续接受这些请求
- **AND** legacy 前端 MUST NOT 因后端模块拆分而失效

#### Scenario: 路由注册完成

- **WHEN** Flask 应用创建完成
- **THEN** 系统 SHALL 注册重构前已有的公开页面、认证、模型图库、照片图库、任务、设置、静态文件、下载和导出路由
- **AND** 任一既有业务端点 MUST NOT 因遗漏注册而返回 404

### Requirement: 后端 SHALL 集中维护访问控制边界

后端模块化重构后，系统 SHALL 继续以集中权限矩阵维护 Public、Unlocked、Owner 和 Conditional 访问级别，并保持现有 LAN 门禁语义。

#### Scenario: 远程未认证客户端访问私有读取资源

- **WHEN** LAN 门禁开启且远程未认证客户端请求模型列表、照片列表、缩略图、原图、下载、导出或 `/files/*` 私有资源
- **THEN** 系统 MUST 拒绝该请求
- **AND** 系统 MUST NOT 返回私有元数据或文件内容

#### Scenario: 远程客户端访问 owner-only 操作

- **WHEN** 远程客户端请求设置写入、删除、重启、目录管理、任务取消、批量转换或访问控制管理端点
- **THEN** 系统 MUST 拒绝该请求，除非真实请求来源满足 owner 条件
- **AND** 系统 MUST NOT 通过客户端可控转发头授予 owner 权限

#### Scenario: 条件远程生成

- **WHEN** 远程已认证客户端提交 `/api/generate` 或 `/api/photo-conversions`
- **THEN** 系统 SHALL 仅在 LAN 门禁开启且 owner 显式启用远程生成时创建任务
- **AND** 其他情况下系统 MUST 拒绝创建生成任务

#### Scenario: 新增 API 默认权限归类

- **WHEN** 后续新增私有 `/api/*` 或 `/files/*` 端点
- **THEN** 系统 SHALL 要求开发者在集中权限矩阵中确认其访问级别
- **AND** 未明确归类的私有读取资源 SHALL 至少按 Unlocked 级别保护

### Requirement: 后端 SHALL 将路由层与服务层职责分离

后端模块化重构后，系统 SHALL 将 HTTP 解析与响应封装保留在路由层，并将可复用业务逻辑放入服务层。

#### Scenario: 路由处理请求

- **WHEN** 路由函数处理 API 请求
- **THEN** 路由层 SHALL 负责读取 Flask request、调用服务、返回 JSON 或文件响应
- **AND** 路由层 MUST NOT 承载大段可复用业务流程，除非该逻辑只属于 HTTP 封装

#### Scenario: 服务执行业务逻辑

- **WHEN** 模型图库、照片图库、任务队列、模型转换、文件解析、导出 HTML 或文件夹选择逻辑被执行
- **THEN** 系统 SHALL 通过对应服务模块承载主要业务逻辑
- **AND** 服务模块 SHALL 尽量避免直接依赖 Flask `request`、`g` 或 `jsonify`

### Requirement: 后端 SHALL 以单一上下文管理配置、路径和共享状态

后端模块化重构后，系统 SHALL 避免在多个模块中复制 workspace 路径、配置状态和任务队列共享状态。

#### Scenario: workspace 路径被使用

- **WHEN** 任一后端模块需要访问输入目录、输出目录、模型缩略图目录、照片图库缓存目录或照片索引文件
- **THEN** 系统 SHALL 从同一个配置与路径上下文派生这些路径
- **AND** 模块间 MUST NOT 使用相互矛盾的 workspace 路径

#### Scenario: 任务队列状态被访问

- **WHEN** 系统创建、列出、取消或清理生成任务
- **THEN** 系统 SHALL 通过单一任务队列管理对象维护队列、任务状态、运行中进程和线程锁
- **AND** 系统 MUST NOT 因模块拆分创建多个互相不可见的任务状态集合

#### Scenario: 应用被测试或工具导入

- **WHEN** 测试或工具代码导入 Flask app 或调用 app factory 创建应用
- **THEN** 系统 SHALL 创建可用的应用与任务队列管理对象
- **AND** 系统 MUST NOT 在默认导入路径启动后台 worker 或 cleanup 线程

#### Scenario: 服务通过运行入口启动

- **WHEN** 用户通过 `python app.py` 或项目启动脚本运行服务
- **THEN** 系统 SHALL 在 HTTP 服务启动前显式启动任务 worker 和 cleanup 线程
- **AND** worker 启动操作 MUST 是幂等的，避免重复启动多个处理同一队列的 worker 集合

#### Scenario: 照片索引被读写

- **WHEN** 系统扫描相册、解析 photo id、生成照片缩略图或更新照片元数据
- **THEN** 系统 SHALL 使用一致的照片索引读写入口和锁保护
- **AND** 系统 MUST NOT 因并发读写导致索引损坏

### Requirement: 后端 SHALL 保持文件系统安全约束

后端模块化重构后，系统 SHALL 保持现有文件路径安全约束，防止访问 workspace、相册 root 或允许服务根之外的文件。

#### Scenario: 请求敏感系统文件

- **WHEN** 任意客户端通过静态文件路由请求 `config.json`、TLS 私钥、证书、后端源码、环境文件或等效敏感文件
- **THEN** 系统 MUST 拒绝该请求
- **AND** 系统 MUST NOT 返回文件内容

#### Scenario: 请求路径穿越或符号链接逃逸

- **WHEN** 任意客户端构造相对穿越、绝对路径、跨盘符路径或符号链接逃逸请求
- **THEN** 系统 MUST 拒绝该请求
- **AND** 系统 MUST NOT 泄露允许根之外的文件内容

#### Scenario: 照片图库解析 photo id

- **WHEN** 系统根据 photo id 提供照片列表、缩略图、原图、下载或转换
- **THEN** 系统 MUST 从索引和已配置相册 root 反查真实文件路径
- **AND** 系统 MUST 再次验证真实路径仍位于对应相册 root 内

### Requirement: 后端 SHALL 提供基于 pytest 的重构验证覆盖

后端模块化重构完成后，系统 SHALL 使用 pytest 提供足够的后端验证来证明行为契约未被破坏。

#### Scenario: 验证路由契约

- **WHEN** 开发者运行 pytest 后端验证
- **THEN** 验证 SHALL 覆盖现有关键 API 路径仍被注册且返回预期类型响应
- **AND** 验证 SHALL 覆盖 React 前端当前依赖的主要 API 域

#### Scenario: 验证安全边界

- **WHEN** 开发者运行 pytest 后端验证
- **THEN** 验证 SHALL 覆盖 LAN 门禁开启和关闭时的私有读取、owner-only 写操作、远程生成条件和敏感文件拒绝
- **AND** 验证 MUST 确认客户端可控转发头不能提升为 owner 权限

#### Scenario: 验证核心业务路径

- **WHEN** 开发者运行 pytest 后端验证
- **THEN** 验证 SHALL 覆盖模型图库、照片图库、任务队列状态、任务取消、静态文件白名单和导出 HTML 的关键路径
- **AND** 验证 SHALL 能发现模块拆分造成的注册遗漏、路径上下文错误或共享状态重复实例问题

#### Scenario: 普通运行不依赖测试工具

- **WHEN** 普通用户通过一键脚本运行 Sharp GUI
- **THEN** 系统 SHALL 正常启动应用
- **AND** 普通运行路径 MUST NOT 要求用户主动执行 pytest

### Requirement: 后端重构 SHALL 保持脚本与发布自动化兼容

后端模块化重构后，系统 SHALL 保持现有安装、构建、运行、发布和 GitHub Release 自动化流程可用。

#### Scenario: 一键安装与运行脚本执行

- **WHEN** 用户执行现有一键安装、普通运行或 verbose 运行脚本
- **THEN** 脚本 SHALL 能找到正确的后端入口、项目根目录、配置文件、证书文件和运行时资源
- **AND** 脚本 MUST NOT 因后端代码迁入 `backend/` 目录而失败

#### Scenario: 构建与发布脚本执行

- **WHEN** 开发者执行现有构建、发布或 Windows 便携包相关脚本
- **THEN** 脚本 SHALL 继续包含必要的后端入口、后端模块、前端构建产物、模板、静态资源和工具脚本
- **AND** 发布产物 MUST NOT 缺失运行后端所需的 `backend/` 代码

#### Scenario: GitHub Release 自动化执行

- **WHEN** GitHub Release workflow 根据 tag 或发布流程运行
- **THEN** workflow SHALL 使用更新后的后端路径假设完成构建和打包
- **AND** workflow MUST NOT 继续依赖已失效的单文件后端布局假设

### Requirement: 后端开发文档 SHALL 反映模块化结构

后端模块化重构完成后，项目文档和 Agent 规则 SHALL 反映新的后端结构与新增 API 工作方式。

#### Scenario: 开发者查阅后端规则

- **WHEN** 开发者阅读后端架构规则或项目总览
- **THEN** 文档 SHALL 描述后端包结构、app factory、routes/services/security/config/paths 的职责
- **AND** 文档 MUST NOT 继续把 `app.py` 描述为承载全部后端逻辑的单文件实现

#### Scenario: 开发者新增 API

- **WHEN** 开发者按新增 API 工作流添加后端端点
- **THEN** 工作流 SHALL 指引开发者选择对应 route 模块、必要时添加 service 逻辑、并同步前端 API/types
- **AND** 工作流 SHALL 要求开发者确认集中权限矩阵中的访问级别
