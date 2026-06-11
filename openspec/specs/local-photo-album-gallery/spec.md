# local-photo-album-gallery Specification

## Purpose
TBD - created by archiving change add-local-photo-album-gallery. Update Purpose after archive.
## Requirements
### Requirement: The system SHALL allow local photo album roots to be configured

The system SHALL allow a local user to configure one or more photo directory roots, and SHALL represent each configured directory as a photo album.

#### Scenario: Add a photo directory from localhost
- **WHEN** a localhost user adds a valid photo directory
- **THEN** the system SHALL persist the directory as a photo album configuration
- **AND** the album SHALL appear in the photo album list without requiring application restart

#### Scenario: Non-local client attempts to modify photo roots
- **WHEN** a non-local client attempts to add, remove, or rescan a photo album root
- **THEN** the system MUST reject the request
- **AND** the system MUST NOT modify the saved photo gallery configuration

#### Scenario: Existing configuration has no photo roots
- **WHEN** the application starts with an existing `config.json` that does not contain photo gallery settings
- **THEN** the system SHALL start normally
- **AND** the photo gallery SHALL show an empty configured-albums state

### Requirement: The system SHALL expose configured directories as albums

The system SHALL list configured photo directories as albums with a display name, cover thumbnail when available, photo count or scan status, and updated timestamp, and SHALL avoid scanning every configured album as a prerequisite for returning the album list.

#### Scenario: Album contains supported images
- **WHEN** a configured directory contains supported image files and indexed album metadata is available
- **THEN** the album SHALL show a cover image derived from an available photo thumbnail
- **AND** the album SHALL expose enough metadata for the UI to show count and freshness information

#### Scenario: Album metadata is cached
- **WHEN** the application requests the configured album list
- **THEN** the system SHALL return album configuration and cached summary metadata without recursively scanning all configured album directories
- **AND** the album list SHALL remain usable even when one large album would take a long time to rescan

#### Scenario: Album cache is missing
- **WHEN** a configured album has no cached summary or media index yet
- **THEN** the album SHALL remain visible in the album list
- **AND** the album SHALL expose a scan status that allows the UI to show that the album needs indexing
- **AND** the album list response SHALL NOT block on scanning all media in that album

#### Scenario: Album is empty
- **WHEN** a configured directory contains no supported images
- **THEN** the album SHALL remain visible
- **AND** the album SHALL show an empty state instead of failing the album list

#### Scenario: Album path is unavailable
- **WHEN** a configured directory cannot be read because the drive, mount, or NAS path is unavailable
- **THEN** that album SHALL show an error status
- **AND** other albums SHALL remain usable

### Requirement: The system MUST handle photo paths safely across Windows, Linux, and macOS

The system MUST normalize and validate all local photo paths so that photo listing, preview, thumbnail, download, and conversion requests cannot access files outside configured album roots.

#### Scenario: Path traversal is attempted through a photo request
- **WHEN** a request attempts to reference a path outside a configured album root
- **THEN** the system MUST reject the request
- **AND** the system MUST NOT return file contents

#### Scenario: Windows paths use different casing or drive letters
- **WHEN** the deployment runs on Windows and a request resolves paths with case differences or cross-drive inputs
- **THEN** the system MUST validate the resolved path using platform-safe path comparison
- **AND** the system MUST NOT crash on cross-drive comparisons

#### Scenario: File names contain spaces or non-ASCII characters
- **WHEN** a configured album contains image files with spaces or non-ASCII characters in their names
- **THEN** the system SHALL list, preview, download, and convert those photos using stable IDs and URLs

### Requirement: The photo grid SHALL browse large albums responsively

The photo gallery UI SHALL keep browsing responsive for large albums by using paginated data loading, cached media indexes, thumbnail assets, stable layout sizing, and bounded incremental rendering.

#### Scenario: Album contains at least 1000 photos
- **WHEN** the user opens an album containing at least 1000 photos and a cached media index exists
- **THEN** the UI SHALL become interactive without waiting for the album directory to be recursively rescanned
- **AND** the photo grid SHALL load the first page from the cached index
- **AND** the photo grid SHALL load additional photos incrementally as the user browses

