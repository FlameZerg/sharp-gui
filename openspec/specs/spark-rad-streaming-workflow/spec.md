# spark-rad-streaming-workflow Specification

## Purpose
TBD - created by archiving change upgrade-spark-2-0-0-and-quick-wins. Update Purpose after archive.
## Requirements
### Requirement: Viewer SHALL support optional RAD paged loading path
The loading pipeline SHALL support an optional `.rad` input path with paged streaming enabled for large-scene usage.

#### Scenario: Loading RAD model with paging
- **WHEN** the selected model source is a `.rad` file and streaming mode is enabled
- **THEN** the viewer SHALL initialize SplatMesh with paged loading behavior
- **AND** scene rendering SHALL begin before all high-detail chunks are fully loaded

### Requirement: Loader MUST provide fallback to existing non-RAD formats
The system MUST keep existing SPZ/PLY/SPLAT loading behavior available as fallback when RAD assets are unavailable or disabled.

#### Scenario: RAD unavailable fallback
- **WHEN** RAD mode is not configured or a RAD source is unavailable
- **THEN** the loader SHALL use the existing non-RAD loading path
- **AND** model viewing SHALL remain functional without RAD-specific prerequisites

### Requirement: Loader SHALL suppress repeated retries for missing derived RAD URLs
When a derived `.rad` URL is confirmed missing (for example, 404), the viewer SHALL avoid repeated retries for the same URL during the current session and SHOULD continue with non-RAD fallback.

#### Scenario: Derived RAD path returns 404
- **WHEN** RAD mode attempts a derived `.rad` path for a non-RAD source and the request returns not found
- **THEN** the viewer SHALL cache the missing RAD URL status for the current session
- **AND** subsequent loads of the same source SHALL prefer non-RAD fallback path without re-triggering repeated missing-RAD requests

### Requirement: RAD usage SHALL remain an explicit user-controlled advanced option
The default quick preset path SHALL NOT force RAD usage, and RAD mode SHALL remain explicitly controlled by advanced/manual settings.

#### Scenario: Using quick presets in default flow
- **WHEN** a user switches between performance, balanced, and detail quick presets
- **THEN** the preset switch SHALL complete without requiring RAD mode to be enabled
- **AND** enabling RAD mode SHALL require explicit action in advanced/manual settings

### Requirement: Workflow SHALL define offline RAD generation contract
The project SHALL document and standardize the offline LoD-to-RAD generation workflow, including command entrypoint, input expectations, and output naming conventions.

#### Scenario: Preparing RAD asset offline
- **WHEN** an engineer prepares a large model for streaming
- **THEN** the documented workflow SHALL produce a valid RAD output set compatible with viewer loading configuration
- **AND** the workflow SHALL state required tool dependencies and command usage clearly

