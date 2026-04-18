## ADDED Requirements

### Requirement: Spark dependency MUST resolve to stable npm release
The frontend dependency configuration SHALL resolve `@sparkjsdev/spark` from npm stable releases on the 2.0.x line, and MUST NOT resolve from non-registry Git branch references.

#### Scenario: Dependency source validation after install
- **WHEN** the project dependencies are installed for this change
- **THEN** the resolved Spark package source SHALL be npm registry tarball metadata
- **AND** the resolved Spark version SHALL be within the configured 2.0.x stable semver range

### Requirement: Runtime integration MUST use stable public APIs only
The viewer and XR integration SHALL rely on Spark stable public APIs and MUST NOT depend on legacy internal fields or deprecated stochastic runtime paths.

#### Scenario: Runtime initialization without legacy internals
- **WHEN** viewer and XR hooks initialize Spark in development mode
- **THEN** Spark initialization SHALL complete without accessing legacy internal properties
- **AND** no compatibility shim for deprecated stochastic internals SHALL be required for normal operation

### Requirement: Migration verification MUST provide deterministic checklist
The change SHALL define a deterministic verification checklist covering build success, model loading, LoD behavior, and XR session lifecycle.

#### Scenario: Running migration checklist
- **WHEN** an engineer runs the migration verification checklist
- **THEN** each required verification item SHALL have a clear pass/fail criterion
- **AND** results SHALL be sufficient to compare pre-migration and post-migration behavior
