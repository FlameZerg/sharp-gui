# Requirement Coverage Self-Check

## spark-stable-upgrade

### Requirement: npm stable dependency source

- Implemented in: frontend/package.json, frontend/package-lock.json
- Evidence:
  - @sparkjsdev/spark set to ^2.0.0
  - lock resolved URL points to npm registry tarball
  - clean install and npm ls baseline captured in dependency-baseline.md

### Requirement: stable public APIs only

- Implemented in: frontend/src/hooks/useXR.ts
- Evidence:
  - Removed access to internal defaultView.stochastic path
  - XR behavior uses SparkRenderer public fields only (autoUpdate/preUpdate and quality params)

### Requirement: deterministic migration checklist

- Implemented in: openspec/changes/upgrade-spark-2-0-0-and-quick-wins/migration-checklist.md

## spark-lod-quick-wins

### Requirement: LoD quick-tuning presets

- Implemented in:
  - frontend/src/constants/spark.ts
  - frontend/src/store/useAppStore.ts
  - frontend/src/hooks/useViewer.ts
  - frontend/src/components/layout/Settings/Settings.tsx
- Evidence:
  - performance/balanced/detail presets defined in state
  - SparkRenderer and SplatMesh params updated instantly via runtime subscription
  - settings UI uses preset-first flow with manual mode revealing advanced options
  - quick presets do not force RAD path, keeping non-RAD models usable in default flow

### Requirement: LoD vs non-LoD toggle

- Implemented in:
  - frontend/src/store/useAppStore.ts
  - frontend/src/hooks/useViewer.ts
  - frontend/src/components/layout/Settings/Settings.tsx
- Evidence:
  - SplatMesh loaded with lod + nonLod options
  - enableLod switched at runtime through compare mode
  - UI disables non-LoD switch if dual-source data is unavailable

### Requirement: interaction stability

- Implemented in: frontend/src/hooks/useViewer.ts
- Evidence:
  - Existing camera reset/orbit/click-focus paths preserved
  - LoD updates only touch Spark params and do not alter controls wiring

## spark-rad-streaming-workflow

### Requirement: optional RAD paged loading

- Implemented in:
  - frontend/src/store/useAppStore.ts
  - frontend/src/components/layout/Settings/Settings.tsx
  - frontend/src/hooks/useViewer.ts
- Evidence:
  - RAD mode and paged toggle exposed in settings
  - Loader tries RAD branch with paged option when enabled
  - RAD mode remains manual advanced option instead of being auto-forced by quick presets

### Requirement: fallback to non-RAD formats

- Implemented in: frontend/src/hooks/useViewer.ts
- Evidence:
  - On RAD load failure (non-RAD selected source), loader falls back to original SPZ/PLY/SPLAT path
  - Missing derived RAD URL (404) is cached per session to avoid repeated retry loops and log noise

### Requirement: offline RAD generation contract

- Implemented in: openspec/changes/upgrade-spark-2-0-0-and-quick-wins/rad-workflow.md
- Evidence:
  - command entrypoints, options, output naming, and frontend loading contract documented

## Additional Verification Artifacts

- Baseline template: openspec/changes/upgrade-spark-2-0-0-and-quick-wins/baseline-template.md
- Migration checklist: openspec/changes/upgrade-spark-2-0-0-and-quick-wins/migration-checklist.md
