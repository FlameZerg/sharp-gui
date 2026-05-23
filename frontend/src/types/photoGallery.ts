export type AppView = 'models' | 'photos';

export type PhotoAlbumScanStatus = 'idle' | 'scanning' | 'error';

export interface PhotoAlbum {
  id: string;
  name: string;
  cover_thumb_url: string | null;
  photo_count: number | null;
  recursive: boolean;
  enabled: boolean;
  scan_status: PhotoAlbumScanStatus;
  updated_at: string | null;
  error?: string | null;
}

export interface PhotoItem {
  id: string;
  album_id: string;
  name: string;
  width: number | null;
  height: number | null;
  thumb_url: string | null;
  full_url?: string;
  preview_url: string;
  download_url: string;
  size?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PhotoAlbumsResponse {
  albums: PhotoAlbum[];
  is_local?: boolean;
}

export interface AddPhotoAlbumRequest {
  path: string;
  name?: string;
  recursive?: boolean;
}

export interface AddPhotoAlbumResponse {
  success: boolean;
  album: PhotoAlbum;
  duplicate?: boolean;
  error?: string;
}

export interface PhotoListResponse {
  items: PhotoItem[];
  next_cursor: string | null;
  total: number;
  scan_status: PhotoAlbumScanStatus;
  error?: string | null;
}

export interface PhotoConversionResponse {
  success: boolean;
  tasks?: import('./task').Task[];
  failed?: Array<{
    id: string;
    error: string;
  }>;
  error?: string;
}
