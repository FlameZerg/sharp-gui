## Why

当前后端入口 `app.py` 已增长到约 2900 行，集中承载 Flask 应用创建、局域网门禁、模型图库、本地照片图库、照片相册上传、任务队列、模型格式转换、静态文件服务、设置管理、重启与导出 HTML 等职责。随着照片图库、LAN 门禁、SPZ 导出、局域网相册上传等能力继续增加，单文件结构已经让阅读、变更定位、权限边界审查和后续扩展变得困难。

本次变更的目标是在不改变现有用户可见行为和 API 契约的前提下，将后端拆分为清晰的包结构与模块边界，让后续维护可以围绕业务域和服务层展开，而不是继续在单个入口文件中叠加逻辑。

## What Changes

- 将后端从单文件 `app.py` 渐进拆分为包化结构，保留 `app.py` 作为兼容启动入口。
- 引入 Flask app factory，集中创建应用、注册 request hooks、注册 routes/blueprints、启动后台任务线程。
- 按职责拆分后端模块：
  - 运行时与配置：环境变量、日志、`config.json` 读写、workspace 路径派生。
  - 安全与门禁：Host/Origin 校验、owner 判定、访问码 session、权限分级矩阵、CORS 响应。
  - 路由层：按前端 API 域拆分 auth、gallery、photo gallery、tasks、settings、files、export、frontend static。
  - 服务层：模型图库、照片图库（含相册上传、文件名净化、图片验证和索引刷新）、任务队列、PLY/SPZ/Splat 转换、独立 HTML 导出、文件夹选择。
- 明确模块依赖方向：路由层只负责 HTTP 解析与响应封装，业务逻辑下沉到服务层；服务层避免直接依赖 Flask `request/g/jsonify`。
- 保持所有现有 HTTP 路径、请求参数、响应结构、权限语义和启动脚本入口兼容。
- 将新增的 `POST /api/photo-albums/<album_id>/uploads` 纳入重构兼容范围，明确其 form-data 契约、相册 root 写入边界、失败清理、扫描刷新和 LAN 门禁权限语义。
- 正式引入 pytest 作为后端测试框架，为重构后的关键边界建立可持续测试覆盖，重点覆盖 LAN 门禁、静态文件白名单、照片图库路径安全、任务队列生命周期和导出流程。
- 保证现有一键安装、构建、运行、发布脚本与 GitHub Release 自动化流程不因后端目录拆分而失效。

范围内：

- 后端 Python 代码结构调整。
- 后端内部模块边界和依赖方向治理。
- 现有照片相册上传 API 的模块归属、权限语义、路径安全和测试覆盖。
- 后端相关规则/README 中关于 `app.py` 单文件描述的同步更新。
- pytest 后端测试覆盖与必要的脚本化回归验证。
- 安装、构建、运行、发布和 GitHub Release 自动化兼容性验证。

范围外：

- 不新增用户可见功能。
- 不改现有 `/api/*`、`/files/*`、`/assets/*` 路径契约。
- 不重写前端状态管理、组件结构或 API 调用语义。
- 不修改 `ml-sharp/`、`templates/index.html`、`static/lib/` 的 legacy 实现。
- 不引入数据库、ORM、异步任务框架或新的 Web 框架。

## Capabilities

### New Capabilities

- `backend-modular-architecture`: 定义后端模块化架构的行为约束，包括入口兼容、路由契约保持、服务边界、权限集中治理和重构验证要求。

### Modified Capabilities

- 无。现有业务能力的需求行为不变，本次变更只调整后端内部结构。

## Impact

- 主要影响：
  - `app.py`
  - 新增后端目录 `backend/`
  - `.agents/rules/project-overview.md`
  - `.agents/rules/backend-guide.md`
  - `.agents/rules/testing.md`
  - `.agents/workflows/new-api-endpoint.md`
  - 一键脚本：`install.sh` / `install.bat` / `build.sh` / `build.bat` / `run.sh` / `run.bat` / `run_verbose.sh` / `run_verbose.bat` / `release.sh` / `release.bat`
  - GitHub Release 自动化：`.github/workflows/release.yml`
- 行为保持：
  - React 前端 `frontend/src/api/*` 不应需要契约调整。
  - Legacy 前端 `templates/index.html` 的后端调用路径保持可用。
  - 安装、构建、运行、verbose 运行、发布打包和 GitHub Release 流程保持兼容。
- 风险区域：
  - LAN 门禁 owner/unlocked/public/conditional 权限矩阵。
  - `/files/*` 静态文件白名单与敏感文件拒绝。
  - 照片相册上传的条件写入权限、文件名净化、图片格式验证、批量上限和无效文件清理。
  - 任务队列共享状态、后台线程启动时机和取消运行中 subprocess。
  - workspace 切换、`/api/restart` 文件描述符关闭与监听地址重新绑定。
  - 照片图库索引锁、路径归一化、缩略图缓存、相册上传后的扫描刷新和批量 ZIP 下载临时文件清理。
