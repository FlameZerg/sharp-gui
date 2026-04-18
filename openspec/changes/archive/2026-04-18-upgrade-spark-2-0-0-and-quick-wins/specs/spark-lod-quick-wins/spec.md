## ADDED Requirements

### Requirement: System SHALL provide LoD quick-tuning presets
The viewer SHALL provide at least one balanced default LoD preset and additional quick-tuning presets for performance-first and detail-first rendering.

#### Scenario: Switching LoD preset
- **WHEN** a user selects a different LoD preset
- **THEN** the SparkRenderer LoD-related parameters SHALL update consistently as one profile
- **AND** the new preset SHALL take effect without reloading the page

### Requirement: Settings SHALL use preset-first interaction with manual advanced controls
The settings panel SHALL prioritize quick presets for common usage, and SHALL only expose advanced LoD/RAD/XR controls in manual mode.

#### Scenario: Entering manual mode to tune advanced options
- **WHEN** a user is in preset mode
- **THEN** advanced controls for LoD compare, RAD toggles, and XR update strategy SHALL be hidden
- **AND** switching to manual mode SHALL reveal those advanced controls without leaving the current viewer session

### Requirement: Quick presets MUST avoid forcing RAD-only paths
Quick preset switching MUST NOT require `.rad` assets to exist, and quick presets SHALL remain usable for SPZ/PLY/SPLAT-only projects.

#### Scenario: Selecting detail preset on non-RAD source
- **WHEN** the active model does not provide a matching `.rad` asset
- **THEN** selecting detail preset SHALL still load and render through non-RAD path
- **AND** the viewer SHALL keep advanced RAD controls available only through manual mode

### Requirement: System SHALL support LoD vs non-LoD comparison when both exist
For scenes that keep both LoD and non-LoD representations, the viewer SHALL allow toggling between them for visual and quality comparison.

#### Scenario: Toggling LoD rendering source
- **WHEN** both LoD and non-LoD data are available for a SplatMesh
- **THEN** the user SHALL be able to switch active rendering source between LoD and non-LoD
- **AND** the switch SHALL not require re-importing the model

### Requirement: Quick-win tuning MUST preserve interaction stability
Quick-win LoD parameter adjustments MUST NOT break existing camera control, picking interaction, or base model transform behavior.

#### Scenario: Interaction after tuning
- **WHEN** LoD quick-win settings are applied during an active viewer session
- **THEN** camera reset, orbit, and click-to-focus interactions SHALL remain functional
- **AND** existing model scale/rotation conventions SHALL remain unchanged
