import { create } from 'zustand';
import type { GalleryItem, Task, ModelFormat } from '@/types';
import type {
  LodCompareMode,
  LodPresetKey,
  QuickPresetMode,
  XrUpdateMode,
  ViewerModelFormat,
} from '@/constants/spark';

// localStorage keys for client-side preference overrides
const LOCAL_FORMAT_KEY = 'sharp-model-format';
const LOCAL_LOD_KEY = 'sharp-lod-enabled';
const LOCAL_HF_KEY = 'sharp-high-fidelity';
const LOCAL_LOD_PRESET_KEY = 'sharp-lod-preset';
const LOCAL_QUICK_PRESET_KEY = 'sharp-quick-preset-mode';
const LOCAL_LOD_COMPARE_KEY = 'sharp-lod-compare-mode';
const LOCAL_RAD_MODE_KEY = 'sharp-rad-mode-enabled';
const LOCAL_RAD_PAGED_KEY = 'sharp-rad-paged-enabled';
const LOCAL_XR_UPDATE_MODE_KEY = 'sharp-xr-update-mode';

function getLocalFormatOverride(): ModelFormat | null {
  try {
    const v = localStorage.getItem(LOCAL_FORMAT_KEY);
    if (v === 'ply' || v === 'spz') return v;
  } catch { /* ignore */ }
  return null;
}

function getLocalLodSetting(): boolean {
  try {
    return localStorage.getItem(LOCAL_LOD_KEY) === 'true';
  } catch { /* ignore */ }
  return false;
}

function getLocalHfSetting(): boolean {
  try {
    return localStorage.getItem(LOCAL_HF_KEY) === 'true';
  } catch { /* ignore */ }
  return false;
}

function getLocalLodPreset(): LodPresetKey {
  try {
    const v = localStorage.getItem(LOCAL_LOD_PRESET_KEY);
    if (v === 'performance' || v === 'balanced' || v === 'detail') {
      return v;
    }
  } catch { /* ignore */ }
  return 'balanced';
}

function getLocalQuickPresetMode(): QuickPresetMode {
  try {
    const v = localStorage.getItem(LOCAL_QUICK_PRESET_KEY);
    if (v === 'performance' || v === 'balanced' || v === 'detail' || v === 'manual') {
      return v;
    }
  } catch { /* ignore */ }
  return 'balanced';
}

function getLocalLodCompareMode(): LodCompareMode {
  try {
    const v = localStorage.getItem(LOCAL_LOD_COMPARE_KEY);
    if (v === 'lod' || v === 'non-lod') return v;
  } catch { /* ignore */ }
  return 'lod';
}

function getLocalRadModeEnabled(): boolean {
  try {
    return localStorage.getItem(LOCAL_RAD_MODE_KEY) === 'true';
  } catch { /* ignore */ }
  return false;
}

function getLocalRadPagedEnabled(): boolean {
  try {
    const v = localStorage.getItem(LOCAL_RAD_PAGED_KEY);
    if (v === null) return true;
    return v === 'true';
  } catch { /* ignore */ }
  return true;
}

function getLocalXrUpdateMode(): XrUpdateMode {
  try {
    const v = localStorage.getItem(LOCAL_XR_UPDATE_MODE_KEY);
    if (v === 'auto' || v === 'manual') return v;
  } catch { /* ignore */ }
  return 'auto';
}

interface QuickPresetState {
  isLodEnabled: boolean;
  lodPreset: LodPresetKey;
  lodCompareMode: LodCompareMode;
  radModeEnabled: boolean;
  radPagedEnabled: boolean;
  xrUpdateMode: XrUpdateMode;
  isHighFidelity: boolean;
}

