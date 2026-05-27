# Sharp GUI 介绍视频字幕

这里保存当前介绍视频的字幕素材：一部分是可以自动生成的“视频内字幕精确版”，另一部分是给 ElevenLabs / agent 继续扩展用的旁白素材。

## 版本来源

默认版本不写在命令里，而是由上一级目录的 `video-manifest.json` 管理：

- `currentVersion` 决定默认版本。
- `versions.<版本>.captionSource` 决定读取哪个字幕源 JSON。
- `versions.<版本>.captionOutputDir` 决定生成到哪个目录。
- `versions.<版本>.renderOutput` 决定对应视频的默认输出文件。

需要显式指定版本时，从 `videos/sharp-gui-intro` 运行：

```powershell
npm run captions -- -Version v10
```

## 文件说明

- `sharp-gui-v10-visual-captions.json`
  视频内底部字幕的源数据，也是自动生成 SRT/VTT 的来源。

- `sharp-gui-v10-visual-captions.zh-CN.srt`
  自动生成的视频内字幕精确版 SRT。

- `sharp-gui-v10-visual-captions.zh-CN.vtt`
  自动生成的视频内字幕精确版 WebVTT。

- `sharp-gui-v10-voiceover-script.txt`
  扩展版旁白文案。需要配音时，可以粘贴到 ElevenLabs Studio 的脚本框。

- `sharp-gui-v10-video-script.md`
  扩展版视频脚本，包含画面节奏、旁白时间窗和发音提示。

- `sharp-gui-v10-voiceover.zh-CN.srt`
  扩展版旁白字幕 SRT，对应旁白文案。

- `sharp-gui-v10-voiceover.zh-CN.vtt`
  扩展版旁白字幕 WebVTT。

## 重新生成视频内字幕

在 `videos/sharp-gui-intro` 下运行：

```powershell
npm run captions
```

这个命令只会重新生成视频内字幕精确版：

- `sharp-gui-v10-visual-captions.zh-CN.srt`
- `sharp-gui-v10-visual-captions.zh-CN.vtt`

## ElevenLabs 使用建议

1. 上传 `renders/sharp-gui-intro-v10-hq-1080p.mp4`。
2. 添加旁白，并粘贴 `sharp-gui-v10-voiceover-script.txt`。
3. 如果 Studio 保留段落结构，尽量让每一段成为独立旁白片段。
4. 按 `sharp-gui-v10-video-script.md` 里的时间轴对齐旁白。
5. 如果需要给生成后的旁白外挂字幕，可以使用 `sharp-gui-v10-voiceover.zh-CN.srt`。

自然中文产品片的效果，建议选择低到中等能量、语气克制的成熟声音。技术词发音不理想时，只调整粘贴到 ElevenLabs 的脚本文案发音，不要直接改字幕文件。
