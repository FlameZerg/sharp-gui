# Spark 2.0.0 Migration Verification Checklist

## Usage

- Mark each check as Pass or Fail.
- Record evidence links or short notes for failed items.
- A full migration pass requires all P0 checks to pass.

## 1. Build and Dependency Baseline

| Priority | Check | Pass Criteria |
|---|---|---|
| P0 | Dependency source | package-lock resolves @sparkjsdev/spark from npm registry tarball, not git source |
| P0 | Dependency version | npm ls shows @sparkjsdev/spark@2.0.0 and three@0.180.x |
| P0 | Clean install | rm -rf node_modules && npm ci succeeds |
| P0 | Type + build | npm run build succeeds without Spark-related errors |
| P1 | Lint | npm run lint succeeds, or only unrelated pre-existing issues remain |

## 2. Loading Pipeline

| Priority | Check | Pass Criteria |
|---|---|---|
| P0 | SPZ/PLY/SPLAT fallback | Standard assets load and render correctly |
| P0 | RAD preferred mode | When RAD mode is on and RAD exists, viewer loads RAD path |
| P0 | RAD fallback | When RAD mode is on and RAD is missing, viewer falls back to non-RAD path |
| P1 | Paged toggle | RAD paged on/off both work without crash |
| P1 | Drag and drop | .ply/.splat/.spz/.rad drag-drop all behave as expected |

## 3. LoD Quick Wins

| Priority | Check | Pass Criteria |
|---|---|---|
| P0 | Preset switch | performance/balanced/detail presets apply immediately without model reload |
| P0 | LoD toggle | LoD on/off updates rendering behavior without breaking session |
| P1 | LoD/non-LoD compare | Non-LoD toggle works when both datasets are available |
| P1 | Compare guardrail | Compare switch is disabled when non-LoD source is unavailable |

## 4. XR Lifecycle

| Priority | Check | Pass Criteria |
|---|---|---|
| P0 | Enter/exit VR | VR session enters and exits cleanly; camera and controls restore |
| P0 | Enter/exit AR | AR session enters and exits cleanly; background and scale restore |
| P0 | XR update strategy | Auto mode and Manual rollback mode both run without render stall |
| P1 | Reset behavior | Controller reset returns rig to calibrated home position |

## 5. Interaction Stability

| Priority | Check | Pass Criteria |
|---|---|---|
| P0 | Camera reset | Reset keeps expected orientation and focus behavior |
| P0 | Orbit + pan + zoom | Core controls work after preset/rad/xr changes |
| P0 | Click-to-focus | Raycast focus still works on loaded model |
| P1 | Transform baseline | Model scale and rotation conventions unchanged |

## 6. Result Summary

| Area | Result | Notes |
|---|---|---|
| Build baseline |  |  |
| Loading pipeline |  |  |
| LoD quick wins |  |  |
| XR lifecycle |  |  |
| Interaction stability |  |  |

Final decision:

- [ ] Migration accepted
- [ ] Migration rejected
- [ ] Migration accepted with follow-up issues
