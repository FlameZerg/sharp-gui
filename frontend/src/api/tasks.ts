import { apiGet, apiPost, apiPostFormDataWithProgress } from './client';
import type { TasksResponse, GenerateResponse } from '@/types';

interface UploadProgress {
  loaded: number;
  total: number | null;
  percent: number;
  lengthComputable: boolean;
}

/**
 * Fetch all tasks with status
 */
export async function fetchTasks(): Promise<TasksResponse> {
  return apiGet<TasksResponse>('/api/tasks');
}

/**
 * Cancel a specific task
 */
export async function cancelTask(
  taskId: string
): Promise<{ success: boolean; error?: string }> {
  return apiPost(`/api/task/${taskId}/cancel`);
}

/**
 * Upload images to generate 3D models
 */
export async function generateFromImages(
  files: FileList | File[],
  options?: {
    onUploadProgress?: (progress: UploadProgress) => void;
  },
): Promise<GenerateResponse> {
  const formData = new FormData();
  
  for (const file of files) {
    if (file.type.startsWith('image/') || /\.(jpe?g|png|webp)$/i.test(file.name)) {
      formData.append('file', file);
    }
  }
  
  return apiPostFormDataWithProgress<GenerateResponse>('/api/generate', formData, {
    onUploadProgress: options?.onUploadProgress,
  });
}
