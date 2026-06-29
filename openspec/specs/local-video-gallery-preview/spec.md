# local-video-gallery-preview Specification

## Purpose
TBD - created by archiving change add-local-video-gallery-preview. Update Purpose after archive.
## Requirements
### Requirement: The system SHALL discover supported local video files
The system SHALL discover supported video files inside configured local album roots and expose them as stable media items without revealing absolute filesystem paths.

#### Scenario: Album contains supported video files
- **WHEN** a configured album contains supported video files
- **THEN** the album media listing SHALL include those videos with stable IDs, names, timestamps, sizes, media type, preview URL, download URL, and playback URL
- **AND** image files in the same album SHALL remain listed

#### Scenario: Video playback URL is generated
- **WHEN** the system returns a playback URL for a video item
- **THEN** the URL SHALL use a path-style route with the video ID, a short-lived signed token, and a safe filename suffix
- **AND** the URL SHALL NOT expose an absolute filesystem path
- **AND** the token SHALL be scoped to inline playback of that video

#### Scenario: Unsupported video-like files are present
- **WHEN** a configured album contains files whose extension or detected media type is not supported
- **THEN** the system SHALL ignore those files for media browsing
- **AND** the album scan SHALL continue processing other files

#### Scenario: Video path traversal is attempted
- **WHEN** a request attempts to access a video outside a configured album root
- **THEN** the system MUST reject the request
- **AND** the system MUST NOT return file contents or filesystem paths

### Requirement: The system SHALL provide video metadata for browsing
The system SHALL expose enough video metadata for the UI to show a useful card and preview state, while allowing metadata fields to be temporarily unavailable.

#### Scenario: Video metadata is available
- **WHEN** the system can determine a video's duration, dimensions, codecs, or bitrate
- **THEN** the video media item SHALL include those fields in the album listing or item detail response
- **AND** the UI SHALL render duration and dimensions when present

#### Scenario: Video metadata is unavailable
- **WHEN** metadata cannot be read because tooling is missing, the source is unavailable, or probing fails
- **THEN** the system SHALL still list the video item when the file itself is supported
- **AND** unavailable metadata fields SHALL be returned as null or omitted without failing the album listing

#### Scenario: Source video changes
- **WHEN** a source video has a different modification time or size from cached metadata
- **THEN** the system SHALL treat cached video metadata and poster assets as stale
- **AND** subsequent browse or preview requests SHALL use refreshed metadata or a safe fallback state

### Requirement: The system SHALL provide cached video poster images
The system SHALL provide bounded poster images for video cards and album covers, and SHALL cache poster assets by source file version.

#### Scenario: Video poster exists and source is unchanged
- **WHEN** a video poster has already been generated for the current source file version
- **THEN** the system SHALL serve the cached poster
- **AND** the system SHALL avoid regenerating it for the same request

#### Scenario: Video poster is missing
- **WHEN** a visible video card needs a poster and no current poster exists
- **THEN** the system SHALL generate or provide a bounded poster asset when possible
- **AND** the gallery SHALL remain responsive while poster generation is pending or unavailable

#### Scenario: Poster generation fails
- **WHEN** a poster cannot be generated for a video
- **THEN** the UI SHALL show a styled video fallback card
- **AND** the failure SHALL NOT prevent opening, downloading, or listing the video item

### Requirement: The video preview SHALL support common playback controls
The video preview SHALL allow users to play, pause, seek, adjust audio, enter fullscreen, download, close, and navigate between media items in the current album context.

#### Scenario: User opens a playable video
- **WHEN** the user opens a video from the gallery grid
- **THEN** the preview SHALL display the video using its playback URL
- **AND** the preview SHALL provide custom controls for play or pause, seek, elapsed and remaining time, volume or mute, fullscreen, download, close, and previous or next media navigation

#### Scenario: User downloads a video from preview
- **WHEN** the user chooses download from the video preview
- **THEN** the preview SHALL download the original video content
- **AND** the download flow SHALL remain reliable for local HTTPS and Chrome preview-overlay interactions
- **AND** the downloaded file name SHALL be safe and recognizable

#### Scenario: Playback token is used for download
- **WHEN** a request attempts to use a video playback token to download the original video as an attachment
- **THEN** the system MUST NOT treat the playback token as download authorization
- **AND** the download endpoint SHALL still require the normal Unlocked access level

#### Scenario: Playback token expires or sessions are revoked
- **WHEN** a playback token is expired or was issued before access sessions were revoked
- **THEN** the playback route SHALL reject the token
- **AND** the system SHALL NOT return video bytes unless the request otherwise satisfies the required access level

#### Scenario: Video file name contains non-ASCII characters
- **WHEN** a video with spaces, Chinese characters, or other non-ASCII characters is previewed or downloaded
- **THEN** the system SHALL generate HTTP response headers that do not trigger server-side header encoding errors
- **AND** playback, Range requests, and download behavior SHALL remain available when the browser supports the media

#### Scenario: Video cannot be played by the browser
- **WHEN** the browser fails to load or decode the video playback URL
- **THEN** the preview SHALL show a localized playback error state that tells the user to download the video and play it locally
- **AND** the preview SHALL keep download and close controls available
- **AND** the error state SHALL use the same glass visual language as the rest of the preview instead of an unrelated high-contrast callout

### Requirement: The mobile video preview SHALL support fine scrubbing from the video surface
The mobile video preview SHALL support a fine seek interaction where long-pressing and dragging the video surface adjusts playback position without replacing the normal progress-bar seek behavior.

