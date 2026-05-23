import { apiDelete, apiGet, apiPost } from './client';
import type {
  AddPhotoAlbumRequest,
  AddPhotoAlbumResponse,
  PhotoAlbumsResponse,
  PhotoConversionResponse,
  PhotoListResponse,
} from '@/types';

export async function fetchPhotoAlbums(): Promise<PhotoAlbumsResponse> {
  return apiGet<PhotoAlbumsResponse>('/api/photo-albums');
}

export async function addPhotoAlbum(
  request: AddPhotoAlbumRequest,
): Promise<AddPhotoAlbumResponse> {
  return apiPost<AddPhotoAlbumResponse>('/api/photo-albums', request);
}

export async function deletePhotoAlbum(
  albumId: string,
): Promise<{ success: boolean; error?: string }> {
  return apiDelete(`/api/photo-albums/${encodeURIComponent(albumId)}`);
}

export async function rescanPhotoAlbum(
  albumId: string,
): Promise<AddPhotoAlbumResponse> {
  return apiPost<AddPhotoAlbumResponse>(`/api/photo-albums/${encodeURIComponent(albumId)}/scan`);
}

export async function fetchPhotoAlbumPhotos(
  albumId: string,
  cursor: string | null,
  limit = 60,
  sort = 'mtime_desc',
): Promise<PhotoListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    sort,
  });
  if (cursor) {
    params.set('cursor', cursor);
  }

  return apiGet<PhotoListResponse>(
    `/api/photo-albums/${encodeURIComponent(albumId)}/photos?${params.toString()}`,
  );
}

export async function convertPhotosToModels(
  photoIds: string[],
): Promise<PhotoConversionResponse> {
  return apiPost<PhotoConversionResponse>(
    '/api/photo-conversions',
    { photo_ids: photoIds },
    { timeout: 300000 },
  );
}

