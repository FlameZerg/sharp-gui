## MODIFIED Requirements

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

## ADDED Requirements

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
- **THEN** the system SHALL build per-album indexes and a catalog summary so existing media can still be listed, previewed, downloaded, and converted
- **AND** the system SHALL reuse already-cached image dimensions and video metadata from the legacy index without re-reading media files when the source file is unchanged
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
