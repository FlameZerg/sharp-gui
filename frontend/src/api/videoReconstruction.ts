import { apiGet, apiPost, apiPostFormData } from './client';
import type {
  VideoReconstructionRequest,
  VideoReconstructionResponse,
  VideoReconstructionStatusResponse,
} from '@/types';

export async function fetchVideoReconstructionStatus(options?: {
  refresh?: boolean;
}): Promise<VideoReconstructionStatusResponse> {
  const query = options?.refresh ? '?refresh=1' : '';
  return apiGet<VideoReconstructionStatusResponse>(`/api/video-reconstructions/status${query}`);
}

export async function createVideoReconstruction(
  request: VideoReconstructionRequest,
): Promise<VideoReconstructionResponse> {
  return apiPost<VideoReconstructionResponse>(
    '/api/video-reconstructions',
    request,
    { timeout: 300000 },
  );
}

export async function createVideoReconstructionFromFile(
  file: File,
  options?: Omit<VideoReconstructionRequest, 'video_id'>,
): Promise<VideoReconstructionResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (options?.mode) {
    formData.append('mode', options.mode);
  }
  if (options?.quality) {
    formData.append('quality', options.quality);
  }
  if (options?.engine) {
    formData.append('engine', options.engine);
  }
  if (options?.output_name) {
    formData.append('output_name', options.output_name);
  }
  if (typeof options?.keep_intermediate_files === 'boolean') {
    formData.append('keep_intermediate_files', String(options.keep_intermediate_files));
  }

  return apiPostFormData<VideoReconstructionResponse>(
    '/api/video-reconstructions/upload',
    formData,
    { timeout: 300000 },
  );
}
