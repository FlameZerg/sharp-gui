## Context

Sharp GUI 通常以「内网部署 + 局域网共享」方式运行：用户在本机启动 Flask 服务，绑定 `0.0.0.0:5050`，同网段设备通过 IP 访问浏览/下载模型与照片。门禁层（`app.py` 内一组 `is_*` 判定 + `enforce_lan_access_control` 前置钩子）已实现 owner/访客/公开三级权限、HMAC 会话 Cookie、登录退避与防 DNS rebinding/CSRF。

但安全审查发现四处实现缺陷，使门禁在默认用法下可被绕过或泄露敏感文件：

1. `serve_files`（`/files/<path:filename>`）以 `BASE_DIR`（程序目录）为默认服务根，且无敏感文件过滤。任意客户端可请求 `/files/config.json`（含 `session_secret`、`password_hash`）、`/files/key.pem`（TLS 私钥）、`/files/app.py`（源码）。门禁关闭时 `/files/*` 直接放行；门禁开启时已解锁访客也能读，从而离线伪造会话令牌（因 `verify_access_session_token` 仅验签名、不绑定客户端）。
2. `app.run(debug=True, host='0.0.0.0')` 固定开启调试，向局域网泄露堆栈并暴露 Werkzeug 交互式调试器（PIN 可被推断 → 潜在 RCE）。
3. `lan_bind_enabled` 被存储、被 Settings API 写入、被 `build_auth_status` 返回给前端，但启动段从未消费它来决定 `host`，是一个误导用户的"假开关"。
4. owner 判定依赖 `request.remote_addr ∈ 本机 IP`。若前置任何本机反向代理（nginx/frp），所有外部请求 `remote_addr` 退化为 `127.0.0.1`，导致全员被判为 owner。

约束：保持无数据库、单 owner + 访问码模型；不破坏既有 HMAC 会话与权限分级契约；遵循 `app.py` 单文件后端的线程安全与现有路由结构；用户可见文案需中英双语同步。

## Goals / Non-Goals

**Goals:**

- 把 `/files/*` 的可服务范围收敛到明确的白名单根目录，使敏感系统文件（`config.json`、`*.pem`、`app.py` 等）在门禁开启或关闭时都无法通过任何静态路由读取。
- 默认以 `debug=False` 运行，消除堆栈泄露与交互式调试器暴露面；保留通过环境变量在本机显式开启 verbose 诊断的能力。
- 让 `lan_bind_enabled` 真正决定监听地址：开启 → `0.0.0.0`（局域网共享），关闭 → `127.0.0.1`（仅本机），并使前端开关语义与实际行为一致。
- 明确并缓解反向代理导致的 owner 误判风险，在 HTTP 模式下对访问码登录给出安全提示。
- 补充门禁安全相关的回归验证项（文件泄露、绑定行为、调试关闭）。

**Non-Goals:**

- 不引入数据库、账户体系或多用户角色。
- 不强制替换 Flask 开发服务器为生产级 WSGI（gunicorn/waitress）——本次以关闭 debug 为底线，是否引入仅作记录。
- 不改动 ml-sharp 引擎、模型生成流程或 legacy `templates/index.html`、`static/lib`。
- 不重写 HMAC 会话或权限分级算法本身。

## Decisions

### 决策 1：`/files/*` 改为白名单根 + 敏感文件拒绝清单

将文件服务从「以 `BASE_DIR` 为默认根」改为「仅允许显式登记的服务根」。保留 `workspace/` 前缀映射到 `WORKSPACE_FOLDER`，其余路径映射到一组受控子目录（如 `outputs/`、`inputs/.thumbnails/`、`static/lib/` 等当前确有被引用的资源），并对解析后的真实路径做 `is_path_inside` 校验；对落在服务根但属于敏感类型（`config.json`、`*.pem`、`*.key`、`app.py`、点文件中的密钥缓存等）的请求显式拒绝（404，不区分"不存在"与"被禁"以避免信息泄露）。

