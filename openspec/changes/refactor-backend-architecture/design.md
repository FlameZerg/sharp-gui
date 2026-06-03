## Context

Sharp GUI 后端当前以单文件 Flask 应用运行，`app.py` 同时承担入口、配置、路径、LAN 门禁、路由、业务逻辑、任务队列、模型转换、静态文件服务、导出 HTML 和服务启动职责。这个结构在项目早期非常直接，但在本地照片图库、局域网门禁、SPZ 导出、LAN bind 重启等能力加入后，已经出现几个维护压力：

- 业务域彼此交织：照片图库路由中混合相册配置、扫描索引、路径安全、缩略图、ZIP 下载和任务入队。
- 安全边界难审查：`before_request` 中已有集中权限矩阵，但部分路由内部仍重复 owner 判断。
- 共享状态隐式分散：`task_status`、`running_processes`、`photo_index_lock`、workspace 路径常量都在模块全局。
- 启动副作用重：导入 `app.py` 会创建 Flask app、初始化目录、启动后台线程，不利于测试和后续重构。
- 文档已经把 `app.py` 描述为单文件后端，但实际行数和职责已经超出这个模式的舒适范围。

本设计面向一次内部架构重构：外部 API、用户体验和部署方式保持不变，把后端拆成稳定的模块边界。

## Goals / Non-Goals

**Goals:**

- 保留 `python app.py`、`run.sh`、`run.bat` 等现有启动入口兼容。
- 将 Flask app 创建、路由注册、hooks 注册、后台线程启动收敛到 app factory。
- 按业务域拆分 routes，按可复用逻辑拆分 services，让前端 API 模块和后端路由域可以互相对应。
- 将 LAN 门禁权限矩阵、Host/Origin 校验、session token 与 CORS 响应维持为集中式安全层。
- 将 workspace 路径、配置读取、运行时环境变量等基础能力从业务逻辑中剥离。
- 让服务层尽量不直接依赖 Flask `request`、`g`、`jsonify`，提高测试和迁移可控性。
- 正式引入 pytest 作为后端测试框架，补充足够的后端测试覆盖，覆盖权限、路径安全、任务状态、关键 API contract 和高风险纯函数。
- 保证现有一键安装、构建、运行、verbose 运行、发布脚本和 GitHub Release 自动化流程不受后端目录拆分影响。
- 同步更新项目规则与后端开发工作流，避免新 API 继续被要求写进单文件 `app.py`。

**Non-Goals:**

- 不新增或移除用户可见功能。
- 不修改现有 `/api/*`、`/files/*`、`/assets/*` 的 URL、请求参数、响应字段和权限语义。
- 不重构 React 前端组件、Zustand store、i18n 文案或 legacy 单文件前端。
- 不引入数据库、ORM、Celery/RQ、FastAPI、Blueprint 以外的新后端框架模式。
- 不改变 `ml-sharp/` 上游项目，也不修改 legacy `static/lib/` 预打包库。
- 不在本次重构中优化 PLY/SPZ 转换算法或任务队列调度策略。

## Decisions

### Decision 1: 保留 `app.py` 作为薄兼容入口

目标结构：

```text
app.py
backend/
  app_factory.py
  server.py
  runtime.py
  config.py
  paths.py
  security/
  services/
  routes/
```

`app.py` 最终只负责导入 `create_app()`、暴露 `app` 变量并在主进程入口调用 `run_server(app)`。这保留现有脚本、文档和第三方使用方式。

Why:

- 用户和启动脚本已经围绕 `python app.py` 工作，兼容入口能降低发布风险。
- Flask 生态也常见 `from app import app` 的测试和部署方式，保留该契约更稳。
- 分阶段迁移时可以先让 `app.py` 代理新模块，避免一次性翻转全部入口。

Alternatives considered:

