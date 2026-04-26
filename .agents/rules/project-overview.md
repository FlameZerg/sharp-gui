# 项目架构总览

## 架构模式

Sharp GUI 采用 **前后端分离 + 双前端模式** 架构：

```
┌─────────────────────────────────────────────────┐
│  浏览器（桌面 / 移动端 / VR）                      │
│  ┌───────────────────┬────────────────────────┐  │
│  │  React 19 前端     │  Three.js + Spark 渲染  │  │
│  │  (Zustand + i18n) │  (WebGL / WebXR)       │  │
│  └────────┬──────────┴─────────┬──────────────┘  │
│           │ fetch              │ .ply/.splat      │
└───────────┼────────────────────┼──────────────────┘
            │ /api/*             │ /files/*
┌───────────┼────────────────────┼──────────────────┐
│  Flask 后端 (app.py)                              │
│  ┌────────┴───────┐  ┌────────┴──────────────┐   │
│  │  REST API 层    │  │  静态文件服务          │   │
│  │  (JSON 响应)    │  │  (inputs/outputs)     │   │
│  └────────┬───────┘  └───────────────────────┘   │
│           │                                       │
│  ┌────────┴───────────────────────────────────┐  │
│  │  任务队列 (queue.Queue + threading.Lock)    │  │
│  │  → subprocess 调用 sharp predict            │  │
│  └────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
            │ subprocess
┌───────────┴───────────────────────────────────────┐
│  Apple ml-sharp (PyTorch + gsplat)                │
│  sharp predict -i <input> -o <output>             │
└───────────────────────────────────────────────────┘
```

## 双前端模式

通过环境变量 `SHARP_FRONTEND_MODE` 切换：

| 模式 | 值 | 说明 |
|------|----|------|
| **React**（默认） | `react` | 现代 SPA，构建产物在 `frontend/dist/` |
| **Legacy** | `legacy` | 单文件版，`templates/index.html`（约 4,555 行） |

启动脚本 `run.sh` 通过 `--legacy` 参数切换。

## 目录结构

```
sharp-gui/
├── app.py                    # Flask 后端 + 任务队列（单文件，约 1,340 行）
├── config.json               # 运行时配置（workspace_folder）
├── install.sh / install.bat  # 一键安装脚本（Python/Git/CUDA/依赖/模型/证书）
├── run.sh / run.bat          # 启动脚本（支持 --legacy）
├── build.sh / build.bat      # 前端构建脚本
├── release.sh / release.bat  # 发布打包脚本
├── update.sh / update.bat    # 自动更新脚本
│
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── api/              #   API 层（client.ts + 功能模块）
│   │   ├── components/       #   组件（common/gallery/layout/viewer 四类）
│   │   │   ├── common/       #     通用 UI：Button, Icons, ImageViewer, Loading, Modal, ParticleBackground
│   │   │   ├── gallery/      #     图库：GalleryItem, GalleryList
│   │   │   ├── layout/       #     布局：Sidebar, ControlsBar, Help, Settings, TaskQueue
│   │   │   └── viewer/       #     查看器：ViewerCanvas, QuickControls, ViewerRevealEffectsRail, GyroIndicator, VirtualJoystick, SpeedTooltip
│   │   ├── constants/        #   Spark / LoD / XR 相关常量
│   │   ├── hooks/            #   自定义 Hooks（useViewer, useXR, useKeyboard, useGyroscope, useJoystick, useGalleryVirtualizer 等）
│   │   ├── i18n/             #   国际化（index.ts + en.json + zh.json）
│   │   ├── store/            #   Zustand 状态管理（useAppStore.ts）
│   │   ├── styles/           #   全局样式（variables.css, animations.css, global.css）
│   │   ├── types/            #   TypeScript 类型定义
│   │   └── utils/            #   工具函数（camera.ts, format.ts, gallery.ts, viewerRevealEffects.ts）
│   ├── vite.config.ts        #   Vite 配置（代理、分包、HTTPS）
│   ├── tsconfig.json         #   TypeScript 配置（strict mode）
│   └── eslint.config.js      #   ESLint flat config
│
├── templates/                # Legacy 单文件前端
│   ├── index.html            #   完整 Legacy SPA（约 4,555 行）
│   └── share_template.html   #   Spark 2.0 独立分享页模板（约 1,333 行）
│
├── static/lib/               # 预打包的 Three.js + GaussianSplats3D（Legacy 版本使用，不可修改）
├── tools/                    # 工具脚本
│   ├── detect_cuda.py        #   CUDA 版本检测
│   ├── download_model.py     #   模型下载（多源 + SHA256 校验）
│   ├── generate_cert.py      #   SSL 证书生成
│   ├── install_torch.py      #   CUDA/CPU PyTorch 安装选择
│   └── update.py             #   自动更新逻辑
│
├── ml-sharp/                 # Apple ML-Sharp 引擎（⚠️ 不可修改）
├── inputs/                   # 用户上传的图片
├── outputs/                  # 生成的 3D 模型（.ply + 自动转换 .spz）
├── openspec/                 # OpenSpec 变更与能力规格
└── docs/                     # GitHub Pages 产品介绍页
```

