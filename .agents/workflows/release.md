# 工作流：版本发布

## 发布方式

项目通过 **Git tag 触发 GitHub Actions** 自动构建并发布到 GitHub Releases。

> 📝 **Commit Message 和 Release Note 格式**请参考 Skill：[.agents/skills/commit-and-release/SKILL.md](../skills/commit-and-release/SKILL.md)，其中定义了 Conventional Commits 中文规范和中英双语 Release Note 模板。

---

## 完整流程

### 1. 确认代码就绪

```bash
# 确保在 main 分支，代码已提交
git status
git log --oneline -5
```

### 2. 构建前端

```bash
./build.sh
# 等效于:
# cd frontend && npm install && npm run build
```

验证 `frontend/dist/` 目录已生成。

### 3. 本地测试

```bash
./run.sh
# 访问 https://127.0.0.1:5050 确认功能正常
```

### 4. 创建 Git tag 并推送

```bash
# 正式版
git tag v1.2.0
git push origin v1.2.0

# 预发布版（tag 中包含 `-`）
git tag v1.3.0-beta.1
git push origin v1.3.0-beta.1
```

### 5. GitHub Actions 自动执行

推送 tag 后，`.github/workflows/release.yml` 自动触发：

1. **Checkout 代码**
2. **Setup Node.js 20**
3. **构建前端**：删除平台相关 lockfile 后执行 `npm install` + `npm run build`
4. **创建发布包**：
   - 复制 `app.py`、脚本文件、`tools/`、`templates/`、`static/`、`frontend/`
   - 删除 `node_modules/`、`.vite/`、`src/`（仅保留 `dist/`）
   - 写入 `version.txt`
   - 打包为 `sharp-gui-vX.Y.Z.zip`
5. **创建 GitHub Release**：
   - tag 含 `-` → 自动标记为 Pre-release
   - 自动生成 Release Notes

### 6. 验证

- 检查 [GitHub Releases 页面](https://github.com/lueluelue12138/sharp-gui/releases)
- 确认 zip 文件已上传
- 确认 Pre-release 标记正确

---

## 本地打包（不通过 CI）

```bash
./release.sh v1.2.0
# 输出: sharp-gui-v1.2.0.zip
```

`release.sh` 执行相同的构建和打包流程，但在本地完成。

---

## 版本号规范

| 格式 | 类型 | 示例 |
|------|------|------|
| `vX.Y.Z` | 正式版 | `v1.0.0`, `v1.2.3` |
| `vX.Y.Z-beta.N` | Beta 预发布 | `v1.3.0-beta.1` |
| `vX.Y.Z-rc.N` | Release Candidate | `v2.0.0-rc.1` |

---

## 用户端更新

用户使用更新脚本获取最新版本：

```bash
# 更新到最新正式版
./update.sh

# 更新到最新版本（含预发布）
./update.sh --pre
```

更新脚本调用 `tools/update.py`，从 GitHub Releases 下载最新包并覆盖安装，保留 `inputs/`、`outputs/`、`config.json` 等用户数据。

---

## 发布前检查清单

- [ ] 所有功能已完成并测试
- [ ] 前端构建成功（`./build.sh`）
- [ ] 本地运行正常（`./run.sh`）
- [ ] README 更新（如有新功能）
- [ ] i18n 文件完整（en.json 和 zh.json key 一致）
- [ ] 无 TypeScript 编译错误
- [ ] 无 ESLint 错误
- [ ] Git 工作区干净