- 直接删除 `app.py`，改为 `python -m backend` 或其他模块入口：结构更纯粹，但会破坏现有脚本和用户习惯。
- 使用 `sharp_gui/` 作为 Python 应用包名：更适合未来 Python 包发布或被其他项目 import 复用，但当前仓库已有 `frontend/`，`backend/` 与其更对称，也更便于贡献者快速定位后端代码。
- 继续保留大文件，只在文件内增加分区注释：短期成本低，但无法解决导入副作用、测试困难和职责边界问题。

### Decision 2: 使用 app factory + Blueprint 注册路由

目标路由层：

```text
backend/routes/
  auth.py
  frontend.py
  gallery.py
  photo_gallery.py
  tasks.py
  settings.py
  files.py
  export.py
```

`create_app()` 负责创建 Flask app、写入必要 config、注册安全 hooks、注册蓝图、启动后台 task manager。各 route 模块只处理 HTTP 输入输出和调用 service。

Why:

- Blueprint 可以自然对应现有前端 API 模块：`auth`、`gallery`、`photoGallery`、`tasks`、`settings`。
- app factory 让测试可以构造应用实例，也能避免导入模块立即启动后台线程。
- 路由按域拆分后，新增 API 的工作流可以从“改 `app.py`”变成“选对应 route + service”。

Alternatives considered:

- 每个模块继续直接 import 全局 `app` 并使用 `@app.route`：迁移简单，但仍保留强全局耦合。
- 使用 Flask class-based views：对当前函数式路由帮助有限，反而增加学习和迁移成本。

### Decision 3: 将配置与路径上下文显式化

目标基础层：

```text
backend/config.py       # load_config/save_config/normalize_access_control_config
backend/paths.py        # PathContext: workspace/input/output/thumbnail/photo cache
backend/runtime.py      # BASE_DIR、FRONTEND_MODE、SHARP_VERBOSE、日志配置
```

`PathContext` 从 `config.json` 派生，并写入 `app.config` 供路由兼容使用；服务层优先接收或读取统一上下文，而不是散落读取模块全局常量。

Why:

- workspace 切换、照片缓存、静态文件服务和导出都依赖同一组路径，显式上下文能减少拆分后的不一致。
- 配置读写仍保持文件系统模式，符合项目“无数据库/无 ORM”的红线。
- 未来测试可用临时 workspace 构造上下文，避免污染真实 `inputs/outputs`。

Alternatives considered:

- 所有模块直接从 `app.config` 读取路径：迁移快，但 service 层仍和 Flask 绑定。
- 引入全局 settings 单例：使用方便，但测试和重启时容易出现旧状态残留。

### Decision 4: 安全层保持集中权限矩阵

目标安全层：

```text
backend/security/access_control.py
  ACCESS_PUBLIC / ACCESS_UNLOCKED / ACCESS_OWNER
  get_required_access_level(path, method, access_config)
  is_owner_request(...)
  verify_access_session_token(...)
  build_auth_status(...)

backend/security/hooks.py
  register_security_hooks(app)
```

`get_required_access_level()` 仍是 `/api/*` 与 `/files/*` 访问分级的单一来源。重构允许保留少量路由内 owner 防御检查，但最终以 hook 层授权为准。

Why:

- LAN 门禁是隐私边界，集中矩阵比每个路由自行判断更容易审查。
- 现有 OpenSpec 已明确 Public/Unlocked/Owner/Conditional 语义，本次重构不能改变。
- 安全 hooks 与业务 routes 分离后，新增路由必须显式被矩阵覆盖或落入默认 Unlocked。

Alternatives considered:

- 在每个 Blueprint 上设置装饰器：局部可读性好，但 conditional 规则和默认 `/api/*` 行为会分散。
- 依赖 Flask-Login 或 flask-cors：会引入新依赖和概念，不符合当前轻量本地部署定位。

Follow-up TODO:

- 本次迁移先保留路由内部已有的重复 owner 检查，作为集中 hook 之外的纵深防御。
- 后续新需求或专门清理任务中，可以在 pytest 覆盖稳定后统一梳理重复 owner 检查，决定哪些可以删除、哪些应保留为显式防御。