function getQuickPresetState(mode: LodPresetKey): QuickPresetState {
  if (mode === 'performance') {
    return {
      isLodEnabled: true,
      lodPreset: 'performance',
      lodCompareMode: 'lod',
      radModeEnabled: false,
      radPagedEnabled: false,
      xrUpdateMode: 'auto',
      isHighFidelity: false,
    };
  }

  if (mode === 'balanced') {
    return {
      isLodEnabled: true,
      lodPreset: 'balanced',
      lodCompareMode: 'lod',
      radModeEnabled: false,
      radPagedEnabled: true,
      xrUpdateMode: 'auto',
      isHighFidelity: false,
    };
  }

  return {
    isLodEnabled: true,
    lodPreset: 'detail',
    lodCompareMode: 'lod',
    radModeEnabled: false,
    radPagedEnabled: false,
    xrUpdateMode: 'auto',
    isHighFidelity: true,
  };
}

function getInitialViewerPresetState(): { quickPresetMode: QuickPresetMode } & QuickPresetState {
  const quickPresetMode = getLocalQuickPresetMode();
  if (quickPresetMode !== 'manual') {
    return {
      quickPresetMode,
      ...getQuickPresetState(quickPresetMode),
    };
  }

  return {
    quickPresetMode,
    isLodEnabled: getLocalLodSetting(),
    lodPreset: getLocalLodPreset(),
    lodCompareMode: getLocalLodCompareMode(),
    radModeEnabled: getLocalRadModeEnabled(),
    radPagedEnabled: getLocalRadPagedEnabled(),
    xrUpdateMode: getLocalXrUpdateMode(),
    isHighFidelity: getLocalHfSetting(),
  };
}

const initialViewerPresetState = getInitialViewerPresetState();

interface AppState {
  // UI State
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  controlsCollapsed: boolean;
  helpPanelVisible: boolean;
  settingsModalOpen: boolean;

  // Loading State
  isLoading: boolean;
  loadingText: string;
  loadingProgress: number;

  // Boot State
  isBooting: boolean;
  bootError: string | null;

  // Gallery
  galleryItems: GalleryItem[];
  currentModelId: string | null;
  currentModelUrl: string | null;
  currentModelFormat: ViewerModelFormat; // Format hint for blob URLs
  previewImage: GalleryItem | null; // For image lightbox

  // Model Format Preference
  serverModelFormat: ModelFormat;        // Host default from config.json
  localModelFormat: ModelFormat | null;  // Client override via localStorage

  // Task Queue
  tasks: Task[];
  hasActiveTasks: boolean;

  // Viewer
  isLimitsOn: boolean;
  isGyroEnabled: boolean;
  isJoystickEnabled: boolean;
  quickPresetMode: QuickPresetMode;
  isLodEnabled: boolean;
  lodPreset: LodPresetKey;
  lodCompareMode: LodCompareMode;
  canCompareLod: boolean;
  radModeEnabled: boolean;
  radPagedEnabled: boolean;
  usedRadLastLoad: boolean;
  xrUpdateMode: XrUpdateMode;
  isHighFidelity: boolean;

  // Settings
  isLocalAccess: boolean;

  // Computed
  /** Effective format: client override > server default */
  effectiveModelFormat: () => ModelFormat;

  // Actions
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  toggleSidebarCollapsed: () => void;
  toggleControlsCollapsed: () => void;
  toggleHelpPanel: () => void;
  setSettingsModalOpen: (open: boolean) => void;

  setLoading: (loading: boolean, text?: string) => void;
  setLoadingProgress: (progress: number) => void;

  setBootComplete: () => void;
  setBootError: (error: string) => void;

  setGalleryItems: (items: GalleryItem[]) => void;
  setCurrentModel: (id: string | null, url: string | null, format?: ViewerModelFormat) => void;
  setPreviewImage: (item: GalleryItem | null) => void;

  setServerModelFormat: (format: ModelFormat) => void;
  setLocalModelFormat: (format: ModelFormat | null) => void;
  toggleLocalModelFormat: () => void;

  setTasks: (tasks: Task[], hasActive: boolean) => void;

  toggleLimits: () => void;
  toggleGyro: () => void;
  toggleJoystick: () => void;
  setQuickPresetMode: (mode: QuickPresetMode) => void;
  applyQuickPreset: (mode: LodPresetKey) => void;
  toggleLod: () => void;
  setLodPreset: (preset: LodPresetKey) => void;
  setLodCompareMode: (mode: LodCompareMode) => void;
  setCanCompareLod: (canCompare: boolean) => void;
  setRadModeEnabled: (enabled: boolean) => void;
  setRadPagedEnabled: (enabled: boolean) => void;
  setUsedRadLastLoad: (used: boolean) => void;
  setXrUpdateMode: (mode: XrUpdateMode) => void;
  toggleHighFidelity: () => void;

