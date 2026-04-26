# Sharp GUI

<p align="right">
  <a href="README.md">🇨🇳 中文</a> | <a href="README.en.md">🇺🇸 English</a>
</p>
<div align="center">

**一个精美的 3D 高斯溅射 (Gaussian Splatting) 图形化界面**

<img src="assets/logo.png" alt="Sharp GUI Logo" width="200" />

<br>

**💡 项目背景**

主页：https://lueluelue12138.github.io/sharp-gui/

iOS 26 的"空间照片"带来了令人惊艳的沉浸式体验，但目前仅限于苹果生态。

作为一个 Web 技术爱好者，我开发了 Sharp GUI，旨在通过浏览器打破设备界限。无论你使用 Android、Windows、Mac 还是 VR 设备，都能 **[一键部署](#-快速开始)**，并在局域网内轻松生成并分享你的 3D 空间记忆。这是一个探索性的开源项目，希望能为你带来乐趣。

<br>

![Sharp GUI](https://img.shields.io/badge/Sharp-GUI-0071e3?style=for-the-badge&logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?style=for-the-badge&logo=react&logoColor=black)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-Viewer-000000?style=for-the-badge&logo=threedotjs&logoColor=white)

基于 [Apple ml-sharp](https://github.com/apple/ml-sharp) 打造，无需上传云端，**本地部署，全屋访问**。

[功能特性](#-功能特性) •
[界面预览](#-界面预览) •
[快速开始](#-快速开始) •
[使用指南](#-使用指南) •
[技术架构](#️-技术架构)

</div>

> [!WARNING]
> **本地部署无内容限制** - 模型完全在本地生成，内容由用户自行负责，请遵守法律法规。详见 [免责声明](#%EF%B8%8F-免责声明)。
>
> **No content restrictions for local deployment** - Users are responsible for generated content. See [Disclaimer](#%EF%B8%8F-免责声明).

---

## ✨ 为什么选择 Sharp GUI?

### 🏠 一次部署，全屋访问

无需在每台设备上安装 App。只需在一台电脑上运行 Sharp GUI，局域网内的手机、平板和VR设备均可通过浏览器直接访问，即刻享受 3D 视觉盛宴。HTTPS 支持确保了陀螺仪等传感器功能在任何设备上都能完美调用。

### 🚀 核心功能

| 功能                | 描述                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------------------------------ |
| **📸 空间影像生成** | 上传任意图片，基于 Apple ML-Sharp 自动生成 3D 高斯溅射模型                                             |
| **🖼️ 现代工作流**   | 支持多选/拖拽批量上传、虚拟滚动图库、站内原图查看，后台队列智能调度，实时进度展示                       |
| **👁️ 全能查看器**   | 基于 Three.js + Spark 2.0 的高性能 WASM 加速查看器，支持**鼠标 / 触摸 / 键盘(WASD) / 陀螺仪**全模态控制、点击模型聚焦、快捷姿态调参和 Reveal Effects |
| **📱 移动端优化**   | 完美适配手机/平板，支持陀螺仪体感控制、虚拟摇杆、触摸手势                                              |
| **🥽 VR/AR 预览**   | 支持 WebXR VR 模式 + AR 透视模式 (Passthrough)，Quest 3/Pro 等头显沉浸式体验，手柄摇杆 + AR 触摸手势   |
| **📤 零门槛分享**   | 一键导出为 Spark 版独立 HTML 文件，将你的空间记忆打包发给朋友，双击即看                               |
| **🎮 GPU 加速**     | 自动检测 NVIDIA GPU，智能选择 CUDA 版本 (cu118/cu124)，GPU 推理显著加速                                |
| **🔄 自动更新**     | 一键检测最新版本并更新，支持 pre-release 通道，无需手动下载替换                                        |
| **🔐 安全与隐私**   | 数据完全本地化，支持一键生成 SSL 证书，保障局域网传输安全                                              |
| **🚀 一键部署运行** | 自动配置 Python/Git 环境、下载依赖、预下载模型、生成 HTTPS 证书，开箱即用                              |

### 🎨 Apple 风格界面设计

采用 Apple Human Interface Guidelines 设计理念，精心打造的高级用户体验：

| 设计元素         | 描述                                                    |
| ---------------- | ------------------------------------------------------- |
| **毛玻璃效果**   | 全局 `backdrop-filter: blur()` + 半透明背景，营造层次感 |
| **SF Pro 字体**  | 使用苹果系统字体栈，原生级渲染体验                      |
| **动态粒子背景** | Canvas 绘制的浮动粒子，增添科技感                       |
| **流畅过渡动画** | 所有交互均有精心调校的 cubic-bezier 缓动曲线            |
| **深色模式**     | 自适应系统深色模式偏好                                  |

### 🎯 用户体验优化

- **骨架屏加载** - 图片缩略图加载时显示渐变骨架动画
- **智能轮询** - 有任务时 2s 轮询，空闲时降至 10s，节省资源
- **拖拽上传** - 将图片直接拖入侧边栏即可开始处理
- **拖拽预览** - 将 .ply/.splat/.spz/.rad 模型文件拖入预览区直接加载
- **队列管理** - 待处理任务支持删除/取消
- **原图查看** - 图库内可直接打开上传原图，方便对照 3D 结果
- **虚拟滚动图库** - 大量模型时保持列表滚动顺滑、缩略图稳定
- **加载进度条** - 实时显示模型加载百分比
- **删除动画** - 删除项目时平滑的滑出动画效果
- **可折叠控制栏** - 底部控制栏可收起，最大化预览空间
- **快捷控制面板** - 按模型保存缩放、位置、旋转、交互方向与显示质量
- **Reveal Effects** - Magic / Spread / Unroll / Twister / Rain 五种模型登场效果，可随时重放
- **操作指南面板** - 右上角帮助按钮，清晰的交互提示

### 🔧 高级特性

- **🔒 HTTPS 支持** - 自动生成自签名证书，局域网安全访问
- **📦 文件优化** - 自动生成 SPZ 紧凑模型，通常比 PLY 小 **5-10 倍**，仍可保留 PLY 原始文件
- **🧹 自动清理** - 已完成任务 1 小时后自动清理，防止内存泄漏
- **⚙️ 可配置路径** - 支持自定义工作区文件夹
- **🖥️ 全屏模式** - 沉浸式 3D 预览体验
- **🥽 VR/AR 模式** - 基于 WebXR 的 VR 预览 + AR 透视 (Passthrough) 模式，支持 Quest 3/Pro 等头显沉浸式体验
- **🎯 点击聚焦** - WASM 加速射线检测，点击模型某处即可平滑聚焦，配合 GPU 加速聚焦光环动画
- **🌐 国际化支持** - 中英文双语界面，自动检测浏览器语言，支持手动切换

---

## 📷 界面预览

### 主界面

<p align="center">
  <img src="docs/images/main.png" width="800" alt="主界面">
</p>

<p align="center"><i>侧边栏图库列表 + 3D 模型预览区域 + 底部毛玻璃控制栏</i></p>

### 移动端适配

<p align="center">
  <img src="docs/images/mobile.png" height="400" alt="手机端">&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="docs/images/pad.png" height="400" alt="平板端">
</p>

<p align="center">
  <i>左：手机端抽屉式侧边栏 | 右：平板端分栏布局</i>
</p>

### 功能演示

<!-- <details> -->
<summary><b>🎬 相机移动控制</b></summary>

<p align="center">
  <img src="docs/images/demo-wasd.gif" height="300" alt="WASD键盘控制">&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="docs/images/demo-joystick.gif" height="300" alt="虚拟摇杆">
</p>

<p align="center">
  <i>左：WASD/QE 键盘移动 (Shift精细) | 右：移动端虚拟摇杆</i>
</p>

<!-- </details> -->

<!-- <details> -->
<summary><b>🎬 批量上传 + 队列处理</b></summary>

<p align="center">
  <img src="docs/images/demo-upload.gif" width="600" alt="批量上传演示">
</p>

<p align="center"><i>拖拽多张图片到侧边栏，队列实时更新处理进度</i></p>

<!-- </details> -->

<!-- <details> -->
<summary><b>🎬 陀螺仪体感控制 (移动端)</b></summary>

<p align="center">
  <img src="docs/images/demo-gyro.gif" height="400" alt="陀螺仪演示">
</p>

<p align="center"><i>倾斜手机控制视角，iOS 风格实时指示球反馈</i></p>

<!-- </details> -->

<!-- <details> -->
<summary><b>🎬 一键导出分享</b></summary>

<p align="center">
  <img src="docs/images/demo-share.gif" width="600" alt="导出分享演示">
</p>

<p align="center"><i>点击 Share 导出独立 HTML，双击即可在任何浏览器打开</i></p>

<!-- </details> -->

---

## 🎨 设计亮点

- 🪟 **Glass Morphism** - 毛玻璃效果控制栏，`backdrop-filter: blur(30px)`
- ✨ **动态粒子背景** - Canvas 绘制的浮动科技感粒子
- ✨ **Reveal Effects Rail** - 查看器侧边特效轨道，支持 Magic / Spread / Unroll / Twister / Rain
- 🧭 **快捷姿态面板** - 模型缩放、位置、旋转和交互方向可即时调整
- 🎯 **iOS 风格指示球** - 移动端陀螺仪实时反馈
- 🎬 **流畅动画** - 所有交互均有 `cubic-bezier` 缓动曲线
- 📱 **响应式设计** - 完美适配桌面/平板/手机

---

## 🚀 快速开始

### 系统要求

| 平台                      | 推理       | 视频渲染 | 状态      |
| ------------------------- | ---------- | -------- | --------- |
| **macOS Apple Silicon**   | ✅ MPS     | ❌       | ✅ 已验证 |
| **Windows x86_64**        | ✅ CPU     | ❌       | ✅ 已验证 |
| **Windows x86_64 + NVIDIA** | ✅ CUDA  | ❓       | ✅ 已验证 |
| **Linux x86_64**          | ✅ CPU     | ❌       | ✅ 已验证 |
| **Linux x86_64 + NVIDIA** | ✅ CUDA    | ✅       | ❓ 未验证 |
| **macOS Intel**           | ✅ CPU     | ❌       | ❓ 未验证 |

> 📢 **缺少 GPU 不影响使用！** 3D 模型生成可在纯 CPU 环境下运行，仅视频渲染需要 CUDA。  
> 💡 有 NVIDIA GPU 时，安装脚本会**自动检测并安装 CUDA 版 PyTorch**，无需手动配置。  
> 👉 未验证平台理论上可正常工作，如遇问题欢迎在 [Issues](https://github.com/lueluelue12138/sharp-gui/issues) 反馈。

### 方式一：下载预构建包 (推荐普通用户)

从 [Releases](https://github.com/lueluelue12138/sharp-gui/releases) 页面下载最新版本：

```bash
# 1. 下载并解压
unzip sharp-gui-vX.Y.Z.zip
cd sharp-gui

# 2. 运行安装脚本 (自动配置 Python 环境、下载模型、生成证书)
./install.sh      # Linux/macOS
# 或
install.bat       # Windows

# 3. 启动服务
./run.sh          # Linux/macOS
# 或
run.bat           # Windows
```

> 💡 预构建包已包含编译好的前端，**无需安装 Node.js**，开箱即用。  
> 💡 想尝鲜最新功能？可下载 [Pre-release](https://github.com/lueluelue12138/sharp-gui/releases) 版本（标记为 `Pre-release` 的版本）。

### 方式二：从源码安装 (开发者 / 追求最新功能)

```bash
# 1. 克隆项目
git clone https://github.com/lueluelue12138/sharp-gui.git
cd sharp-gui

# 2. 运行安装脚本 (自动拉取 ml-sharp 并配置环境)
./install.sh      # Linux/macOS
# 或
install.bat       # Windows

# 3. (可选) 如需修改前端，安装 Node.js 18+ 后运行：
./build.sh        # 构建前端
```

> 💡 安装脚本会自动生成 HTTPS 证书，建议使用 HTTPS 模式以获得完整功能。

### 安装脚本做了什么？

安装脚本会自动完成以下步骤，无需手动配置：

- 🐍 **检测/安装 Python** - 自动查找兼容版本 (3.10~3.13)，缺失时自动安装 (Windows)
- 📦 **检测/安装 Git** - 缺失时自动安装 (Windows)
- 🎮 **检测 NVIDIA GPU** - 有 GPU 时自动安装 CUDA 版 PyTorch，智能选择 cu118/cu124
- 🧩 **安装依赖** - 创建虚拟环境，安装 ml-sharp 核心和 GUI 依赖
- 📥 **预下载模型** - 安装阶段即下载推理模型 (~500MB)，避免首次运行等待
- 🔐 **生成 HTTPS 证书** - 自动生成自签名证书，支持局域网安全访问

### 启动服务

```bash
./run.sh          # Linux/macOS (React 版本)
./run.sh --legacy # 使用原始单文件版本
# 或
run.bat           # Windows
```

访问 **https://127.0.0.1:5050 (推荐)** 或 **http://127.0.0.1:5050** 即可使用 🎉

### 更新版本

```bash
# 更新到最新正式版
./update.sh       # Linux/macOS
update.bat        # Windows

# 更新到最新版本 (含预发布)
./update.sh --pre
```

> 💡 更新脚本会自动检测最新 Release 并下载覆盖，保留你的模型和输出文件。

### 卸载

所有依赖均安装在项目内的 `venv/` 虚拟环境中，不会影响系统环境。卸载只需删除项目文件夹：

```bash
# 删除项目 (包含 venv、ml-sharp、模型等)
rm -rf sharp-gui/

# (可选) 清理模型缓存
# Windows: del %USERPROFILE%\.cache\torch\hub\checkpoints\sharp_*.pt
# macOS/Linux: rm ~/.cache/torch/hub/checkpoints/sharp_*.pt
```

---

## 📖 使用指南

### 生成 3D 模型

1. **上传图片** - 点击「Generate New」按钮或直接拖拽图片到侧边栏
2. **等待处理** - 观察队列区域的实时进度（首次运行会下载 ~500MB 模型）
3. **预览模型** - 点击图库中的项目即可查看 3D 效果

### 3D 交互控制

#### 基础操作

| 操作     | 桌面端       | 移动端   |
| -------- | ------------ | -------- |
| 旋转视角 | 鼠标左键拖拽 | 单指滑动 |
| 平移画面 | 鼠标右键拖拽 | 双指平移 |
| 缩放     | 滚轮         | 双指捏合 |
| 精细缩放 | Shift + 滚轮 | -        |
| 锁定焦点 | 点击模型     | 点击模型 |

#### 相机移动

| 控制方式         | 功能描述                             |
| ---------------- | ------------------------------------ |
| **WASD / QE**    | 键盘平移相机（前后左右上下）         |
| **Shift + WASD** | 加速移动模式                         |
| **Alt + WASD**   | 精细移动模式                         |
| **虚拟摇杆**     | 移动端触摸平移（点击 Move 按钮开启） |

#### 特殊模式

| 模式     | 操作                   | 说明                              |
| -------- | ---------------------- | --------------------------------- |
| 快捷控制 | 点击齿轮按钮           | 调整模型缩放、位置、旋转、交互方向和显示质量 |
| 渲染特效 | 点击右侧特效轨道       | 切换或重放 Magic / Spread / Unroll / Twister / Rain |
| 陀螺仪   | 点击「Gyro」按钮       | 倾斜手机控制视角                  |
| 正面视角 | 点击「Front View」按钮 | 限制为正面视角，再次点击自由      |
| 重置视角 | 点击「Reset」按钮      | 恢复初始视角                      |
| 全屏模式 | 点击「Fullscreen」按钮 | 沉浸式预览                        |
| VR 预览  | 点击「VR」按钮         | 进入 VR 模式（需 VR 设备/模拟器） |
| AR 透视  | 点击「AR」按钮         | 进入 AR 模式，现实世界叠加 3D 模型 |
| 重置视角 | 按下「R」键            | 快捷键重置相机到初始位置          |

### 导出分享

点击 **Share** 按钮，生成独立的 HTML 文件：

- 📦 包含完整的 3D 查看器（Three.js + Spark 2.0）
- 🌐 无需服务器，双击即可在浏览器打开
- 📉 默认嵌入 SPZ 紧凑模型；需要兼容旧流程时仍可导出 PLY/Splat 路径
- 🔒 包含免责声明，说明内容责任归属

---

## ⚙️ 配置选项

### 自定义工作目录

可通过界面设置或编辑 `config.json` (首次运行后生成):

```json
{
  "workspace_folder": "/path/to/workspace"
}
```

系统会自动在工作目录下创建：

- `inputs/` - 上传的图片
- `outputs/` - 生成的模型

### 启用 HTTPS (推荐)

启用 HTTPS 后可支持**局域网设备的陀螺仪功能**（浏览器要求安全上下文才能访问传感器 API）。

安装脚本会自动尝试生成证书。如需手动生成：

```bash
python tools/generate_cert.py
```

> 💡 **Windows 用户**: 需要先安装 [Git for Windows](https://git-scm.com/download/win) 或 OpenSSL。

生成成功后重启服务，使用 `https://` 访问：

| 模式      | 本机                   | 局域网            | 陀螺仪    |
| --------- | ---------------------- | ----------------- | --------- |
| **HTTPS** | https://127.0.0.1:5050 | https://[IP]:5050 | ✅ 可用   |
| HTTP      | http://127.0.0.1:5050  | http://[IP]:5050  | ❌ 仅本机 |

首次访问 HTTPS 时浏览器会提示证书警告（因为是自签名证书），选择「继续访问」即可。

---

## 🏗️ 技术架构

### 项目结构

```
sharp-gui/
├── 📄 app.py                 # Flask 后端 + 任务队列系统
├── 📄 install.sh/bat         # 一键安装脚本
├── 📄 run.sh/bat             # 启动脚本 (支持 --legacy 参数)
├── 📄 build.sh/bat           # 前端构建脚本
├── 📄 update.sh/bat          # 自动更新脚本
├── 📄 release.sh/bat         # 发布打包脚本
├── 📁 tools/                 # 工具脚本
│   ├── 📄 generate_cert.py   # SSL 证书生成工具
│   ├── 📄 download_model.py  # 模型下载工具
│   ├── 📄 detect_cuda.py     # CUDA 版本检测
│   └── 📄 update.py          # 自动更新核心逻辑
├── 📁 frontend/              # React 现代前端 (v1.0.0+)
├── 📁 templates/             # 原始单文件前端 (Legacy)
├── 📁 static/lib/            # Three.js + Gaussian Splats 3D（Legacy 旧前端使用）
├── 📁 ml-sharp/              # (安装后) Apple ML-Sharp 核心
├── 📁 inputs/                # 输入图片
└── 📁 outputs/               # 输出模型 (.ply + .spz)
```

### 前端架构 (React)

```
frontend/
├── 📁 src/
│   ├── 📁 api/               # API 客户端 (gallery, tasks, settings)
│   ├── 📁 components/
│   │   ├── 📁 common/        # 通用组件 (Button, Modal, Loading, ImageViewer, ParticleBackground)
│   │   ├── 📁 gallery/       # 图库组件 (GalleryList, GalleryItem)
│   │   ├── 📁 layout/        # 布局组件 (Sidebar, ControlsBar, TaskQueue, Settings)
│   │   └── 📁 viewer/        # 查看器组件 (ViewerCanvas, QuickControls, ViewerRevealEffectsRail, VirtualJoystick, GyroIndicator)
│   ├── 📁 hooks/             # 自定义 Hooks (useViewer, useXR, useGyroscope, useKeyboard, useGalleryVirtualizer)
│   ├── 📁 i18n/              # 国际化 (zh.json, en.json)
│   ├── 📁 store/             # Zustand 状态管理
│   ├── 📁 styles/            # 全局样式 (variables, animations)
│   ├── 📁 types/             # TypeScript 类型定义
│   └── 📁 utils/             # 工具函数
├── 📄 vite.config.ts         # Vite 配置 (代码分割)
└── 📁 dist/                  # 构建产物
```

### 核心技术栈

| 层级         | 技术                                               |
| ------------ | -------------------------------------------------- |
| **前端**     | React 19 + TypeScript + Vite / 原生单文件 (Legacy) |
| **状态管理** | Zustand                                            |
| **国际化**   | i18next + react-i18next                            |
| **样式**     | CSS Modules + Apple Glass Morphism                 |
| **后端**     | Python 3.10+, Flask, 多线程任务队列                |
| **AI 引擎**  | Apple ML-Sharp (PyTorch, gsplat)                   |
| **3D 渲染**  | Three.js + Spark (WASM 加速高斯溅射)               |

### 性能优化

| 优化项         | 说明                                                                             |
| -------------- | -------------------------------------------------------------------------------- |
| **代码分割**   | Vite manualChunks: three.js (~493KB), spark (~487KB), react-vendor (4KB)         |
| **缩略图系统** | 自动生成 200px JPEG 缩略图，节省带宽                                             |
| **智能轮询**   | 有任务时 2s 轮询，空闲时 10s，节省资源                                           |
| **格式转换**   | 生成后自动转换 SPZ 紧凑模型；分享导出默认嵌入 SPZ，历史 PLY 导出路径保留 Splat 兼容 |
| **内存清理**   | 已完成任务 1 小时后自动从内存中移除                                              |
| **进度优化**   | 进度条只允许前进，避免视觉跳变                                                   |

---

## 🛠️ 开发者指南

### 前端开发

```bash
# 安装依赖
cd frontend
npm install

# 开发模式 (热更新)
npm run dev

# 构建生产版本
npm run build
# 或使用项目脚本
./build.sh
```

### 切换前端版本

```bash
./run.sh           # 使用 React 现代版本 (默认)
./run.sh --legacy  # 使用原始单文件版本
```

### 创建发布包

```bash
# 自动构建并打包
./release.sh v1.0.0

# 输出: sharp-gui-v1.0.0.zip (包含预构建前端)
```

---

## 🤝 致谢

- [Apple ML-Sharp](https://github.com/apple/ml-sharp) - 核心 3D 生成模型
- [Spark](https://github.com/nickthetimid/spark) - WASM 加速高斯溅射渲染引擎
- [Gaussian Splats 3D](https://github.com/mkkellogg/GaussianSplats3D) - 原版 Three.js 高斯溅射渲染器（Legacy 版本使用）
- [antimatter15/splat](https://github.com/antimatter15/splat) - Splat 格式转换参考

---

## 🙋 参与贡献

欢迎提交 Issue 和 Pull Request！

- 🐛 **Bug 反馈** - 在 [Issues](https://github.com/lueluelue12138/sharp-gui/issues) 中提交问题
- 💡 **功能建议** - 通过 Issue 讨论新功能想法
- 🔧 **代码贡献** - Fork 项目后提交 PR
- 🖥️ **平台测试** - 如果你在 NVIDIA GPU 或其他未验证环境上测试通过，欢迎反馈！

---

## ⚠️ 免责声明

由于本地部署**生成内容无限制**，本项目生成的 3D 模型由用户使用 AI 工具生成，**模型内容由用户自行负责**，与本开源项目及其开发者无关。

**严禁将本工具用于生成或传播任何违法、侵权或不当内容。**

---

## 📄 许可证

本项目基于 MIT 许可证开源。

请注意：ML-Sharp 模型有单独的 [模型许可证](https://github.com/apple/ml-sharp/blob/main/LICENSE_MODEL)，仅限非商业用途。

---

<div align="center">

**如果觉得有用，请给个 ⭐ Star 支持!**

Made with ❤️ by [lueluelue12138](https://github.com/lueluelue12138)

</div>
