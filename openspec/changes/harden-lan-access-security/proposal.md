## Why

当前局域网门禁的设计骨架（权限分级、HMAC 会话、不信任转发头、防 DNS rebinding）是合格的，但实现中存在若干会让门禁形同虚设的安全缺陷：`/files/*` 路由把整个程序目录暴露给客户端，可被直接读取 `config.json`（含会话签名密钥与密码哈希）、`key.pem`（HTTPS 私钥）和 `app.py` 源码；生产环境固定开启 Flask `debug=True`，向局域网泄露堆栈并暴露交互式调试器（潜在 RCE）；`lan_bind_enabled` 是一个不生效的"假开关"，用户以为收窄了监听范围实际无效；缺少反向代理与 HTTPS 的默认防护与提示。在"内网部署 + 局域网共享"的默认用法下，这些缺陷叠加会导致同网段设备无需任何凭证即可读取本机敏感文件，一旦端口转发到公网风险扩大。

## What Changes

- **收敛 `/files/*` 可服务范围**：将文件服务限制到明确的白名单根目录（如 `outputs/`、`inputs` 缩略图、`static/lib` 等 legacy 资源），拒绝对 `config.json`、`*.pem`、`key.pem`、`cert.pem`、`app.py` 等敏感文件的访问；超出白名单根的路径一律拒绝。
- **关闭生产调试模式**：默认以 `debug=False` 运行，移除向客户端返回完整堆栈和交互式调试器的行为；保留通过环境变量在本机显式开启 verbose/调试的能力。
- **让 `lan_bind_enabled` 真正生效**：根据该配置在启动时决定绑定 `0.0.0.0`（局域网共享）还是仅 `127.0.0.1`（仅本机），并使前端开关与实际监听行为一致。
- **加固敏感文件边界**：将 `config.json` 与 TLS 证书私钥置于不可被任何静态路由服务的位置或显式拒绝清单，确保即使路由配置变化也不泄露密钥。
- **反向代理与 HTTPS 防护提示**：在 owner 判定路径与文档中明确反向代理（`remote_addr` 退化为 `127.0.0.1` 导致全员变 owner）的风险与应对，HTTP 模式下对访问码登录给出明确的安全提示。
- **门禁关闭时仍保护敏感资源**：即使门禁关闭，敏感系统文件（密钥、配置、源码）也 **BREAKING** 地不再通过 `/files/*` 暴露给局域网。

不包含（Out of Scope）：

- 不引入数据库、账户体系或多用户角色（维持无数据库、单 owner + 访问码模型）。
- 不替换 Flask 框架本身；是否引入生产级 WSGI 服务器仅在 design 中评估，本次以关闭 debug 为底线。
- 不改动 3D 推理引擎、模型生成流程或 legacy `templates/index.html` 前端。
- 不重构既有的 HMAC 会话与权限分级契约（仅修复绕过与泄露路径）。

## Capabilities

### New Capabilities
<!-- 无新增能力，本次为对既有能力的安全加固 -->

### Modified Capabilities
- `lan-access-control`: 新增对静态文件服务边界、调试模式暴露面、监听地址绑定与反向代理 owner 误判的行为契约，确保敏感系统文件在门禁开启或关闭时都不被泄露，且 `lan_bind_enabled` 配置与实际监听行为一致。

## Impact

- **后端 `app.py`**：`serve_files`（`/files/<path>` 路由）、`__main__` 启动段（`app.run` 的 `debug` 与 `host` 参数、SSL 上下文）、`is_owner_request` / `is_local_request`（反向代理风险）、`get_required_access_level`（敏感路径判定）、`normalize_access_control_config` 与启动绑定对 `lan_bind_enabled` 的消费。
- **配置与证书**：`config.json`（含 `access_control.session_secret`、`password_hash`）、`cert.pem` / `key.pem` 的存放位置与可服务性。
- **启动脚本**：`run.sh` / `run.bat`（可能新增/传递绑定相关环境变量与提示）。
- **文档**：`README.md` 的「局域网门禁与隐私边界」章节需补充反向代理与 HTTPS 风险说明。
- **测试规范**：`.agents/rules/testing.md` 中的局域网门禁 smoke checklist 需补充文件泄露与绑定行为的验证项。
- **i18n**：若新增用户可见的安全提示文案，需同步维护 `frontend/src/i18n/en.json` 与 `zh.json`。