### Decision 5: 服务层承载业务逻辑，路由层保持薄

目标依赖方向：

```text
routes ─────────▶ services ─────────▶ config / paths / runtime
  │                    │
  └────────▶ security ─┘
```

服务层建议拆分：

```text
backend/services/
  model_gallery.py      # 模型列表、原图、缩略图、删除、下载选择
  photo_gallery.py      # 相册配置、扫描、索引、缩略图、photo id、ZIP 输入准备
  task_queue.py         # TaskManager、worker、状态、取消、清理
  model_convert.py      # ply_to_splat、ply_to_spz
  export_html.py        # Spark 独立 HTML 资源嵌入和响应内容构建
  folder_picker.py      # 跨平台原生文件夹选择
  static_files.py       # /files 白名单路径解析与敏感文件拒绝
```

Why:

- 业务逻辑从 route 中下沉后，后续可以单测服务函数，不必都走 HTTP client。
- 照片图库和模型图库是两个独立业务域，拆开后更容易维护路径安全和缓存策略。
- 导出 HTML、模型转换、文件夹选择属于工具型服务，不应和 API 路由互相夹杂。

Alternatives considered:

- 只拆 routes，不拆 services：文件变短，但复杂度仍留在路由函数中。
- 建立复杂领域对象层：对当前本地文件系统应用过重，容易让重构变成架构工程本身。

### Decision 6: 任务队列由单一 TaskManager 管理

`TaskManager` 负责持有 `queue.Queue`、`task_status`、`task_lock`、`running_processes`，并提供 `enqueue_file()`、`list_tasks()`、`cancel_task()`、`start_workers()` 等接口。worker 调用 `sharp predict` 与 SPZ 自动转换的行为保持不变。

Why:

- 当前任务队列是典型共享可变状态，拆分后最怕出现多个 queue/status 实例。
- 把状态封装到 manager 内，可以明确后台线程启动时机，也方便测试构造不启动 worker 的 app。
- route 层只调用 manager API，避免直接操作锁。

Alternatives considered:

- 继续保留模块全局 `task_queue/task_status`：迁移小，但拆分后生命周期更难理解。
- 引入外部任务队列：对本地部署和便携包过重，且超出本次“行为不变”范围。

### Decision 7: 分阶段迁移而不是一次性大爆破

建议迁移顺序：

1. 建立 `backend/` 目录、app factory、薄 `app.py`，先保持所有路由仍可工作。
2. 抽出 `runtime/config/paths` 和模型转换纯函数。
3. 抽出安全层 hooks 与权限矩阵。
4. 按域迁移 routes，保持 URL 不变。
5. 抽出 photo/model/task/export/folder/static services。
6. 更新文档与新 API 工作流。
7. 补充并运行验证。

Why:

- 每个阶段都可以启动应用并验证关键路径，回归定位更容易。
- 安全和任务队列风险较高，分阶段能避免同时引入多类行为变化。
- 文档最后同步，可以确保它描述的是最终落地结构。

Alternatives considered:

- 一次性移动所有函数：完成速度看似快，但出现权限或线程问题时很难定位。
- 先写完整测试再重构：理想但项目当前没有测试框架，前置成本较高；本次应以高风险 smoke/单元测试优先。

### Decision 8: 本次正式引入 pytest

本次变更正式引入 pytest 作为后端测试框架，并以 `tests/` 目录承载后端测试。测试目标不是追求一开始的机械百分比，而是确保迁移后的高风险边界有稳定覆盖：权限矩阵、静态文件安全、路径归一化、配置迁移、route map、TaskManager 状态和无需真实推理的 API contract。

Why:

- 架构拆分会移动大量代码，如果只依赖手动 smoke，很难保证安全边界和路径边界没有回退。
- app factory 和服务层拆分的收益之一就是让 Flask test client 与纯函数测试变得更自然。
- 后续维护需要一个可持续的测试入口，避免每次新增 API 都回到手动验证。

Alternatives considered:

