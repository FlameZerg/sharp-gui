## 1. Gallery Contract and Foundations

- [x] 1.1 Update the backend gallery contract in `app.py` so row previews only expose real thumbnail resources, add thumbnail-friendly cache/conditional response handling, and remove full-resolution original images as the default row-preview fallback.
- [x] 1.2 Sync `frontend/src/api/gallery.ts`, `frontend/src/types/gallery.ts`, and any related callers with the new thumbnail semantics and metadata needed for stable gallery reconciliation.
- [x] 1.3 Add the chosen virtualized-list dependency and a thin local adapter/scaffold so the gallery renderer can be swapped or rolled back without rewriting business components.

## 2. Sidebar Layout and Virtualized Gallery Rendering

- [x] 2.1 Refactor `Sidebar` / gallery layout so the model list owns a single predictable scroll viewport on desktop and mobile instead of relying on ambiguous nested scrolling.
- [x] 2.2 Rebuild `GalleryList` around virtualized row rendering with overscan, active-row awareness, and stable scroll-to-selection behavior for large galleries.
- [x] 2.3 Refactor `GalleryItem` thumbnail handling to use explicit loading, ready, and fallback states with near-viewport preloading, while keeping rows visually stable during fast scrolling and viewport re-entry.

## 3. Store Isolation and Refresh Coordination

- [x] 3.1 Convert `App`, `GalleryList`, `GalleryItem`, and gallery-related helpers from broad `useAppStore()` subscriptions to selector-based reads and stable row props so unrelated viewer state changes do not fan out into list rerenders.
- [x] 3.2 Implement a merge-aware gallery update path that preserves row identity, active selection, and the current scroll anchor when `useTaskQueue` refreshes gallery data after task completion.
- [x] 3.3 Ensure sidebar collapse/expand, mobile sidebar open/close, and other non-gallery UI state changes keep the current gallery browsing context and loaded thumbnail state intact.

## 4. Fallback UX, i18n, and Rollback Safety

- [x] 4.1 Add any new gallery loading, fallback, or error text to both `frontend/src/i18n/en.json` and `frontend/src/i18n/zh.json`, and wire the new text into the list states.
- [x] 4.2 Add accessible fallback UI for missing or failed thumbnails so the row remains operable, selectable, and semantically labeled even when image loading is unsuccessful.
- [x] 4.3 Keep a short-term rollback path between the legacy and virtualized gallery renderers until the new path is validated against the key browsing scenarios.

## 5. Validation and Regression Checks

- [x] 5.1 Validate large-gallery browsing scenarios with a sufficiently dense dataset, including initial open, deep scroll, fast scroll, and re-entering previously viewed rows.
- [x] 5.2 Validate task-completion refresh, selected-row preservation, missing-thumbnail fallback, delete flow, and desktop/mobile sidebar visibility changes against the spec scenarios.
- [x] 5.3 Run the relevant verification commands (`npm run build`, repo-appropriate lint checks) plus targeted manual gallery regression, and fix any regressions introduced by the change.