#### Scenario: Mobile user long-presses and drags horizontally on the video surface
- **WHEN** a mobile user long-presses and drags horizontally on the video surface beyond the configured gesture threshold
- **THEN** the preview SHALL enter a fine scrub state
- **AND** the playback position SHALL update by a small, visible time offset relative to the drag distance
- **AND** the preview SHALL show the target time or offset during the gesture

#### Scenario: Mobile user releases a fine scrub gesture
- **WHEN** a mobile user releases the video surface after fine scrubbing
- **THEN** the video SHALL seek to the chosen time
- **AND** playback SHALL resume or remain paused according to the state before the gesture

#### Scenario: Mobile user taps without dragging
- **WHEN** a mobile user taps the video surface without crossing the fine scrub threshold
- **THEN** the preview SHALL toggle play or pause
- **AND** the interaction SHALL NOT accidentally seek the video

#### Scenario: Desktop user interacts with the video surface
- **WHEN** a desktop user clicks or drags on the video surface
- **THEN** the preview SHALL NOT enter video-surface fine scrub mode
- **AND** desktop seek SHALL remain available through the normal progress control

### Requirement: The video preview SHALL be responsive and accessible
The video preview SHALL adapt to desktop and mobile viewports and expose accessible controls for keyboard, pointer, and touch users.

#### Scenario: Desktop user opens video preview
- **WHEN** the video preview opens on a desktop viewport
- **THEN** the video SHALL be centered in an immersive overlay
- **AND** controls SHALL use project-styled glass buttons and remain reachable without covering critical content
- **AND** playback and seek controls SHALL be visually centered in the compact control bar while volume controls remain left-aligned

#### Scenario: Mobile user opens video preview
- **WHEN** the video preview opens on a mobile viewport
- **THEN** controls SHALL fit within the viewport without horizontal overflow
- **AND** touch targets SHALL remain reachable and large enough for touch interaction
- **AND** filename, download, fullscreen, close, and playback controls SHALL NOT overlap at intermediate tablet or narrow desktop widths

#### Scenario: Mobile controls are collapsed
- **WHEN** mobile preview controls are collapsed and the user taps the preview surface outside control buttons
- **THEN** the controls SHALL expand in place without forcing a scroll-to-top action
- **AND** normal scrolling SHALL remain available after the interaction

#### Scenario: Mobile user enters fullscreen for a landscape video
- **WHEN** a mobile user requests fullscreen for a landscape video
- **THEN** the preview SHALL attempt to lock screen orientation to landscape
- **AND** if the browser or device rejects orientation lock, playback SHALL continue with a graceful fallback rather than failing

#### Scenario: Keyboard user controls video preview
- **WHEN** a keyboard-only user navigates the video preview
- **THEN** each actionable control SHALL expose a semantic label
- **AND** focus state SHALL be visible

### Requirement: Video gallery UI MUST be localized
The system MUST provide localized text for all video gallery labels, empty states, errors, metadata, tooltips, and actions in both supported locales.

#### Scenario: Language changes while viewing videos
- **WHEN** the application language switches between supported locales
- **THEN** video gallery filters, playback controls, errors, metadata labels, and download actions SHALL render from locale resources
- **AND** English and Chinese locale resources SHALL contain matching keys for the new user-visible text

### Requirement: 视频图库 SHALL 为受支持视频提供重建入口
本地视频图库和视频预览体验 SHALL 在用户具备生成权限时，为受支持视频提供本地化的“生成 3D”操作，并且该操作 SHALL 与现有媒体图库玻璃态视觉语言一致。

#### Scenario: 用户选择一个视频
- **WHEN** 用户在本地媒体图库选择一个受支持视频
- **THEN** 选择栏 SHALL 提供视频生成 3D 操作
- **AND** 该操作 SHALL 与现有下载、清除选择等操作保持一致的布局和视觉层级

#### Scenario: 用户选择多个视频
- **WHEN** 用户在本地媒体图库选择多个受支持视频
- **THEN** UI SHALL 能表达当前选择包含可重建视频
- **AND** 若首版只支持单视频创建任务，UI SHALL 限制一次只提交一个视频或给出明确提示
- **AND** 系统 MUST NOT 静默忽略未处理的视频

#### Scenario: 用户打开视频预览
- **WHEN** 用户在预览层打开一个受支持本地视频
- **THEN** 预览层 SHALL 提供生成 3D 操作
- **AND** 播放、暂停、seek、音量、下载、全屏、上一项、下一项和关闭控制 SHALL 保持可用

#### Scenario: 用户没有生成权限
- **WHEN** 当前用户可以浏览视频但不能创建生成任务
- **THEN** 视频重建操作 SHALL 按现有生成权限规则禁用或隐藏
- **AND** 用户尝试受限操作时 UI SHALL 显示本地化权限原因

#### Scenario: 选择内容同时包含照片和视频
- **WHEN** 用户同时选择照片和视频
- **THEN** UI SHALL 区分照片转 3D 和视频重建
- **AND** 系统 MUST NOT 将视频提交到照片转换流程
- **AND** 系统 MUST NOT 将照片提交到视频重建流程

#### Scenario: 移动端显示视频重建入口
- **WHEN** 视频重建操作在移动端或触控设备上可见
- **THEN** 该操作 SHALL 无需 hover 即可触达
- **AND** 该操作 MUST NOT 与现有视频播放控制、选择栏按钮或关闭按钮重叠

#### Scenario: 视频重建弹窗打开
- **WHEN** 用户从选择栏或视频预览触发生成 3D
- **THEN** UI SHALL 打开项目风格一致的玻璃态配置弹窗
- **AND** 弹窗 SHALL 展示模式、质量和输出名称
- **AND** 用户 SHALL 可以取消而不影响视频播放或当前选择状态