  setLocalAccess: (isLocal: boolean) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Initial State
  sidebarOpen: false,
  sidebarCollapsed: false,
  controlsCollapsed: false,
  helpPanelVisible: false,
  settingsModalOpen: false,

  isLoading: false,
  loadingText: '',
  loadingProgress: 0,

  isBooting: true,
  bootError: null,

  galleryItems: [],
  currentModelId: null,
  currentModelUrl: null,
  currentModelFormat: null,
  previewImage: null,

  // Model Format Preference
  serverModelFormat: 'spz',
  localModelFormat: getLocalFormatOverride(),

  tasks: [],
  hasActiveTasks: false,

  isLimitsOn: true,
  isGyroEnabled: false,
  isJoystickEnabled: false,
  quickPresetMode: initialViewerPresetState.quickPresetMode,
  isLodEnabled: initialViewerPresetState.isLodEnabled,
  lodPreset: initialViewerPresetState.lodPreset,
  lodCompareMode: initialViewerPresetState.lodCompareMode,
  canCompareLod: false,
  radModeEnabled: initialViewerPresetState.radModeEnabled,
  radPagedEnabled: initialViewerPresetState.radPagedEnabled,
  usedRadLastLoad: false,
  xrUpdateMode: initialViewerPresetState.xrUpdateMode,
  isHighFidelity: initialViewerPresetState.isHighFidelity,

  isLocalAccess: false,

  // Computed: client override > server default
  effectiveModelFormat: () => {
    const state = get();
    return state.localModelFormat ?? state.serverModelFormat;
  },

  // Actions
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  toggleControlsCollapsed: () => set((state) => ({ controlsCollapsed: !state.controlsCollapsed })),
  toggleHelpPanel: () => set((state) => ({ helpPanelVisible: !state.helpPanelVisible })),
  setSettingsModalOpen: (open) => set({ settingsModalOpen: open }),

  setLoading: (loading, text = '') => set((state) => ({
    isLoading: loading,
    loadingText: text,
    loadingProgress: loading
      ? (state.isLoading ? state.loadingProgress : 0)
      : 0,
  })),
  setLoadingProgress: (progress) => set((state) => ({
    loadingProgress: Math.max(state.loadingProgress, progress),
  })),

  setBootComplete: () => set({ isBooting: false }),
  setBootError: (error) => set({ bootError: error }),

  setGalleryItems: (items) => set({ galleryItems: items }),
  setCurrentModel: (id, url, format = null) => set({ currentModelId: id, currentModelUrl: url, currentModelFormat: format }),
  setPreviewImage: (item) => set({ previewImage: item }),

  setServerModelFormat: (format) => set({ serverModelFormat: format }),
  setLocalModelFormat: (format) => {
    if (format) {
      try { localStorage.setItem(LOCAL_FORMAT_KEY, format); } catch { /* ignore */ }
    } else {
      try { localStorage.removeItem(LOCAL_FORMAT_KEY); } catch { /* ignore */ }
    }
    set({ localModelFormat: format });
  },
  toggleLocalModelFormat: () => {
    const state = get();
    const current = state.localModelFormat ?? state.serverModelFormat;
    const next: ModelFormat = current === 'spz' ? 'ply' : 'spz';
    // Set as local override
    try { localStorage.setItem(LOCAL_FORMAT_KEY, next); } catch { /* ignore */ }
    set({ localModelFormat: next });
  },

  setTasks: (tasks, hasActive) => set({ tasks, hasActiveTasks: hasActive }),