**Why**：根因是服务根过宽。收敛根目录从结构上消除整类泄露，比逐个打补丁更稳。`config.json` 与证书本就不在 `outputs/`、`static/lib` 等内容目录下，收敛后天然不可达；拒绝清单作为纵深防御的第二层。

**Alternatives considered**：
- 仅加扩展名黑名单（保留 `BASE_DIR` 为根）：黑名单易遗漏（如未来新增的密钥文件），不如白名单根稳健，否决。
- 把 `config.json`/证书物理移出程序目录：可作为额外加固，但会牵动启动脚本与发布打包路径，本次以"不可服务"为主，物理迁移列为可选 open question。

### 决策 2：默认 `debug=False`，调试经环境变量显式开启且仅本机意义

启动段改为根据环境变量（如复用 `SHARP_VERBOSE`/新增 `SHARP_DEBUG`）决定 `debug`，默认 `False`。verbose 日志仍可用于排障，但不再向 HTTP 响应注入堆栈/调试器。

**Why**：`debug=True` 对外网/局域网暴露是公认高危项（堆栈泄露 + 调试器 RCE）。默认关闭符合"安全默认值"。

**Alternatives considered**：
- 直接引入 waitress/gunicorn：更彻底，但增加依赖与跨平台启动复杂度（Windows 便携包），超出本次范围，记录在 Non-Goals。
- 保留 `debug=True` 仅在 `127.0.0.1` 绑定时：逻辑复杂且仍有误用风险，否决。

### 决策 3：`lan_bind_enabled` 驱动 `host` 绑定

启动段读取 `access_control.lan_bind_enabled`：`True` → `host='0.0.0.0'`；`False` → `host='127.0.0.1'`。环境变量（如 `SHARP_LAN_IP`/新增 `SHARP_BIND_HOST`）可覆盖以兼容现有脚本。前端开关文案需如实描述"关闭后仅本机可访问，需重启生效"。

实现注记（事后补充）：`/api/restart` 使用 `os.execv` 实现进程级重启以读取新 `host` 配置。但发现 Werkzeug reloader（`use_reloader=True`）开启时，父进程会通过 `WERKZEUG_SERVER_FD` 把旧地址的 socket 传给子进程，execv 后新映像继承该 socket 导致重新 bind 时 `Address already in use`，绑定"假切换"。最终实现：`use_reloader=False`（默认）+ restart 前调用 `os.closerange` 关闭所有继承 FD，保证 execv 后 socket 被释放并以新地址干净重新绑定。`SHARP_DEBUG=1` 时 reloader 随调试器一同开启，仅供本机开发排障。

**Why**：消除"假开关"带来的错误安全预期；提供一个真正只监听本机的安全姿态，配合门禁关闭场景。

**Alternatives considered**：
- 仅靠门禁不收窄绑定：用户明确表达"只想本机用"时，最小攻击面应是不监听外网口，否决"只做应用层"的方案。
- 运行时热切换绑定：Werkzeug 不支持不重启换绑定地址，故采用"改配置 + 提示重启"，与现有 workspace 变更一致。

### 决策 4：反向代理 owner 误判的防护策略

owner 判定继续基于真实 `remote_addr` 且不信任 `X-Forwarded-For` 等头（保持现状正确部分）。新增：在文档与启动诊断中明确"若在本机前置反向代理，所有请求会被判为 owner"的风险；提供配置项/环境变量让用户在反代场景下关闭 `allow_localhost_bypass`（需先设访问码，现有约束已具备），从而强制所有访问走访问码。

**Why**：自动识别反代不可靠（无法区分"真本机"与"本机代理转发"）。把决定权交给用户并以显著提示 + 可操作开关来缓解，比错误地信任某些头更安全。

**Alternatives considered**：
- 引入 `ProxyFix` 信任代理头：会重新打开伪造转发头绕过 owner 的风险，与既有安全目标冲突，否决。
- 默认关闭 localhost bypass：破坏"本机开箱即用免登录"的核心体验，否决。

### 决策 5：HTTP 模式登录安全提示

