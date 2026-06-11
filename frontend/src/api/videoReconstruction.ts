import { apiGet, apiPost } from './client';
import type {
  VideoReconstructionRequest,
  VideoReconstructionResponse,
  VideoReconstructionStatusResponse,
} from '@/types';

export async function fetchVideoReconstructionStatus(): Promise<VideoReconstructionStatusResponse> {
  return apiGet<VideoReconstructionStatusResponse>('/api/video-reconstructions/status');
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