  toggleLimits: () => set((state) => ({ isLimitsOn: !state.isLimitsOn })),
  toggleGyro: () => set((state) => ({ isGyroEnabled: !state.isGyroEnabled })),
  toggleJoystick: () => set((state) => ({ isJoystickEnabled: !state.isJoystickEnabled })),
  setQuickPresetMode: (mode) => {
    try { localStorage.setItem(LOCAL_QUICK_PRESET_KEY, mode); } catch { /* ignore */ }
    set({ quickPresetMode: mode });
  },
  applyQuickPreset: (mode) => {
    const next = getQuickPresetState(mode);

    try { localStorage.setItem(LOCAL_QUICK_PRESET_KEY, mode); } catch { /* ignore */ }
    try { localStorage.setItem(LOCAL_LOD_KEY, String(next.isLodEnabled)); } catch { /* ignore */ }
    try { localStorage.setItem(LOCAL_LOD_PRESET_KEY, next.lodPreset); } catch { /* ignore */ }
    try { localStorage.setItem(LOCAL_LOD_COMPARE_KEY, next.lodCompareMode); } catch { /* ignore */ }
    try { localStorage.setItem(LOCAL_RAD_MODE_KEY, String(next.radModeEnabled)); } catch { /* ignore */ }
    try { localStorage.setItem(LOCAL_RAD_PAGED_KEY, String(next.radPagedEnabled)); } catch { /* ignore */ }
    try { localStorage.setItem(LOCAL_XR_UPDATE_MODE_KEY, next.xrUpdateMode); } catch { /* ignore */ }
    try { localStorage.setItem(LOCAL_HF_KEY, String(next.isHighFidelity)); } catch { /* ignore */ }

    set({
      quickPresetMode: mode,
      isLodEnabled: next.isLodEnabled,
      lodPreset: next.lodPreset,
      lodCompareMode: next.lodCompareMode,
      radModeEnabled: next.radModeEnabled,
      radPagedEnabled: next.radPagedEnabled,
      xrUpdateMode: next.xrUpdateMode,
      isHighFidelity: next.isHighFidelity,
    });
  },
  toggleLod: () => {
    const next = !get().isLodEnabled;
    try { localStorage.setItem(LOCAL_LOD_KEY, String(next)); } catch { /* ignore */ }
    set({ isLodEnabled: next });
  },
  setLodPreset: (preset) => {
    try { localStorage.setItem(LOCAL_LOD_PRESET_KEY, preset); } catch { /* ignore */ }
    set({ lodPreset: preset });
  },
  setLodCompareMode: (mode) => {
    const canCompareLod = get().canCompareLod;
    const nextMode: LodCompareMode = canCompareLod ? mode : 'lod';
    try { localStorage.setItem(LOCAL_LOD_COMPARE_KEY, nextMode); } catch { /* ignore */ }
    set({ lodCompareMode: nextMode });
  },
  setCanCompareLod: (canCompare) => {
    set((state) => ({
      canCompareLod: canCompare,
      lodCompareMode: canCompare ? state.lodCompareMode : 'lod',
    }));
    if (!canCompare) {
      try { localStorage.setItem(LOCAL_LOD_COMPARE_KEY, 'lod'); } catch { /* ignore */ }
    }
  },
  setRadModeEnabled: (enabled) => {
    try { localStorage.setItem(LOCAL_RAD_MODE_KEY, String(enabled)); } catch { /* ignore */ }
    set({ radModeEnabled: enabled });
  },
  setRadPagedEnabled: (enabled) => {
    try { localStorage.setItem(LOCAL_RAD_PAGED_KEY, String(enabled)); } catch { /* ignore */ }
    set({ radPagedEnabled: enabled });
  },
  setUsedRadLastLoad: (used) => set({ usedRadLastLoad: used }),
  setXrUpdateMode: (mode) => {
    try { localStorage.setItem(LOCAL_XR_UPDATE_MODE_KEY, mode); } catch { /* ignore */ }
    set({ xrUpdateMode: mode });
  },
  toggleHighFidelity: () => {
    const next = !get().isHighFidelity;
    try { localStorage.setItem(LOCAL_HF_KEY, String(next)); } catch { /* ignore */ }
    set({ isHighFidelity: next });
  },

  setLocalAccess: (isLocal) => set({ isLocalAccess: isLocal }),
}));
