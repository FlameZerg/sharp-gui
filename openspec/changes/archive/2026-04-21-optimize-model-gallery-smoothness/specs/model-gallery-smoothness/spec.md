## ADDED Requirements

### Requirement: Large galleries remain responsive to browse
The system SHALL keep the sidebar model gallery interactive when the gallery contains at least 200 items, and SHALL allow users to continue browsing deeper items without waiting for every offscreen row and thumbnail to be realized up front.

#### Scenario: Initial open with a large gallery
- **WHEN** the user opens the sidebar while the gallery contains at least 200 model entries
- **THEN** the gallery SHALL become scrollable and selectable without requiring all offscreen rows to finish rendering first

#### Scenario: User scrolls deep into a large gallery
- **WHEN** the user rapidly scrolls from the top of a large gallery toward later entries
- **THEN** rows entering the viewport SHALL continue appearing as needed without the sidebar freezing or becoming non-responsive

### Requirement: Gallery browsing context is preserved during refresh and layout-only changes
The system SHALL preserve the user's current gallery browsing context when gallery data is refreshed or when sidebar layout state changes without changing the underlying gallery contents.

#### Scenario: Task completion refreshes the gallery mid-scroll
- **WHEN** the user is browsing the middle of the gallery and a completed task inserts or updates items
- **THEN** the gallery SHALL preserve the user's current viewport anchor instead of resetting the scroll position to the top

#### Scenario: Sidebar visibility changes without gallery content changes
- **WHEN** the user collapses and re-expands the sidebar, or closes and reopens the sidebar on mobile, while gallery contents are unchanged
- **THEN** the gallery SHALL restore the same logical browsing position and visible context

#### Scenario: Unrelated UI state changes occur
- **WHEN** the user changes non-gallery UI state such as opening settings or toggling viewer-only controls while gallery contents remain unchanged
- **THEN** the currently visible gallery rows SHALL remain visually stable and SHALL NOT lose their current thumbnail state

### Requirement: Visible rows always present a stable thumbnail state
The system SHALL present a deterministic visual state for the thumbnail area of every visible gallery row, limited to a loaded thumbnail, a loading placeholder, or an error/fallback placeholder.

#### Scenario: Fast scrolling through thumbnail-heavy content
- **WHEN** the user scrolls quickly through the gallery
- **THEN** each row entering the viewport SHALL show either a thumbnail or a placeholder state, and SHALL NOT present a blank gap where the thumbnail region disappears

#### Scenario: Thumbnail is still loading
- **WHEN** a visible row's thumbnail asset has not completed loading yet
- **THEN** the row SHALL keep a stable placeholder state until the thumbnail is ready

#### Scenario: Row re-enters the viewport
- **WHEN** a row that was already viewed re-enters the viewport during the same browsing session
- **THEN** the row SHALL restore its thumbnail presentation without a visible reset to an empty thumbnail region if the asset is already available

### Requirement: List rows prefer dedicated thumbnail assets
The system MUST use dedicated thumbnail assets for gallery rows when available, and MUST NOT use full-resolution original images as the default row preview path.

#### Scenario: Dedicated thumbnail asset exists
- **WHEN** the gallery item has a valid thumbnail asset
- **THEN** the row SHALL request and render that thumbnail asset as its preview image

#### Scenario: Dedicated thumbnail asset is missing or invalid
- **WHEN** the gallery item has no usable thumbnail asset
- **THEN** the row SHALL render a stable fallback state and the gallery SHALL remain scrollable and selectable without requesting the full-resolution original image as the default row preview

### Requirement: Active selection remains consistent across gallery updates
The system SHALL preserve the active model selection across gallery refreshes whenever the selected model still exists after the refresh.

#### Scenario: Selected model is still present after refresh
- **WHEN** the gallery refreshes and the currently selected model entry still exists
- **THEN** the same model entry SHALL remain selected after the refresh completes

#### Scenario: Selected model was removed
- **WHEN** the gallery refreshes and the currently selected model entry no longer exists
- **THEN** the system SHALL clear the stale active state without leaving an invalid selected row in the gallery

### Requirement: New gallery states are localized
The system MUST provide localized user-visible text for any new gallery loading, fallback, or error states introduced by this capability.

#### Scenario: Language changes after gallery UI is available
- **WHEN** the application language switches between supported locales
- **THEN** all new gallery loading, placeholder, and error messages introduced by this capability SHALL render from locale resources for the selected language