#### Scenario: Album index is not available
- **WHEN** the user opens an album that has not been indexed yet
- **THEN** the UI SHALL show an indexing or loading state for that album
- **AND** the system SHALL build the album index without blocking unrelated application views

#### Scenario: User scrolls quickly through the photo grid
- **WHEN** the user rapidly scrolls through a large album
- **THEN** visible grid items SHALL show either a thumbnail, loading placeholder, or fallback state
- **AND** the UI SHALL NOT require full-resolution originals for offscreen or list thumbnails
- **AND** loading the next page SHALL NOT trigger a full album directory rescan when a usable cached index exists

#### Scenario: Mobile viewport renders the photo grid
- **WHEN** the photo gallery is viewed on a mobile-width viewport
- **THEN** the grid SHALL avoid horizontal overflow
- **AND** core actions SHALL remain reachable without hover-only interactions
- **AND** the grid SHALL support more than one visible column when the selected density allows it

#### Scenario: User adjusts photo grid density
- **WHEN** the user changes the gallery column density from the grid control
- **THEN** the photo grid SHALL update the displayed column count without reloading the album
- **AND** the control SHALL expose a clear current density label

#### Scenario: Touch user pinches on the photo grid
- **WHEN** a touch user performs a two-finger pinch gesture in the photo gallery
- **THEN** the grid SHALL adjust toward a denser or larger photo layout
- **AND** the interaction SHALL preserve normal scrolling outside the gesture

### Requirement: The photo gallery SHALL provide useful sort modes

The photo gallery SHALL allow users to sort photos by common file properties using localized labels, and SHALL use cached album index data for ordinary sort changes.

#### Scenario: User sorts by time, name, or size
- **WHEN** the user selects a sort mode for modified time, created time, file name, or file size
- **THEN** the photo list request SHALL use the corresponding backend sort key
- **AND** the grid SHALL render photos in the requested order
- **AND** the sort change SHALL NOT trigger a full album directory rescan when a usable cached index exists

#### Scenario: Sort labels are displayed
- **WHEN** sort options are shown in the UI
- **THEN** each option SHALL keep a readable field name
- **AND** ascending or descending direction SHALL be visible through arrows or A-Z/Z-A notation

### Requirement: The system SHALL provide cached thumbnails for photo browsing

The system SHALL use dedicated cached thumbnails for album covers and photo grid items, SHALL regenerate thumbnails when the underlying source image changes, and SHALL keep thumbnail generation bounded so large source images do not make the whole gallery unresponsive.

#### Scenario: Thumbnail exists and source is unchanged
- **WHEN** a photo thumbnail has already been generated for the current source file version
- **THEN** the system SHALL serve the cached thumbnail
- **AND** the system SHALL avoid regenerating it for the same request

#### Scenario: Thumbnail is missing
- **WHEN** a visible photo or album cover needs a thumbnail that is missing
- **THEN** the system SHALL generate a bounded thumbnail on demand
- **AND** the system SHALL keep the rest of the gallery responsive
- **AND** concurrent thumbnail generation SHALL be limited so multiple large source images do not exhaust CPU, memory, or disk IO

#### Scenario: Source image changes
- **WHEN** a source image has a different modification time or size from the cached metadata
- **THEN** the system SHALL treat the previous thumbnail as stale
- **AND** a fresh thumbnail SHALL be generated before being served as current

### Requirement: The photo preview SHALL support viewing, downloading, and conversion

The photo preview SHALL allow the user to inspect a photo, download the original image, navigate between photos in the current album context, and convert the photo to a 3D model.

#### Scenario: User opens a photo
- **WHEN** the user opens a photo from the masonry grid
- **THEN** the preview SHALL display the photo using the original image URL
- **AND** the preview SHALL NOT upscale or reuse the grid thumbnail as the primary preview image
- **AND** the preview SHALL provide controls to close, download, and convert the photo to 3D

#### Scenario: Original image has a non-ASCII filename
- **WHEN** the user opens or downloads a photo whose filename contains spaces or non-ASCII characters
- **THEN** the system SHALL return the original image with browser-compatible response headers
- **AND** the preview SHALL render the image instead of an empty frame

