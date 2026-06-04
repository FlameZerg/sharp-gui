import { apiDelete, apiGet, apiPost, apiPostBlob, apiPostFormData } from './client';
import type {
  AddPhotoAlbumRequest,
  AddPhotoAlbumResponse,
  PhotoAlbumsResponse,
  PhotoConversionResponse,
  PhotoListResponse,
  PhotoUploadResponse,
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

export async function uploadPhotosToGallery(
  albumId: string,
  files: FileList | File[],
): Promise<PhotoUploadResponse> {
  const formData = new FormData();

  for (const file of files) {
    if (file.type.startsWith('image/') || /\.(jpe?g|png|webp)$/i.test(file.name)) {
      formData.append('file', file);
    }
  }

  return apiPostFormData<PhotoUploadResponse>(
    `/api/photo-albums/${encodeURIComponent(albumId)}/uploads`,
    formData,
    { timeout: 300000 },
  );
}

function getDownloadFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return plainMatch?.[1] ?? null;
}

export async function downloadPhotos(
  photoIds: string[],
): Promise<{ downloaded: number; failed: number; filename: string }> {
  const { blob, response } = await apiPostBlob(
    '/api/photo-downloads',
    { photo_ids: photoIds },
    { timeout: 300000 },
  );
  const filename = getDownloadFilename(response.headers.get('Content-Disposition'))
    ?? 'sharp-gui-photos.zip';
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);

  return {
    downloaded: Number(response.headers.get('X-Photo-Download-Count') ?? photoIds.length),
    failed: Number(response.headers.get('X-Photo-Download-Failed') ?? 0),
    filename,
  };
}
