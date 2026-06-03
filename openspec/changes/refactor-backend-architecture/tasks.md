## 1. 基线与保护网

- [ ] 1.1 记录当前 `app.py` 的 Flask route map，保存为重构前端点基线，覆盖页面、认证、模型图库、照片图库、任务、设置、静态文件和导出路由。
- [ ] 1.2 梳理当前 `app.py` 的全局状态与副作用清单，包括 workspace 路径、`photo_index_lock`、`task_status`、`running_processes`、后台线程启动和 verbose 日志。
- [ ] 1.3 正式引入 pytest 后端测试入口，建立 `tests/` 目录和基础 fixtures，能在不启动真实推理任务的情况下创建 Flask test client。
- [ ] 1.4 补充 route map pytest，确认关键现有端点注册完整且 React 前端 API 依赖的路径未缺失。
- [ ] 1.5 补充安全 pytest，覆盖门禁开/关、owner-only 拒绝远程、远程生成条件和转发头不能提升 owner。
- [ ] 1.6 补充静态文件安全 pytest，覆盖模型文件允许访问、敏感文件和路径穿越请求被拒绝。
- [ ] 1.7 补充高风险纯函数和服务层 pytest，覆盖配置 normalize、路径归一化、photo id 解析、任务状态操作和无需真实推理的入队/取消逻辑。
- [ ] 1.8 明确后端测试运行命令和依赖记录，确保普通一键运行路径不强制依赖 pytest。

## 2. 包结构与兼容入口

- [ ] 2.1 新增 `backend/` 目录骨架，包括 `app_factory.py`、`server.py`、`runtime.py`、`config.py`、`paths.py`、`security/`、`services/`、`routes/`。
- [ ] 2.2 实现 `create_app()` 初版，创建 Flask app、设置 template folder、初始化路径配置和挂载 TaskManager，但默认不启动后台 worker。
- [ ] 2.3 将 `app.py` 收敛为兼容入口，继续暴露 `app` 变量，并在 `__main__` 中调用新的 server 启动函数。
- [ ] 2.4 在 server 启动函数中显式启动 TaskManager worker/cleanup 线程，并确保启动操作幂等。
- [ ] 2.5 确认 `python app.py`、`from app import app` 和现有启动脚本路径仍可工作，其中 `from app import app` 不产生后台线程副作用。

## 3. 运行时、配置与路径上下文

- [ ] 3.1 将基础运行时常量和环境变量解析迁移到 `backend/runtime.py`，保持 `SHARP_FRONTEND_MODE`、`SHARP_VERBOSE`、`SHARP_LOG_LEVEL`、`SHARP_LOG_FILE`、`SHARP_DEBUG` 行为不变。
- [ ] 3.2 将 `load_config()`、`save_config()`、access-control 配置 normalize 相关纯逻辑迁移到 `backend/config.py`。
- [ ] 3.3 引入统一路径上下文，集中派生 workspace、inputs、outputs、模型缩略图、照片图库缓存、照片索引文件和允许服务根。
- [ ] 3.4 将目录创建逻辑放到应用创建阶段，确认 workspace 切换后仍遵循现有“保存后重启生效”语义。
- [ ] 3.5 迁移 verbose 日志 tee 和运行时诊断输出，确认 verbose 模式仍写入配置的日志文件。

## 4. 安全层迁移

- [ ] 4.1 将访问级别常量、Host/Origin 校验、owner 判定、access session 编解码、登录失败延迟和 auth status 构建迁移到 `backend/security/access_control.py`。
- [ ] 4.2 调整 `get_required_access_level()` 为集中权限矩阵函数，保持所有现有 Public、Unlocked、Owner、Conditional 路径语义不变。
- [ ] 4.3 将 `before_request` 和 `after_request` 注册迁移到 `backend/security/hooks.py`。
- [ ] 4.4 迁移 auth routes 到 `backend/routes/auth.py`，保持 `/api/auth/status`、`login`、`logout`、`access-code`、`revoke`、`settings` 契约不变。
- [ ] 4.5 保留路由内部已有的重复 owner 检查作为暂时纵深防御，并在文档中记录后续专门清理 TODO。
- [ ] 4.6 运行安全 pytest，确认门禁、CORS、owner-only、远程生成和敏感资源保护未回退。

## 5. 业务服务与路由迁移

