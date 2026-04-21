## 1. Store and Type Foundations

- [x] 1.1 Define quick-controls data contracts (transform, interaction toggles, quality quick settings, per-model override payload) in frontend type/store layer.
- [x] 1.2 Extend useAppStore with flat state fields and actions for quick-controls open state, draft/applied values, and reset operations.
- [x] 1.3 Add local persistence helpers and model-id keyed override map initialization logic.

## 2. QuickControls Component and Styling

- [x] 2.1 Create QuickControls component three-file structure (QuickControls.tsx, QuickControls.module.css, index.ts) under viewer components.
- [x] 2.2 Implement bottom-right floating trigger and expandable glass panel with grouped sections (姿态校正 / 交互方向).
- [x] 2.3 Implement responsive behavior and layering rules to avoid overlap with Help and ControlsBar on desktop/mobile.

## 3. Viewer Runtime Integration

- [x] 3.1 Mount QuickControls in ViewerCanvas overlay near existing Help control region.
- [x] 3.2 Implement useViewer-side apply pipeline that maps store values to active SplatMesh position/rotation/uniform-scale in real time.
- [x] 3.3 Implement orientation preset mapping (including upside-down correction) and baseline reset behavior.

## 4. Interaction and Quality Parameter Wiring

- [x] 4.1 Wire reverse pointer direction/slide toggles to the viewer control implementation used in desktop/touch interactions.
- [x] 4.2 Remove quick-panel quality controls and keep quality tuning in existing settings/Lod surfaces to avoid duplicated semantics.
- [x] 4.3 Add runtime guards for unavailable contexts (no active model, XR presenting, or unsupported control path).

## 5. Per-Model Restore and Reset Flow

- [x] 5.1 Save quick-controls overrides by current model ID after user adjustments.
- [x] 5.2 Restore overrides when reopening the same model and fallback to defaults for unseen models.
- [x] 5.3 Implement reset-all for active model overrides and verify state/store consistency after reset.

## 6. i18n and Accessibility

- [x] 6.1 Add all quick-controls user-visible strings to both i18n files (frontend/src/i18n/en.json and frontend/src/i18n/zh.json).
- [x] 6.2 Add semantic labels, keyboard operability, and focus-visible styles for trigger and panel controls.
- [x] 6.3 Ensure touch devices do not depend on hover-only affordances and keep tap targets accessible.

## 7. Validation and Regression Checks

- [x] 7.1 Validate all spec scenarios manually: panel toggle, transform updates, preset correction, reverse interaction, per-model restore/reset.
- [x] 7.2 Run frontend lint/build checks and fix regressions introduced by the feature.
- [x] 7.3 Verify visual consistency under 375/768/1024/1440 widths and both light/dark system modes.