# Sharp GUI Frontend

React 19 + TypeScript + Vite frontend for Sharp GUI. The production build is served by the Flask backend from `frontend/dist/`; release packages already include this build, so normal users do not need Node.js.

## Stack

- React 19 + TypeScript 5.9 + Vite 7
- Zustand single-store state management
- i18next + react-i18next bilingual UI
- Three.js + `@sparkjsdev/spark` 2.0 viewer
- CSS Modules + CSS Variables design system

## Key Areas

```
src/
├── api/          # fetch client and API modules
├── components/   # common, gallery, layout, viewer components
├── constants/    # Spark/LoD constants
├── hooks/        # viewer, XR, keyboard, gallery virtualizer, task queue hooks
├── i18n/         # en.json + zh.json
├── store/        # useAppStore Zustand store
├── styles/       # variables, animations, global styles
├── types/        # shared TypeScript types
└── utils/        # camera, format, gallery, reveal effects helpers
```

## Development

```bash
npm install
npm run dev
npm run build
npm run lint
```

Run the Flask backend separately for API/file requests. Vite proxies `/api` and `/files` to the backend during development.

## Notes For Agents

- Read `../.antigravityrules` and the referenced `.agents/rules/*.md` files before changing code.
- Use `@/` imports for frontend source paths and `import type` for pure type imports.
- Keep user-visible text synchronized in `src/i18n/en.json` and `src/i18n/zh.json`.
- New components use `ComponentName.tsx` + `ComponentName.module.css` + `index.ts`, named exports, and CSS Modules.
- Do not add Tailwind, Sass, CSS-in-JS, axios, Redux, or default exports in new code.
