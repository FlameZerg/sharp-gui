import { apiGet, apiPost } from './client';
import type { ModelFormat, VideoReconstructionConfig } from '@/types';

export interface SettingsData {
  workspace_folder?: string;
  model_format?: ModelFormat;
  is_local?: boolean;
  video_reconstruction?: VideoReconstructionConfig;
}

/**
 * Fetch current settings
 */
export async function fetchSettings(): Promise<SettingsData> {
  return apiGet<SettingsData>('/api/settings');
}

/**
 * Save settings
 */
export async function saveSettings(
  settings: SettingsData
): Promise<{ success: boolean; needs_restart?: boolean; error?: string }> {
  return apiPost('/api/settings', settings);
}

/**
 * Request folder selection dialog (local only)
 */
export async function browseFolder(
  title: string,
  initialDir?: string
): Promise<{ success: boolean; path?: string; error?: string }> {
  return apiPost('/api/browse-folder', { title, initial_dir: initialDir });
}

/**
 * Restart server (local only)
 */
export async function restartServer(): Promise<void> {
  try {
    await apiPost('/api/restart');
  } catch {
    // Restart will close connection, this is expected
  }
}

/**
 * Batch convert all existing PLY models to SPZ (local only)
 */
export async function convertAllToSpz(): Promise<{
  success: boolean;
  converted: number;
  skipped: number;
  failed: number;
  total: number;
}> {
  return apiPost('/api/convert-all', undefined, { timeout: 300000 });
}
