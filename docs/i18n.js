/**
 * Sharp GUI Homepage - Internationalization (i18n)
 *
 * Lightweight i18n system for Chinese/English support:
 * - Auto-detects browser language
 * - Persists preference to localStorage
 * - Supports URL parameter override (?lang=en)
 * - Real-time language switching without page reload
 */

const i18n = {
  zh: {
    // === Meta ===
    "meta.title": "Sharp GUI - 本地化 3D 高斯溅射",
    "meta.description":
      "一个精美的 3D 高斯溅射 (Three.js + Spark) 图形化界面,基于 Apple ml-sharp,本地部署,全屋访问。",

    // === Navbar ===
    "nav.features": "特性",
    "nav.showcase": "演示",
    "nav.architecture": "架构",
    "nav.install": "安装",

    // === Hero Section ===
    "hero.badge": "✨ 自托管 3D 空间相册",
    "hero.title": "你的空间记忆<br>触手可及",
    "hero.subtitle":
      "打破设备界限，一次部署，全屋访问。无需云端上传，在浏览器中即可生成并漫游令人惊叹的 3D 场景。",
    "hero.cta.start": "快速开始",
    "hero.cta.github": "Star on GitHub",

    // === Workflow Section ===
    "workflow.title": "极简工作流",
    "workflow.subtitle": "从照片到 3D 空间，只需三步",
    "workflow.step1.title": "上传图片",
    "workflow.step1.desc": "拖拽上传您的照片或视频素材，支持批量处理",
    "workflow.step2.title": "本地生成",
    "workflow.step2.desc": "基于 Ml-Sharp，本地生成，保护隐私",
    "workflow.step3.title": "即刻漫游",
    "workflow.step3.desc": "在任意设备上通过浏览器沉浸式预览",

    // === Photo Gallery Section ===
    "photoGallery.tag": "本地照片图库",
    "photoGallery.title": "把电脑和 NAS 变成<br>空间照片入口",
    "photoGallery.desc":
      "配置多个本地目录作为相册，用缓存缩略图快速浏览，打开时加载原图，并可把单张或多张照片直接加入 3D 生成队列。",
    "photoGallery.point1": "多目录相册",
    "photoGallery.point2": "可调瀑布流",
    "photoGallery.point3": "原图预览下载",
    "photoGallery.point4": "批量转 3D",

    // === Video Reconstruction Section ===
    "videoRecon.tag": "视频 3DGS 重建",
    "videoRecon.title": "从视频重建<br>可漫游 3D 场景",
    "videoRecon.desc":
      "从本地相册视频或拖拽视频出发，配置质量档和自定义参数，经过抽帧、位姿估计、Gaussian 训练与导出，最终回到现有模型图库中预览和分享。",
    "videoRecon.point1.title": "质量档与自定义参数",
    "videoRecon.point1.desc": "标准、高质量或自定义帧数 / 迭代 / 匹配策略",
    "videoRecon.point2.title": "任务阶段与实时预览",
    "videoRecon.point2.desc": "队列中同步显示进度，训练过程中可打开预览",
    "videoRecon.point3.title": "输出 PLY / SPZ 模型",
    "videoRecon.point3.desc": "结果复用模型图库、缩略图和原视频回看入口",
    "videoRecon.flow1": "选择视频",
    "videoRecon.flow2": "配置参数",
    "videoRecon.flow3": "预览训练",
    "videoRecon.flow4": "查看结果",
    "videoRecon.badge.input": "本地视频",
    "videoRecon.badge.output": ".ply / .spz",

    // === Platform Section ===
    "platform.badge": "🌐 无界互联",
    "platform.title": "一次部署，全屋触手可及",
    "platform.subtitle":
      "打破设备隔阂。在 PC 运行服务，手机、平板通过局域网即可流畅访问。<br>响应式设计，为您呈现一致的优雅体验。",

    // === Features Section ===
    "features.title": "核心特性",
    "features.apple.title": "Apple 风格设计",
    "features.apple.desc": "原生级毛玻璃效果、SF Pro 字体与丝滑的缓动动画。",
    "features.privacy.title": "隐私·无界",
    "features.privacy.desc":
      '数据完全本地化，<span class="text-premium">无限制内容生成</span>，一切由你掌控。',
    "features.performance.title": "高性能渲染",
    "features.performance.desc":
      "基于 Three.js + Spark (WASM 加速)，体积减少 43%，点击聚焦，加载飞快。",
    "features.control.title": "全模态控制",
    "features.control.desc":
      "不仅支持键盘 WASD 漫游，更支持移动端陀螺仪体感操控，身临其境。",
    "features.joystick.title": "移动端虚拟摇杆",
    "features.joystick.desc":
      "触摸屏设备内置虚拟摇杆，实现如PC端键盘一样的漫游体验。",

    // === Share Section ===
    "share.tag": "社交裂变",
    "share.title": "一键导出，<br>让作品自由流动",
    "share.desc":
      "告别繁琐的服务器部署。只需点击导出，即可生成一个独立的 HTML 文件。",
    "share.feature1.title": "零依赖交付",
    "share.feature1.desc": "模型数据与查看器打包为单文件",
    "share.feature2.title": "全平台兼容",
    "share.feature2.desc": "微信、AirDrop 直接发送，双击即看",
    "share.feature3.title": "极度轻量",
    "share.feature3.desc": "自动压缩算法，由 GB 级瘦身至 MB 级",

    // === Showcase Section ===
    "showcase.title": "功能演示",
    "showcase.wasd.title": "WASD 漫游",
    "showcase.wasd.desc": "Shift 加速/微调，精准控制视角",
    "showcase.upload.title": "批量处理队列",
    "showcase.upload.desc": "拖拽上传，并支持批量处理和任务中断",
    "showcase.share.title": "一键导出分享",
    "showcase.share.desc": "生成独立 HTML，支持任何设备查看",

    // === Architecture Section ===
    "arch.badge": "🏗️ 技术架构",
    "arch.title": "简洁而强大",
    "arch.subtitle": "现代化技术栈，为极致体验而生",
    "arch.backend.queue": "异步串行队列",
    "arch.backend.cert": "自签名证书",
    "arch.ai.sharp": "Apple 研究引擎",
    "arch.ai.ply": "PLY/SPZ 格式",
    "arch.metric.compression": "体积压缩",
    "arch.metric.inference": "单图推理",
    "arch.metric.render": "流畅渲染",
    "arch.metric.vr": "VR/AR 支持",

    // === Install Section ===
    "install.title": "🚀 立即开始",
    "install.subtitle": "支持 macOS, Linux 和 Windows (WSL)",
    "install.tab": "Release (推荐)",
    "install.download": "下载最新版本",
    "install.tip.prefix": "想要第一时间获取最新功能？使用 ",
    "install.tip.middle": " 克隆仓库，之后运行 ",
    "install.tip.suffix": " 即可同步最新代码。",
    "install.copy.alert": "命令已复制到剪贴板！",

    // === Footer ===
    "footer.made": "Made with ❤️ by",
    "footer.disclaimer": "Disclaimer: 本项目生成的模型内容由用户自行负责。",

    // === Language Switcher ===
    "lang.switch": "EN",
  },

  en: {
    // === Meta ===
    "meta.title": "Sharp GUI - Local 3D Gaussian Splatting",
    "meta.description":
      "A beautiful 3D Gaussian Splatting GUI based on Apple ml-sharp. Local deployment, access from anywhere.",

    // === Navbar ===
    "nav.features": "Features",
    "nav.showcase": "Showcase",
    "nav.architecture": "Architecture",
    "nav.install": "Install",

    // === Hero Section ===
    "hero.badge": "✨ Self-Hosted 3D Spatial Gallery",
    "hero.title": "Your Spatial Memories<br>At Your Fingertips",
    "hero.subtitle":
      "Break device barriers. Deploy once, access everywhere. Generate and explore stunning 3D scenes right in your browser—no cloud upload needed.",
    "hero.cta.start": "Get Started",
    "hero.cta.github": "Star on GitHub",

    // === Workflow Section ===
    "workflow.title": "Simple Workflow",
    "workflow.subtitle": "From photos to 3D space in just 3 steps",
    "workflow.step1.title": "Upload Images",
    "workflow.step1.desc":
      "Drag and drop your photos or videos, batch processing supported",
    "workflow.step2.title": "Local Generation",
    "workflow.step2.desc": "Powered by Ml-Sharp, fully local, privacy-first",
    "workflow.step3.title": "Explore Now",
    "workflow.step3.desc": "Immersive preview on any device via browser",

    // === Photo Gallery Section ===
    "photoGallery.tag": "Local Photo Gallery",
    "photoGallery.title": "Turn Your PC and NAS<br>Into a Spatial Photo Hub",
    "photoGallery.desc":
      "Configure multiple local folders as albums, browse fast cached thumbnails, open original images, and send one or many photos into the 3D generation queue.",
    "photoGallery.point1": "Multi-folder albums",
    "photoGallery.point2": "Adjustable masonry",
    "photoGallery.point3": "Original preview/download",
    "photoGallery.point4": "Batch 3D conversion",

    // === Video Reconstruction Section ===
    "videoRecon.tag": "Video 3DGS Reconstruction",
    "videoRecon.title": "Video to 3D,<br>ready to explore",
    "videoRecon.desc":
      "Start from an album video or a dropped file, choose a quality preset or custom parameters, then move through frame extraction, pose estimation, Gaussian training, export, and final preview in the existing model gallery.",
    "videoRecon.point1.title": "Presets and custom tuning",
    "videoRecon.point1.desc": "Standard, high quality, or custom frames / iterations / matching",
    "videoRecon.point2.title": "Task stages and live preview",
    "videoRecon.point2.desc": "Track queue progress and open a preview while training runs",
    "videoRecon.point3.title": "PLY / SPZ model output",
    "videoRecon.point3.desc": "Reuse the model gallery, thumbnails, and source-video replay",
    "videoRecon.flow1": "Choose video",
    "videoRecon.flow2": "Tune settings",
    "videoRecon.flow3": "Preview training",
    "videoRecon.flow4": "Open result",
    "videoRecon.badge.input": "Local video",
    "videoRecon.badge.output": ".ply / .spz",

    // === Platform Section ===
    "platform.badge": "🌐 Seamless Access",
    "platform.title": "Deploy Once, Access Everywhere",
    "platform.subtitle":
      "Break device barriers. Run the server on PC, access from phone or tablet via LAN.<br>Responsive design delivers a consistent elegant experience.",

    // === Features Section ===
    "features.title": "Core Features",
    "features.apple.title": "Apple-Style Design",
    "features.apple.desc":
      "Native-level glassmorphism, SF Pro typography, and silky-smooth animations.",
    "features.privacy.title": "Privacy · Unlimited",
    "features.privacy.desc":
      'Completely local data, <span class="text-premium">unrestricted content generation</span>, you\'re in control.',
    "features.performance.title": "High Performance",
    "features.performance.desc":
      "Based on Three.js + Spark (WASM-accelerated), 43% size reduction, click-to-focus, blazing fast.",
    "features.control.title": "Multi-Modal Control",
    "features.control.desc":
      "Not just WASD keyboard navigation, but also mobile gyroscope for immersive control.",
    "features.joystick.title": "Mobile Virtual Joystick",
    "features.joystick.desc":
      "Built-in virtual joystick for touch devices, PC-like navigation experience.",

    // === Share Section ===
    "share.tag": "Share Anywhere",
    "share.title": "One-Click Export,<br>Let Your Work Flow",
    "share.desc":
      "Say goodbye to complex server deployments. Just click export to generate a standalone HTML file.",
    "share.feature1.title": "Zero Dependencies",
    "share.feature1.desc": "Model data and viewer bundled in a single file",
    "share.feature2.title": "Cross-Platform",
    "share.feature2.desc": "Send via WeChat, AirDrop—double-click to view",
    "share.feature3.title": "Ultra Lightweight",
    "share.feature3.desc": "Auto compression from GB to MB level",

    // === Showcase Section ===
    "showcase.title": "Feature Demos",
    "showcase.wasd.title": "WASD Navigation",
    "showcase.wasd.desc": "Shift to speed up/fine-tune, precise camera control",
    "showcase.upload.title": "Batch Processing",
    "showcase.upload.desc":
      "Drag & drop upload, with task queue and cancellation",
    "showcase.share.title": "One-Click Export",
    "showcase.share.desc": "Generate standalone HTML, viewable on any device",

    // === Architecture Section ===
    "arch.badge": "🏗️ Architecture",
    "arch.title": "Simple Yet Powerful",
    "arch.subtitle": "Modern tech stack built for the ultimate experience",
    "arch.backend.queue": "Async Serial Queue",
    "arch.backend.cert": "Self-Signed Cert",
    "arch.ai.sharp": "Apple Research Engine",
    "arch.ai.ply": "PLY/SPZ Format",
    "arch.metric.compression": "Size Reduction",
    "arch.metric.inference": "Single Image",
    "arch.metric.render": "Smooth Render",
    "arch.metric.vr": "VR/AR Support",

    // === Install Section ===
    "install.title": "🚀 Get Started",
    "install.subtitle": "Supports macOS, Linux, and Windows (WSL)",
    "install.tab": "Release (Recommended)",
    "install.download": "Download Latest",
    "install.tip.prefix": "Want the latest features? Use ",
    "install.tip.middle": " to clone, then run ",
    "install.tip.suffix": " to sync the latest code.",
    "install.copy.alert": "Commands copied to clipboard!",

    // === Footer ===
    "footer.made": "Made with ❤️ by",
    "footer.disclaimer":
      "Disclaimer: Users are responsible for the content generated by this project.",

    // === Language Switcher ===
    "lang.switch": "中文",
  },
};