#### Scenario: User downloads a photo
- **WHEN** the user chooses download from the photo preview
- **THEN** the system SHALL return the original photo as an attachment
- **AND** the downloaded file name SHALL be safe and recognizable

#### Scenario: User converts from preview
- **WHEN** the user chooses convert to 3D from the photo preview
- **THEN** the system SHALL create a generation task from that photo
- **AND** the existing task queue SHALL show the new task

### Requirement: The photo gallery SHALL support multi-select conversion to 3D

The photo gallery SHALL allow users to select multiple photos from the current album or visible photo set and submit them as a batch to the existing 3D generation queue.

#### Scenario: User selects multiple photos
- **WHEN** the user enters selection mode and selects multiple photo cards
- **THEN** the UI SHALL show the selected count
- **AND** the UI SHALL provide a batch convert-to-3D action

#### Scenario: User submits batch conversion
- **WHEN** the user submits selected photos for conversion
- **THEN** the backend SHALL validate every requested photo ID against configured album roots
- **AND** valid photos SHALL be copied or staged into the existing input workflow
- **AND** generation tasks SHALL be created using the existing task queue lifecycle

#### Scenario: Some selected photos are no longer available
- **WHEN** a batch conversion includes photos that were deleted or became unavailable
- **THEN** the response SHALL report the failed photo IDs or count
- **AND** successfully queued photos SHALL still be returned as created tasks

### Requirement: The photo gallery entry SHALL be a first-level application entry

The photo gallery SHALL be reachable from a first-level application control near the existing model workflow, rather than only from settings.

#### Scenario: User switches from model gallery to photo gallery
- **WHEN** the user activates the photo gallery entry
- **THEN** the main content area SHALL switch from the 3D viewer workspace to the photo gallery workspace
- **AND** the existing model gallery and current model selection SHALL remain preserved

#### Scenario: User returns to model view
- **WHEN** the user switches back to the model view
- **THEN** the existing 3D viewer behavior SHALL remain available
- **AND** model gallery selection SHALL NOT be cleared solely because the user visited the photo gallery

### Requirement: New photo gallery UI MUST be localized and accessible

The system MUST provide localized text and accessible controls for all new photo gallery user-facing UI.

#### Scenario: Language changes
- **WHEN** the application language switches between supported locales
- **THEN** all photo gallery labels, empty states, errors, tooltips, and actions SHALL render from locale resources

#### Scenario: Keyboard user navigates photo gallery controls
- **WHEN** a keyboard-only user navigates albums, photo cards, selection controls, and preview controls
- **THEN** focus state SHALL be visible
- **AND** each actionable control SHALL expose a clear semantic label

#### Scenario: Photo gallery asks for input or confirmation
- **WHEN** the photo gallery needs a path input, sorting menu, confirmation, or status feedback
- **THEN** the UI SHALL use project-styled custom components
- **AND** the main photo gallery flow SHOULD avoid browser-native `select`, `prompt`, `confirm`, and `alert` controls

### Requirement: The photo gallery SHALL filter media by type
The photo gallery SHALL provide a type filter that lets users browse all media, only photos, or only videos within the current album.

#### Scenario: User selects all media
- **WHEN** the user selects the all-media filter
- **THEN** the grid SHALL show supported photos and videos from the current album
- **AND** the total count and empty state SHALL reflect the all-media result set

#### Scenario: User selects photos only
- **WHEN** the user selects the photos filter
- **THEN** the grid SHALL show only supported image items from the current album
- **AND** existing photo preview, download, selection, and convert-to-3D behavior SHALL remain available

#### Scenario: User selects videos only
- **WHEN** the user selects the videos filter
- **THEN** the grid SHALL show only supported video items from the current album
- **AND** video preview and download behavior SHALL remain available
- **AND** convert-to-3D actions SHALL NOT be offered for video-only selections

#### Scenario: Filter labels are displayed
- **WHEN** the media type filter is shown in the UI
- **THEN** the all, photos, and videos labels SHALL render from locale resources
- **AND** the active filter SHALL be visually and semantically identifiable
- **AND** the type filter SHALL keep a shared segmented background while avoiding mismatched pill count badges
- **AND** each segment SHALL keep consistent height and alignment with adjacent toolbar controls across desktop, tablet, and mobile widths