- 只保留脚本化 smoke：落地快，但对权限和路径边界的断言不足，不利于后续扩展。
- 一次性引入复杂覆盖率门禁：能推动覆盖率，但当前项目没有后端测试基础，过强门禁可能拖慢迁移。先建立关键路径覆盖，后续再视稳定度增加覆盖率阈值。

### Decision 9: 脚本与发布自动化纳入兼容性验收

本次重构不只验证 Flask API，还必须验证现有一键安装、构建、运行、verbose 运行、发布打包和 GitHub Release 自动化仍能找到正确入口与文件布局。

Why:

- Sharp GUI 面向本地部署和 Windows 便携包，用户入口主要是脚本和 Release 包，而不是直接 import Python 模块。
- 后端目录拆分可能影响脚本中对 `app.py`、项目根目录、前端构建产物、证书、config、inputs/outputs、portable packaging 的路径假设。
- GitHub Release 自动化失败会直接影响发布交付，即使本地 API 验证通过也不能视为完整成功。

Alternatives considered:

- 只验证 `python app.py`：覆盖了最小运行入口，但不能证明安装、打包和 CI 发布流程仍正常。
- 等发布前再检查脚本：风险发现太晚，重构阶段就应把脚本路径假设纳入检查。

### Decision 10: app import 不启动后台 worker，服务运行时显式启动

`TaskManager` 在默认 app import 时不启动后台 worker。`create_app()` 默认只创建 Flask app、注册路由、初始化配置和挂载 TaskManager；真正通过 `python app.py` 或项目启动脚本运行服务时，由 `run_server(app)` 或等效运行入口显式调用 `TaskManager.start_workers()`。

建议接口语义：

```text
create_app(start_background_workers=False)
run_server(app)  # 启动 HTTP 服务前确保 worker/cleanup 线程启动一次
```

Why:

- pytest 和工具代码会通过 `from app import app` 或 `create_app()` 导入应用；导入时启动后台线程会造成测试不可控、线程泄漏、重复 worker 和偶发阻塞。
- 当前用户路径是 `python app.py` 与脚本启动，不是外部 WSGI server import 后直接托管；因此运行入口显式启动 worker 更符合项目现状。
- 任务队列是可变共享状态，启动时机必须集中管理，并且 `start_workers()` 应具备幂等保护，防止重复启动。
- 测试可以在不启动真实 worker 的情况下验证路由、权限、任务入队和取消状态；真正的 worker 行为可通过单独单元测试或受控集成验证覆盖。

Alternatives considered:

- import 时自动启动 worker：最接近当前单文件行为，但会让 pytest、route map 检查和 `from app import app` 都带有后台线程副作用。
- `create_app()` 默认启动 worker，测试显式关闭：容易漏传参数，且默认行为对测试和工具代码不友好。
- 完全不在进程内启动 worker，改成外部独立 worker 进程：架构更清晰，但会改变本地一键运行模型，超出本次重构范围。

## Risks / Trade-offs