无 TLS 证书（HTTP）时，访问码与 Cookie 明文传输。决定在 owner 设置门禁/前端登录路径上，于 HTTP 模式给出明确的本地化提示，建议生成证书启用 HTTPS。

**Why**：在不强制 HTTPS（影响开箱即用）与安全告知之间取平衡，让用户知情决策。

**Alternatives considered**：
- 强制 HTTPS：证书生成对部分用户有门槛，且会破坏纯本机/无传感器场景的简易性，否决。

## Risks / Trade-offs

- [收敛 `/files/*` 根目录可能误伤现有被引用的合法资源（如导出 HTML 依赖的 data URL 资源、缩略图路径）] → 实施前用 `grep` 全量梳理 `/files/` 与 `get_relative_files_path` 的实际产出路径，把所有合法根登记进白名单，并在回归中逐一验证模型下载、缩略图、原图、导出 HTML、照片资源均可访问。
- [关闭 `debug` 后丢失开发期热重载与堆栈，影响排障效率] → 实施中发现 `use_reloader=True` 会与 `os.execv` 重启冲突（socket 继承导致地址重用失败），因此 reloader 随 `debug` 一并由 `SHARP_DEBUG` 控制，默认关闭。verbose 日志仍可用于排障，`SHARP_DEBUG=1` 本机开发时可恢复热重载。
- [`lan_bind_enabled=False` 后用户忘记需重启，误以为仍可局域网访问或仍不可] → 前端开关明确标注"需重启生效"，保存后给出与 workspace 变更一致的重启提示。
- [反代场景仅靠文档与开关，用户可能忽视仍以 owner 暴露管理操作] → 启动诊断输出中加入"检测到所有请求可能来自代理"的提示路径（如对非典型 `remote_addr` 分布给出告警），并在 README 安全章节置顶说明。
- [拒绝清单/白名单实现若有路径规范化疏漏（大小写、符号链接、Windows 盘符）仍可能逃逸] → 复用既有 `is_path_inside` / `is_real_path_inside`（基于 `realpath` + `commonpath` + `normcase`），并对 `..`、绝对路径、符号链接编写针对性回归。

## Migration Plan

1. 配置兼容：`lan_bind_enabled` 已有默认值（`True`），旧 `config.json` 无需迁移；启动绑定改为消费该值，默认行为（局域网共享）与现状一致，不影响既有用户。
2. 文件服务收敛：先以"白名单根 + 拒绝清单"上线，保持所有现有合法 URL 可用；通过回归校验确认无功能回退。
3. 调试默认关闭：发布即生效，排障改用环境变量。
4. 文档与脚本：同步更新 `README.md` 门禁章节、`run.sh`/`run.bat` 提示与 `.agents/rules/testing.md` 的 smoke checklist。

**回退方案**：所有改动集中在 `app.py` 启动段与 `serve_files`、启动脚本与文档，无数据结构变更；如出现资源不可访问的回退，可临时将白名单根放宽或恢复旧 `serve_files` 逻辑（git revert 单文件即可），不影响用户数据（`inputs/`、`outputs/`、`config.json` 不变）。

**验证点**：
- 局域网设备 `curl /files/config.json`、`/files/key.pem`、`/files/app.py` 均返回 404/拒绝。
- 模型下载、缩略图、原图、导出 HTML、照片缩略图/原图/打包下载在门禁开/关两种状态下均正常。
- 触发后端异常时响应不含堆栈；`/console`（调试器）不可达。
- `lan_bind_enabled=False` 重启后，仅 `127.0.0.1` 可连，局域网 IP 拒绝连接。

## Open Questions

- 是否在本次一并把 `config.json` 与 TLS 证书物理迁移出 `BASE_DIR`（更强加固，但牵动发布打包与脚本）？已决定：本次以"不可服务"为底线，物理迁移留作后续增量。
- 是否需要为反代场景提供自动告警阈值？已决定：仅以文档 + 手动开关（`allow_localhost_bypass`）为准，避免误报。