#### Scenario: Viewport width is between desktop and mobile breakpoints
- **WHEN** the gallery toolbar is shown on a narrow desktop, tablet portrait, or other intermediate width
- **THEN** toolbar groups SHALL wrap or reflow without clipping button text
- **AND** labels SHALL remain horizontally readable instead of stacking one character per line

#### Scenario: Mobile toolbar changes between expanded and compact states
- **WHEN** the gallery toolbar changes between expanded and compact states on a mobile or tablet viewport
- **THEN** the toolbar content SHALL animate or transition without causing the masonry grid below it to jump vertically
- **AND** the reserved layout height SHALL remain stable enough that media cards do not shift as a side effect of the control state change
- **AND** tapping non-button space in the compact toolbar SHALL expand the controls in place without forcing a scroll-to-top action
- **AND** any rebound effect SHALL feel subtle and coordinated rather than causing child controls to bounce independently

#### Scenario: Mobile toolbar uses glass styling
- **WHEN** the gallery toolbar is rendered in mobile or tablet layout
- **THEN** the visible control surface SHALL keep the same Apple-style glass background, blur, border, and shadow language used by the desktop toolbar
- **AND** the outer layout container SHALL NOT use transform, isolation, filter, or transform-related will-change rules that break backdrop sampling for the visible glass surface

#### Scenario: Mobile toolbar shows summary text
- **WHEN** the gallery toolbar is expanded on a mobile or tablet viewport
- **THEN** the album summary, media count, and filter context text SHALL remain readable on the glass surface
- **AND** secondary text SHALL keep a subdued visual hierarchy without becoming too small or too low-contrast
- **AND** the title block and media type filter SHALL be spaced tightly enough to avoid a visually empty gap

### Requirement: Temporary gallery downloads SHALL be cleaned up
The system SHALL avoid unbounded accumulation of temporary ZIP files created for bulk gallery downloads.

#### Scenario: Bulk media download completes normally
- **WHEN** the user downloads selected gallery media as a ZIP archive
- **THEN** the system SHALL serve the archive as a temporary file
- **AND** the archive SHALL include supported photos and videos that are part of the current selection
- **AND** the system SHALL attempt to remove the temporary ZIP when the response closes

#### Scenario: Bulk media download leaves stale temporary ZIP files
- **WHEN** a browser cancellation, interrupted connection, or server restart leaves `photo-gallery-*.zip` files in the gallery cache
- **THEN** the system SHALL clean up expired temporary ZIP files before creating subsequent bulk download archives
- **AND** the cleanup SHALL NOT remove the gallery index, thumbnails, video posters, or unrelated files

### Requirement: The photo gallery SHALL NOT block application startup

The application SHALL complete its authenticated startup path without waiting for local photo album scanning or full photo album metadata loading.

#### Scenario: Authenticated user opens the application in model view
- **WHEN** an authenticated or owner user opens the application and the default model view is active
- **THEN** the application SHALL leave the boot screen without waiting for all configured photo albums to scan
- **AND** model gallery, task queue, settings, and viewer functionality SHALL remain available

#### Scenario: User switches to the photo gallery after startup
- **WHEN** the user switches from the model view to the photo gallery view
- **THEN** the application SHALL load photo album summaries at that time if they are not already loaded
- **AND** the photo gallery SHALL show loading, cached, indexing, or error states without returning the whole application to the boot screen

### Requirement: The system SHALL maintain cache-first album indexes

The system SHALL maintain media indexes that allow album listing, paging, filtering, sorting, preview, download, thumbnail, video poster, and conversion operations to resolve media without using full album scans as the normal read path.

#### Scenario: Cached index serves a page
- **WHEN** a client requests a page of media for an indexed album
- **THEN** the system SHALL read the album media from cached index data
- **AND** the response SHALL include the requested page, next cursor, total count, and media counts
- **AND** the system SHALL NOT recursively scan the album directory as part of that ordinary page request