- [风险] Blueprint 注册遗漏导致某个端点 404 -> 缓解：迁移前后列出所有 route rule，并对照现有端点清单做 diff；至少覆盖 auth、gallery、photo、tasks、settings、files、export。
- [风险] LAN 门禁权限语义被改变 -> 缓解：为 Public/Unlocked/Owner/Conditional 端点建立 pytest 覆盖；重点验证门禁开/关、远程生成开/关、owner-only 拒绝远程。
- [风险] 后台 worker 被重复启动或测试导入时启动 -> 缓解：由 app factory 显式控制 `start_background_workers`，默认运行入口启动，测试可关闭；TaskManager 内部防重复启动。
- [风险] 路径上下文拆分后使用旧 workspace -> 缓解：所有路径从同一个 `PathContext` 派生；workspace 修改仍要求重启，与现有 `/api/settings` 行为一致。
- [风险] `/files/*` 白名单或敏感文件拒绝出现回退 -> 缓解：将静态文件解析服务独立测试，验证模型文件可访问、`config.json/key.pem/app.py` 和路径穿越均 404。
- [风险] 照片图库索引锁拆分后出现竞争或死锁 -> 缓解：photo index 的 lock 与读写函数保留同模块封装，服务接口不向外暴露锁对象。
- [风险] 导出 HTML 涉及多个前端依赖文件路径，拆分后资源定位失败 -> 缓解：保留 `BASE_DIR` 派生策略，验证 SPZ 导出和 PLY 兼容导出都能生成 HTML。
- [风险] 文档和工作流仍要求向 `app.py` 添加路由 -> 缓解：实现完成后同步更新 `.agents/rules/backend-guide.md` 和 `.agents/workflows/new-api-endpoint.md`。
- [风险] pytest 引入后测试环境与普通用户运行环境混淆 -> 缓解：将 pytest 作为开发/验证依赖记录清楚，不让普通一键运行路径强依赖测试工具。
- [风险] 安装、构建、运行、发布脚本仍假设单文件后端布局 -> 缓解：逐个审查脚本和 `.github/workflows/release.yml` 中的路径引用，必要时更新并加入验收清单。
- [取舍] 拆分会短期增加文件数量 -> 缓解：目录按业务域命名，保持模块粒度克制，避免为每个小函数创建文件。

## Migration Plan

1. 迁移前基线：
   - 记录现有 Flask route map。
   - 手动或脚本化验证 `/api/auth/status`、`/api/gallery`、`/api/tasks`、`/api/settings`、`/files/*`、照片图库和导出。
2. 建立新包与入口：
   - 新增 `backend/` 目录与 `create_app()`。
   - 保留 `app.py` 导出 `app` 并在主入口调用服务启动逻辑。
3. 迁移基础层：
   - 移动运行时常量、配置读写、路径派生、日志 tee。
   - 保证目录初始化仍发生在应用创建阶段。
4. 迁移安全层：
   - 将权限矩阵和 hooks 移入 `security/`。
   - 先保持逻辑原样，再跑门禁 pytest 验证，必要时补充手动验证。
5. 迁移服务与路由：
   - 先迁移低耦合的 frontend/files/export/model_convert。
   - 再迁移 gallery/photo_gallery。
   - 最后迁移 task_queue 和 settings/restart。
6. 文档与验证：
   - 更新后端架构规则、新 API 工作流、README 中单文件描述。
   - 运行 pytest 后端测试与前端构建或最小类型检查，确认 API 契约未变。
   - 审查并验证安装、构建、运行、verbose 运行、发布脚本和 GitHub Release workflow 的路径假设。

Rollback:

- 每个阶段应保持小提交或可回退 patch。
- 如果某阶段验证失败，优先回退该阶段迁移，保留已验证的基础拆分。
- `app.py` 兼容入口贯穿整个过程，必要时可以临时将对应 route 重新指回旧逻辑。

Verification points:

- `python app.py` 可启动，HTTP/HTTPS、LAN bind 和 verbose 日志行为保持。
- `from app import app` 或测试创建 app 时不会启动后台 worker；`python app.py` 和启动脚本运行服务时会启动 worker/cleanup 线程且不会重复启动。
- `flask app.url_map` 或等效脚本中现有 route 路径完整存在。
- pytest 可以运行，且覆盖权限矩阵、路径安全、route map、关键 API 和无需真实推理的任务队列逻辑。
- 门禁关闭时读取开放但 owner-only 仍拒绝远程；门禁开启时未认证远程读取被拒绝。
- 任务上传、状态轮询、取消、worker 执行和完成后 SPZ 自动转换保持。
- 照片相册列表、照片分页、缩略图、原图、ZIP 下载和照片转 3D 保持。
- `/files/config.json`、`/files/key.pem`、`/files/app.py` 和路径穿越请求仍不可访问。
- SPZ/Ply 导出 HTML 能下载并包含必要资源。
- `install.*`、`build.*`、`run.*`、`run_verbose.*`、`release.*`、Windows portable packaging 相关脚本和 `.github/workflows/release.yml` 的关键路径检查通过。