## 关键依赖版本

### 前端 (package.json)

| 依赖 | 版本 | 说明 |
|------|------|------|
| react / react-dom | ^19.2.0 | UI 框架 |
| zustand | ^5.0.10 | 状态管理 |
| three | ^0.180.0 | 3D 渲染引擎 |
| @mkkellogg/gaussian-splats-3d | - | 已移除，替换为 Spark |
| @sparkjsdev/spark | ^2.0.0 | WASM 加速高斯溅射渲染器（稳定版） |
| i18next | ^25.8.0 | 国际化核心 |
| react-i18next | ^16.5.3 | React 绑定 |
| typescript | ~5.9.3 | 类型系统 |
| vite | ^7.2.4 | 构建工具 |
| eslint | ^9.39.1 | 代码检查 |

### 后端

| 依赖 | 说明 |
|------|------|
| Python 3.10~3.13 | 运行环境 |
| Flask | Web 框架 |
| Pillow (PIL) | 图片处理 / 缩略图 |
| numpy | PLY 数据处理 |
| plyfile | PLY 文件解析 |
| ml-sharp (sharp CLI) | AI 推理引擎 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SHARP_FRONTEND_MODE` | `react` | 前端模式：`react` 或 `legacy` |
| `SHARP_LAN_IP` | 自动检测 | 局域网访问 IP |
| `PYTHONHTTPSVERIFY` | `0`（安装时） | 绕过 SSL 验证（企业/学校网络） |

## 端口与协议

- 默认端口：**5050**
- HTTPS：自动检测项目根目录下 `cert.pem` / `key.pem`
- 开发代理：Vite dev server 将 `/api` 和 `/files` 代理到 `localhost:5050`

## 3D 渲染引擎迁移说明

项目 3D 渲染层已从 `@mkkellogg/gaussian-splats-3d`（已停止维护）迁移至 `@sparkjsdev/spark` 2.0 稳定版：

- **React 前端**（`frontend/`）：使用 Spark（SplatMesh + SparkRenderer + LoD + RAD 可选流式加载），支持 PLY / SPLAT / SPZ / RAD
- **Legacy 前端**（`templates/index.html` + `static/lib/`）：仍使用预打包的 GaussianSplats3D，不修改
- **导出分享**（`share_template.html`）：已迁移到 Spark 2.0，后端将 Three.js / OrbitControls / Spark 作为 data URL 嵌入独立 HTML

## 模型格式与图库

- 后端推理仍生成 `.ply` 原始模型。
- 生成完成后自动转换 `.spz` 紧凑模型；用户设置可在 PLY / SPZ 之间选择默认查看和下载格式。
- 图库响应包含原图 URL、缩略图 URL、PLY/SPZ 大小与版本戳；缺失缩略图会在请求时限量修复。
- React 图库使用虚拟滚动和缩略图加载状态，避免大量模型时滚动卡顿。

## WebXR 支持

React 前端支持 WebXR 双模式：

| 模式 | Session Type | 适用设备 |
|------|-------------|---------|
| **VR** | `immersive-vr` | Quest 3/Pro、Vision Pro |
| **AR Passthrough** | `immersive-ar` | Quest 3/Pro（全彩透视）、Android Chrome |

核心实现在 `hooks/useXR.ts`，采用 Camera Rig 模式 + 高度校准。
