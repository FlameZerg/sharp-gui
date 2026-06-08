## MODIFIED Requirements

### Requirement: The system SHALL expose configured directories as albums

The system SHALL list configured photo directories as albums with a display name, cover thumbnail when available, media count or scan status, and updated timestamp.

#### Scenario: Album contains supported images
- **WHEN** a configured directory contains supported image files
- **THEN** the album SHALL show a cover image derived from an available photo thumbnail
- **AND** the album SHALL expose enough metadata for the UI to show count and freshness information

#### Scenario: Album contains supported videos
- **WHEN** a configured directory contains supported video files
- **THEN** the album SHALL include those videos in its media count
- **AND** the album SHALL be able to use a video poster as its cover when appropriate

#### Scenario: Album is empty
- **WHEN** a configured directory contains no supported media files
- **THEN** the album SHALL remain visible
- **AND** the album SHALL show an empty state instead of failing the album list

#### Scenario: Album path is unavailable
- **WHEN** a configured directory cannot be read because the drive, mount, or NAS path is unavailable
- **THEN** that album SHALL show an error status
- **AND** other albums SHALL remain usable

#### Scenario: Album is removed from configuration
- **WHEN** a configured album is deleted from Sharp GUI
- **THEN** the system SHALL remove that album from the runtime configuration
- **AND** the system SHALL remove media index entries for that album
- **AND** cached thumbnails or video posters that belong to that album's media IDs SHALL be removed
- **AND** original files inside the configured album directory SHALL NOT be deleted

### Requirement: The photo grid SHALL browse large albums responsively

The photo gallery UI SHALL keep browsing responsive for large mixed-media albums by using paginated data loading, thumbnail or poster assets, stable layout sizing, and windowed or otherwise bounded rendering.

#### Scenario: Album contains at least 1000 media items
- **WHEN** the user opens an album containing at least 1000 supported photos or videos
- **THEN** the UI SHALL become interactive without waiting for all media items to be fetched, decoded, probed, or rendered
- **AND** the grid SHALL load additional media items incrementally as the user browses

#### Scenario: User scrolls quickly through the photo grid
- **WHEN** the user rapidly scrolls through a large album
- **THEN** visible grid items SHALL show either a thumbnail, poster, loading placeholder, or fallback state
- **AND** the UI SHALL NOT require full-resolution originals or full video files for offscreen or list thumbnails

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

The photo gallery SHALL allow users to sort photos and videos by common file properties using localized labels.

#### Scenario: User sorts by time, name, or size
- **WHEN** the user selects a sort mode for modified time, created time, file name, or file size
- **THEN** the media list request SHALL use the corresponding backend sort key
- **AND** the grid SHALL render photos and videos in the requested order

#### Scenario: Sort labels are displayed
- **WHEN** sort options are shown in the UI
- **THEN** each option SHALL keep a readable field name
- **AND** ascending or descending direction SHALL be visible through arrows or A-Z/Z-A notation

## ADDED Requirements

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
