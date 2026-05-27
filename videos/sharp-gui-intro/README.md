# Sharp GUI 介绍视频

这里是 Sharp GUI 介绍视频的 HyperFrames 源码、字幕素材和一键构建脚本。

## 版本入口

视频版本统一由 `video-manifest.json` 管理：

- `currentVersion` 决定默认版本。
- `versions.<版本>.captionSource` 决定字幕源 JSON。
- `versions.<版本>.captionOutputDir` 决定字幕生成目录。
- `versions.<版本>.renderOutput` 决定默认渲染输出文件。

默认命令会读取 `currentVersion`。需要指定版本时，可以这样运行：

```powershell
npm run captions -- -Version v10
npm run build -- -Version v10
npm run render -- -Version v10
```

## 常用命令

- `npm run captions`
  根据 `video-manifest.json` 中当前版本的字幕源，重新生成视频内字幕的精确中文版 SRT/VTT。

- `npm run build`
  先生成当前版本字幕，再运行 HyperFrames 检查，并渲染当前版本的高码率 1080p 视频。

- `npm run render`
  只调用 `render.ps1` 渲染当前版本视频，不重新生成字幕。

- `npm run check`
  只运行 lint 和 inspect，不渲染视频。

## 字幕素材

`captions/` 是通用字幕目录，不按版本单独建文件夹。版本号保留在具体文件名里，这样后续如果有 v11、v12，也可以按需并存。

- `sharp-gui-v10-visual-captions.json`
  视频内底部字幕的源数据。

- `sharp-gui-v10-visual-captions.zh-CN.srt`
  自动生成的视频内字幕精确版 SRT。

- `sharp-gui-v10-visual-captions.zh-CN.vtt`
  自动生成的视频内字幕精确版 WebVTT。

- `sharp-gui-v10-voiceover-*`
  扩展版旁白脚本和 ElevenLabs 时间轴素材。这部分是 agent 编写的辅助素材，不由字幕生成脚本自动生成。

渲染产物放在 `renders/`，并且会被 Git 忽略。