// Current language
let currentLang = "zh";

/**
 * Detect user's preferred language
 * Priority: URL param > localStorage > navigator.language > default (zh)
 */
function detectLanguage() {
  // 1. Check URL parameter
  const urlParams = new URLSearchParams(window.location.search);
  const urlLang = urlParams.get("lang");
  if (urlLang && (urlLang === "en" || urlLang === "zh")) {
    return urlLang;
  }

  // 2. Check localStorage
  const storedLang = localStorage.getItem("sharp-gui-lang");
  if (storedLang && (storedLang === "en" || storedLang === "zh")) {
    return storedLang;
  }

  // 3. Check browser language
  const browserLang = navigator.language || navigator.userLanguage;
  if (browserLang) {
    if (browserLang.startsWith("zh")) {
      return "zh";
    } else {
      return "en";
    }
  }

  // 4. Default to Chinese
  return "zh";
}

/**
 * Get translation by key
 */
function t(key) {
  return i18n[currentLang][key] || i18n["zh"][key] || key;
}

/**
 * Translate all elements with data-i18n attribute
 */
function translatePage() {
  // Update <html lang>
  document.documentElement.lang = currentLang === "zh" ? "zh-CN" : "en";

  // Update page title
  document.title = t("meta.title");

  // Update meta description
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) {
    metaDesc.content = t("meta.description");
  }

  // Translate all elements with data-i18n
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.getAttribute("data-i18n");
    const translation = t(key);

    // Check if translation contains HTML
    if (translation.includes("<br>") || translation.includes("<span")) {
      element.innerHTML = translation;
    } else {
      element.textContent = translation;
    }
  });

  // Translate placeholder attributes
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const key = element.getAttribute("data-i18n-placeholder");
    element.placeholder = t(key);
  });

  // Translate aria-label attributes
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    const key = element.getAttribute("data-i18n-aria");
    element.setAttribute("aria-label", t(key));
  });

  // Update language switch button text
  const langBtn = document.getElementById("lang-switch-btn");
  if (langBtn) {
    langBtn.textContent = t("lang.switch");
  }
}

/**
 * Set language and translate page
 */
function setLanguage(lang) {
  if (lang !== "zh" && lang !== "en") {
    lang = "zh";
  }

  currentLang = lang;
  localStorage.setItem("sharp-gui-lang", lang);
  translatePage();
}

/**
 * Toggle between Chinese and English
 */
function toggleLanguage() {
  const newLang = currentLang === "zh" ? "en" : "zh";
  setLanguage(newLang);
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  currentLang = detectLanguage();
  translatePage();
});

// Export for global access
window.setLanguage = setLanguage;
window.toggleLanguage = toggleLanguage;
window.t = t;
