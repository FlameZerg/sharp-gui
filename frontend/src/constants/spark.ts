import { SplatFileType } from '@sparkjsdev/spark';
import type { SparkRenderer, SplatMesh } from '@sparkjsdev/spark';

export type ViewerModelFormat = 'ply' | 'splat' | 'spz' | 'rad' | null;

export type LodPresetKey = 'performance' | 'balanced' | 'detail';
export type QuickPresetMode = LodPresetKey | 'manual';
export type LodCompareMode = 'lod' | 'non-lod';
export type XrUpdateMode = 'auto' | 'manual';

export interface LodPresetConfig {
  lodSplatScale: number;
  lodRenderScale: number;
  behindFoveate: number;
  coneFov0: number;
  coneFov: number;
  coneFoveate: number;
}

export const LOD_PRESETS: Record<LodPresetKey, LodPresetConfig> = {
  performance: {
    lodSplatScale: 0.55,
    lodRenderScale: 2.2,
    behindFoveate: 0.45,
    coneFov0: 44,
    coneFov: 90,
    coneFoveate: 0.9,
  },
  balanced: {
    lodSplatScale: 0.95,
    lodRenderScale: 1.35,
    behindFoveate: 0.15,
    coneFov0: 58,
    coneFov: 112,
    coneFoveate: 0.6,
  },
  detail: {
    lodSplatScale: 1.35,
    lodRenderScale: 0.95,
    behindFoveate: 0.03,
    coneFov0: 72,
    coneFov: 135,
    coneFoveate: 0.3,
  },
};

const DEFAULT_PRESET: LodPresetKey = 'balanced';

const MODEL_EXT_RE = /\.(ply|spz|splat|rad)(\?.*)?$/i;

export function getLodPresetConfig(preset: LodPresetKey): LodPresetConfig {
  return LOD_PRESETS[preset] ?? LOD_PRESETS[DEFAULT_PRESET];
}

export function getSplatFileTypeFromFormat(
  format: ViewerModelFormat,
): SplatFileType | undefined {
  if (format === 'ply') return SplatFileType.PLY;
  if (format === 'splat') return SplatFileType.SPLAT;
  if (format === 'spz') return SplatFileType.SPZ;
  if (format === 'rad') return SplatFileType.RAD;
  return undefined;
}

export function deriveRadUrl(url: string): string | null {
  if (url.startsWith('blob:') || url.startsWith('data:')) {
    return null;
  }

  const match = MODEL_EXT_RE.exec(url);
  if (!match) return null;

  const ext = match[1].toLowerCase();
  if (ext === 'rad') return null;

  return url.replace(MODEL_EXT_RE, '.rad$2');
}

export function applyLodPresetToRenderer(
  renderer: SparkRenderer,
  preset: LodPresetConfig,
): void {
  renderer.lodSplatScale = preset.lodSplatScale;
  renderer.lodRenderScale = preset.lodRenderScale;
  renderer.behindFoveate = preset.behindFoveate;
  renderer.coneFov0 = preset.coneFov0;
  renderer.coneFov = preset.coneFov;
  renderer.coneFoveate = preset.coneFoveate;
}

export function applyLodPresetToMesh(
  mesh: SplatMesh,
  preset: LodPresetConfig,
): void {
  mesh.lodScale = preset.lodSplatScale;
  mesh.behindFoveate = preset.behindFoveate;
  mesh.coneFov0 = preset.coneFov0;
  mesh.coneFov = preset.coneFov;
  mesh.coneFoveate = preset.coneFoveate;
}

export function hasLodComparisonData(mesh: SplatMesh): boolean {
  const packedHasLod = Boolean(mesh.packedSplats?.lodSplats);
  const extHasLod = Boolean(mesh.extSplats?.lodSplats);

  const source = mesh.splats as { lodSplats?: unknown } | undefined;
  const sourceHasLod = Boolean(source?.lodSplats);

  return packedHasLod || extHasLod || sourceHasLod;
}