#### Scenario: Media ID is resolved without a global lookup
- **WHEN** a preview, download, thumbnail, video poster, or conversion request references a media ID
- **THEN** the system SHALL resolve the media ID to its configured album using the album identity encoded in the media ID, without reading a global media-lookup table
- **AND** the system SHALL read only the relevant album index to locate the media's relative path
- **AND** the system MUST still validate that the resolved file is inside the configured album root before returning or copying file contents

#### Scenario: Cached media file is missing
- **WHEN** an encoded media ID resolves to a file that was deleted or moved outside Sharp GUI
- **THEN** the system SHALL return a not-found or unavailable response for that media item
- **AND** the system MUST NOT expose files outside configured album roots

#### Scenario: Cached index uses old global format
- **WHEN** an existing workspace has the legacy global photo gallery index format
- **THEN** the system SHALL derive a catalog summary (counts and cover) from the legacy index without reading media files, so the album list stays usable
- **AND** the system SHALL build each album's media index on demand when the album is first browsed, so existing media can still be listed, previewed, downloaded, and converted
- **AND** the system MAY reuse already-cached image dimensions and video metadata from the legacy index to avoid recomputation, but is not required to preserve them across all albums
- **AND** the system SHALL NOT delete original photos or videos
- **AND** thumbnail or video poster cache entries keyed by the previous media ID format MAY be invalidated and regenerated on demand

#### Scenario: Legacy index is missing or unreadable
- **WHEN** no legacy index exists or the legacy index cannot be parsed
- **THEN** the system SHALL build the album index by scanning the album directory
- **AND** the system SHALL surface an indexing state to the UI while the index is being built

### Requirement: The system SHALL separate scanning from ordinary browsing

The system SHALL distinguish explicit or background album scanning from ordinary album browsing, so users can browse cached data without paying scan cost on every request.

#### Scenario: User explicitly rescans an album
- **WHEN** an owner user requests a rescan for a configured album
- **THEN** the system SHALL scan that album directory and update its cached media index and album summary
- **AND** the updated summary SHALL be reflected in subsequent album list and album page responses

#### Scenario: Ordinary browsing uses stale but valid cache
- **WHEN** a cached album index exists but may be older than the current directory contents
- **THEN** ordinary paging, filtering, and sorting requests SHALL be allowed to return the cached result
- **AND** the system SHALL rely on explicit refresh, background scan, or single-file validation to correct stale data

#### Scenario: Scanning one album is slow
- **WHEN** scanning one large or NAS-backed album takes a long time
- **THEN** other indexed albums SHALL remain browseable
- **AND** application startup and model preview SHALL remain available

#### Scenario: Background scan completes during active browsing
- **WHEN** a background scan or refresh updates an album index while the user is actively paging or scrolling that album
- **THEN** the in-progress browsing session SHALL continue against a stable view of the index
- **AND** the updated index SHALL take effect on the next album entry or explicit refresh rather than reordering or shifting the list the user is currently scrolling

### Requirement: The photo gallery SHALL expose bounded cache management

The photo gallery SHALL provide owner-controlled cache management behavior for generated gallery cache files without deleting user original media.

#### Scenario: Owner inspects gallery cache
- **WHEN** an owner requests gallery cache status
- **THEN** the system SHALL report useful cache information for indexes, thumbnails, video posters, and temporary gallery download files
- **AND** the response SHALL avoid exposing unrestricted filesystem contents

#### Scenario: Owner clears generated gallery cache
- **WHEN** an owner clears generated gallery cache
- **THEN** the system SHALL remove generated index, thumbnail, video poster, or temporary download cache according to the requested scope
- **AND** the system MUST NOT delete original photos or videos from configured album directories
- **AND** subsequent gallery browsing SHALL rebuild missing cache as needed

#### Scenario: Non-owner attempts cache management
- **WHEN** a non-owner client attempts to clear gallery cache or trigger owner-only cache management
- **THEN** the system MUST reject the request
- **AND** the system MUST NOT remove cached files or alter gallery configuration

#### Scenario: User-facing cache controls are shown
- **WHEN** cache status or cache cleanup controls are displayed in the UI
- **THEN** all labels, confirmations, errors, and success messages SHALL render from both Chinese and English locale resources

