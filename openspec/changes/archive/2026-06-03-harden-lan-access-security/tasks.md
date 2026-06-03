## 1. 调研与基线确认

- [x] 1.1 用 grep 全量梳理 `/files/` URL 的所有产出点（`get_relative_files_path`、`serve_files`、模型 `model_url`/`spz_url`、缩略图 `THUMBNAIL_FOLDER`、导出 HTML 引用），列出当前合法服务路径清单，作为白名单根的依据。
- [x] 1.2 确认 `config.json`、`cert.pem`、`key.pem`、`app.py` 相对 `BASE_DIR`/`WORKSPACE_FOLDER` 的位置，明确哪些落在拟定服务根内、需进入拒绝清单。
- [x] 1.3 复核 `is_path_inside` / `is_real_path_inside` 的规范化能力（`..`、绝对路径、符号链接、Windows 盘符、大小写），确认可复用于新校验。

## 2. 收敛 `/files/*` 文件服务边界

- [x] 2.1 在 `app.py` 重写 `serve_files`：以显式白名单服务根（`outputs/`、`inputs/.thumbnails/`、`static/lib/`、`WORKSPACE_FOLDER` 下经 `workspace/` 前缀映射的资源等当前确有引用者）替代默认 `BASE_DIR` 根。
- [x] 2.2 对解析后的真实路径做 `is_path_inside` 校验，路径落在任一服务根之外（含相对穿越、绝对路径、符号链接）一律返回 404。
- [x] 2.3 增加敏感文件拒绝清单（`config.json`、`*.pem`、`*.key`、`app.py`、密钥/索引缓存等），命中即 404，且不区分"不存在"与"被禁"以避免信息泄露。
- [x] 2.4 确认门禁关闭路径不绕过上述校验：在 `enforce_lan_access_control` 放行 `ACCESS_UNLOCKED` 时，`serve_files` 自身的白名单/拒绝逻辑仍然生效。

## 3. 关闭默认调试模式

- [x] 3.1 修改 `app.py` `__main__` 启动段，`app.run` 默认 `debug=False`；新增/复用环境变量（如 `SHARP_DEBUG`）仅供本机显式开启调试。
- [x] 3.2 确认 verbose 日志（`SHARP_VERBOSE`）仍写入日志文件，但不再向 HTTP 响应注入堆栈，且 Werkzeug 调试器端点默认不可达。

## 4. 让 `lan_bind_enabled` 真正生效

- [x] 4.1 启动段读取 `access_control.lan_bind_enabled`，`True` → `host='0.0.0.0'`，`False` → `host='127.0.0.1'`；保留环境变量（如 `SHARP_BIND_HOST`）覆盖以兼容现有脚本。
- [x] 4.2 启动诊断日志按实际绑定地址输出可访问 URL（仅本机时不再打印局域网 IP 可访问的误导信息）。
- [x] 4.3 更新前端门禁设置中 `lan_bind_enabled` 开关文案，明确"关闭后仅本机可访问，需重启生效"，并在保存后给出与 workspace 变更一致的重启提示；同步维护 `en.json` 与 `zh.json`。

## 5. 反向代理与 HTTPS 安全提示

- [x] 5.1 在 `app.py` 启动诊断输出中加入反向代理风险提示路径（本机前置代理会使所有请求被判为 owner），并在文档中说明可通过关闭 `allow_localhost_bypass`（需先设访问码）强制访问码。
- [x] 5.2 在前端访问码登录/门禁设置路径上，于 HTTP（非加密）模式显示本地化"访问码将明文传输，建议启用 HTTPS"提示；同步维护 `en.json` 与 `zh.json`。
- [x] 5.3 确认 owner 判定仍仅基于真实 `remote_addr`，不引入 `ProxyFix` 或信任 `X-Forwarded-For`/`X-Real-IP`/`Forwarded` 等可控头。

## 6. 文档与测试规范同步

- [x] 6.1 更新 `README.md`「局域网门禁与隐私边界」章节：补充 `/files/*` 不再暴露敏感文件、`lan_bind_enabled` 真实语义、反向代理 owner 误判风险与 HTTPS 建议。
- [x] 6.2 更新 `.agents/rules/testing.md` 的局域网门禁 smoke checklist：新增"敏感文件不可下载""仅本机绑定时局域网拒连""异常响应无堆栈"等验证项。

## 7. 回归验证与验收

- [x] 7.1 后端冒烟：门禁开/关两种状态下，`curl /files/config.json`、`/files/key.pem`、`/files/app.py` 均返回 404/拒绝且无敏感内容。
- [x] 7.2 功能回归：模型下载、模型缩略图、原图、导出 HTML、照片缩略图/原图/打包下载在门禁开/关状态下均可正常访问。
- [x] 7.3 调试关闭验证：触发后端异常，确认响应不含堆栈；调试器端点不可达。
- [x] 7.4 绑定验证：`lan_bind_enabled=False` 重启后仅 `127.0.0.1` 可连，局域网 IP 连接被拒；`True` 时局域网可连。
- [x] 7.5 前端验证：`npm run build`（或项目既定构建命令）通过，i18n 中英文案齐全无缺失 key，HTTP 模式安全提示与绑定开关提示按预期渲染。