- [ ] 5.1 迁移 React/Legacy 前端静态入口路由到 `backend/routes/frontend.py`，保持 `/`、`/assets/*` 和 React 根静态文件行为不变。
- [ ] 5.2 迁移静态文件解析与 `/files/*` 路由到 `services/static_files.py` 和 `routes/files.py`，保持白名单根与敏感文件拒绝逻辑不变。
- [ ] 5.3 迁移 PLY→Splat 与 PLY→SPZ 转换到 `services/model_convert.py`，确认 worker 和导出流程仍调用同一转换实现。
- [ ] 5.4 迁移模型图库逻辑到 `services/model_gallery.py` 和 `routes/gallery.py`，覆盖列表、上传入队、删除、模型下载、原图、缩略图、批量 SPZ 转换。
- [ ] 5.5 迁移照片图库逻辑到 `services/photo_gallery.py` 和 `routes/photo_gallery.py`，覆盖相册配置、扫描、分页排序、缩略图、原图、ZIP 下载和照片转 3D。
- [ ] 5.6 将任务队列封装为单一 `TaskManager`，迁移 worker、清理线程、任务状态、运行中进程、取消逻辑和文件入队逻辑，并支持受控启动/停止或测试禁用。
- [ ] 5.7 迁移任务 routes 到 `routes/tasks.py`，保持 `/api/tasks`、`/api/task/<id>/cancel` 和 `/api/generate` 响应结构不变。
- [ ] 5.8 迁移设置、重启和文件夹选择到 `routes/settings.py`、`services/folder_picker.py` 和 server 支撑函数，保持 workspace 设置、model_format、browse-folder、restart 行为不变。
- [ ] 5.9 迁移独立 HTML 导出到 `services/export_html.py` 和 `routes/export.py`，确认 SPZ 默认导出和 PLY 兼容导出都能返回 HTML 附件。
- [ ] 5.10 删除或收敛 `app.py` 中已迁移的旧实现，避免同一功能存在两套来源。

## 6. 文档与开发规范同步

- [ ] 6.1 更新 `.agents/rules/project-overview.md`，将后端描述从单文件模式改为模块化包结构。
- [ ] 6.2 更新 `.agents/rules/backend-guide.md`，说明 app factory、routes、services、security、config、paths、TaskManager 的职责边界。
- [ ] 6.3 更新 `.agents/rules/testing.md`，将 pytest 后端测试作为正式推荐/本次落地方式，并记录关键覆盖目标。
- [ ] 6.4 更新 `.agents/workflows/new-api-endpoint.md`，将新增端点流程改为选择 route 模块、必要时添加 service、同步权限矩阵、前端 API/types。
- [ ] 6.5 更新 README/README.en 中后端架构描述，保留 `app.py` 作为兼容入口的说明。
- [ ] 6.6 确认文档中不再把 `app.py` 描述为承载全部后端逻辑的单文件实现。
- [ ] 6.7 在后端文档中记录“重复 owner 检查暂时保留，后续新需求中再统一优化”的代办事项。

## 7. 回归验收

- [ ] 7.1 对比重构前后 route map，确认既有 HTTP 路径和方法完整保留。
- [ ] 7.2 运行 pytest 后端测试，覆盖认证状态、模型图库、照片图库、任务状态、设置读取、静态文件、导出关键路径和 app import 不启动 worker 的行为。
- [ ] 7.3 运行安全 pytest，确认敏感文件、路径穿越、远程 owner-only、远程生成条件和转发头场景均符合规格。
- [ ] 7.4 运行前端构建或类型检查，确认后端契约未迫使 `frontend/src/api/*` 和类型定义变更。
- [ ] 7.5 手动启动 `python app.py` 或项目启动脚本，确认启动日志、HTTPS/HTTP、LAN bind、verbose 模式和 Ctrl+C 退出行为正常。
- [ ] 7.6 审查并按可行方式验证 `install.sh` / `install.bat`、`build.sh` / `build.bat`、`run.sh` / `run.bat`、`run_verbose.sh` / `run_verbose.bat`、`release.sh` / `release.bat` 未受后端目录拆分影响。
- [ ] 7.7 审查 Windows portable packaging 相关脚本和 `.github/workflows/release.yml`，确认发布产物会包含 `backend/` 并仍以 `app.py` 作为兼容入口。
- [ ] 7.8 运行 `openspec status --change refactor-backend-architecture`，确认任务状态和 artifact 状态可用于后续归档。
