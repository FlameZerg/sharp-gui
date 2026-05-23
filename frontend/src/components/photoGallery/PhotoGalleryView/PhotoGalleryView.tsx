import { useCallback, useEffect, useRef, useState } from 'react';

import { useTranslation } from 'react-i18next';
import { useShallow } from 'zustand/react/shallow';

import {
  addPhotoAlbum,
  browseFolder,
  convertPhotosToModels,
  fetchPhotoAlbumPhotos,
  fetchPhotoAlbums,
} from '@/api';
import { CloseIcon } from '@/components/common/Icons';
import { TextInputDialog } from '@/components/common/TextInputDialog';
import { PhotoMasonryGrid } from '@/components/photoGallery/PhotoMasonryGrid';
import { PhotoSelectionBar } from '@/components/photoGallery/PhotoSelectionBar';
import { PhotoToolbar } from '@/components/photoGallery/PhotoToolbar';
import { useAppStore } from '@/store';
import type { PhotoItem } from '@/types';

import styles from './PhotoGalleryView.module.css';

const MIN_GRID_COLUMNS = 1;
const MAX_GRID_COLUMNS = 8;

function getDefaultGridColumns() {
  if (typeof window === 'undefined') {
    return 5;
  }

  if (window.innerWidth <= 768) {
    return 2;
  }
  if (window.innerWidth <= 980) {
    return 3;
  }
  if (window.innerWidth <= 1280) {
    return 4;
  }
  return 5;
}

function clampGridColumns(columns: number) {
  return Math.min(MAX_GRID_COLUMNS, Math.max(MIN_GRID_COLUMNS, columns));
}

function getTouchDistance(touches: React.TouchList) {
  const dx = touches[0].clientX - touches[1].clientX;
  const dy = touches[0].clientY - touches[1].clientY;
  return Math.sqrt(dx * dx + dy * dy);
}

export function PhotoGalleryView() {
  const { t } = useTranslation();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const hasCustomGridColumns = useRef(false);
  const pinchRef = useRef<{ distance: number; columns: number } | null>(null);
  const [sort, setSort] = useState('mtime_desc');
  const [gridColumns, setGridColumns] = useState(getDefaultGridColumns);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [isAddingAlbum, setIsAddingAlbum] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pathDialogOpen, setPathDialogOpen] = useState(false);
  const [notice, setNotice] = useState<{ tone: 'success' | 'error'; message: string } | null>(null);

  const {
    photoAlbums,
    currentPhotoAlbumId,
    photoItems,
    photoNextCursor,
    photoTotal,
    photoSelectionMode,
    selectedPhotoIds,
    isLocalAccess,
    sidebarCollapsed,
    setPhotoAlbums,
    setPhotoItems,
    clearPhotoItems,
    setPhotoSelectionMode,
    toggleSelectedPhoto,
    clearSelectedPhotos,
    setPreviewPhoto,
    setTasks,
    setActiveView,
    setCurrentPhotoAlbum,
  } = useAppStore(
    useShallow((state) => ({
      photoAlbums: state.photoAlbums,
      currentPhotoAlbumId: state.currentPhotoAlbumId,
      photoItems: state.photoItems,
      photoNextCursor: state.photoNextCursor,
      photoTotal: state.photoTotal,
      photoSelectionMode: state.photoSelectionMode,
      selectedPhotoIds: state.selectedPhotoIds,
      isLocalAccess: state.isLocalAccess,
      sidebarCollapsed: state.sidebarCollapsed,
      setPhotoAlbums: state.setPhotoAlbums,
      setPhotoItems: state.setPhotoItems,
      clearPhotoItems: state.clearPhotoItems,
      setPhotoSelectionMode: state.setPhotoSelectionMode,
      toggleSelectedPhoto: state.toggleSelectedPhoto,
      clearSelectedPhotos: state.clearSelectedPhotos,
      setPreviewPhoto: state.setPreviewPhoto,
      setTasks: state.setTasks,
      setActiveView: state.setActiveView,
      setCurrentPhotoAlbum: state.setCurrentPhotoAlbum,
    })),
  );

  const currentAlbum = photoAlbums.find((album) => album.id === currentPhotoAlbumId) ?? null;

  useEffect(() => {
    const handleResize = () => {
      if (hasCustomGridColumns.current) {
        setGridColumns((current) => clampGridColumns(current));
        return;
      }
      setGridColumns(getDefaultGridColumns());
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const refreshAlbums = useCallback(async () => {
    const response = await fetchPhotoAlbums();
    setPhotoAlbums(response.albums);
  }, [setPhotoAlbums]);

  const loadPhotos = useCallback(async (cursor: string | null, append: boolean) => {
    if (!currentPhotoAlbumId) {
      clearPhotoItems();
      return;
    }

    try {
      if (append) {
        setIsLoadingMore(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      const response = await fetchPhotoAlbumPhotos(currentPhotoAlbumId, cursor, 60, sort);
      setPhotoItems(response.items, response.next_cursor, response.total, append);
      if (response.error) {
        setError(response.error);
      }
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : t('photoLoadFailed');
      setError(message);
      if (!append) {
        clearPhotoItems();
      }
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, [clearPhotoItems, currentPhotoAlbumId, setPhotoItems, sort, t]);

  useEffect(() => {
    void loadPhotos(null, false);
  }, [loadPhotos]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el || !photoNextCursor || isLoadingMore || isLoading) {
      return;
    }

    const remaining = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (remaining < 700) {
      void loadPhotos(photoNextCursor, true);
    }
  }, [isLoading, isLoadingMore, loadPhotos, photoNextCursor]);

  const submitAlbumPath = useCallback(async (selectedPath: string) => {
    if (!selectedPath.trim() || isAddingAlbum) {
      return;
    }

    try {
      setIsAddingAlbum(true);
      setNotice(null);
      const result = await addPhotoAlbum({ path: selectedPath.trim(), recursive: true });
      await refreshAlbums();
      setCurrentPhotoAlbum(result.album.id);
      setPathDialogOpen(false);
    } catch (addError) {
      const message = addError instanceof Error ? addError.message : t('photoAlbumAddFailed');
      setNotice({ tone: 'error', message });
    } finally {
      setIsAddingAlbum(false);
    }
  }, [isAddingAlbum, refreshAlbums, setCurrentPhotoAlbum, t]);

  const handleAddAlbum = useCallback(async () => {
    if (!isLocalAccess) {
      return;
    }

    let selectedPath: string | undefined;
    try {
      const result = await browseFolder(t('photoSelectFolder'));
      if (result.success && result.path) {
        selectedPath = result.path;
      }
    } catch {
      // Fall back to manual path input.
    }

    if (!selectedPath) {
      setPathDialogOpen(true);
      return;
    }

    void submitAlbumPath(selectedPath);
  }, [isLocalAccess, submitAlbumPath, t]);

  const handleRefresh = useCallback(async () => {
    await refreshAlbums();
    await loadPhotos(null, false);
  }, [loadPhotos, refreshAlbums]);

  const handleSortChange = useCallback((nextSort: string) => {
    setSort(nextSort);
    scrollRef.current?.scrollTo({ top: 0 });
  }, []);

  const handleGridColumnsChange = useCallback((nextColumns: number) => {
    hasCustomGridColumns.current = true;
    setGridColumns(clampGridColumns(nextColumns));
  }, []);

  const handleGridTouchStart = useCallback((event: React.TouchEvent<HTMLDivElement>) => {
    if (event.touches.length === 2) {
      pinchRef.current = {
        distance: getTouchDistance(event.touches),
        columns: gridColumns,
      };
    }
  }, [gridColumns]);

  const handleGridTouchMove = useCallback((event: React.TouchEvent<HTMLDivElement>) => {
    if (!pinchRef.current || event.touches.length !== 2) {
      return;
    }

    event.preventDefault();
    const distance = getTouchDistance(event.touches);
    const delta = distance - pinchRef.current.distance;
    if (Math.abs(delta) < 34) {
      return;
    }

    const nextColumns = delta > 0
      ? pinchRef.current.columns - 1
      : pinchRef.current.columns + 1;
    const clampedColumns = clampGridColumns(nextColumns);
    hasCustomGridColumns.current = true;
    setGridColumns(clampedColumns);
    pinchRef.current = {
      distance,
      columns: clampedColumns,
    };
  }, []);

  const handleGridTouchEnd = useCallback(() => {
    pinchRef.current = null;
  }, []);

  const convertPhotos = useCallback(async (photos: PhotoItem[]) => {
    if (photos.length === 0 || isConverting) {
      return;
    }

    try {
      setIsConverting(true);
      const result = await convertPhotosToModels(photos.map((photo) => photo.id));
      if (result.tasks?.length) {
        setTasks(result.tasks, true);
      }
      clearSelectedPhotos();
      const failedCount = result.failed?.length ?? 0;
      const queuedCount = result.tasks?.length ?? 0;
      setNotice({
        tone: failedCount > 0 ? 'error' : 'success',
        message: failedCount > 0
          ? t('photoConvertPartial', { success: queuedCount, failed: failedCount })
          : t('photoConvertQueued', { count: queuedCount }),
      });
      if (queuedCount > 0 && failedCount === 0) {
        setActiveView('models');
      }
    } catch (convertError) {
      const message = convertError instanceof Error ? convertError.message : t('photoConvertFailed');
      setNotice({ tone: 'error', message });
    } finally {
      setIsConverting(false);
    }
  }, [clearSelectedPhotos, isConverting, setActiveView, setTasks, t]);

  const handleConvertSelected = useCallback(() => {
    const selected = photoItems.filter((photo) => selectedPhotoIds.includes(photo.id));
    void convertPhotos(selected);
  }, [convertPhotos, photoItems, selectedPhotoIds]);

  const handleConvertOne = useCallback((photo: PhotoItem) => {
    void convertPhotos([photo]);
  }, [convertPhotos]);

  return (
    <div className={styles.root}>
      <div className={styles.backdrop} />
      <div
        ref={scrollRef}
        className={[
          styles.scrollArea,
          !sidebarCollapsed ? styles.scrollAreaWithSidebar : '',
        ].filter(Boolean).join(' ')}
        onScroll={handleScroll}
        onTouchStart={handleGridTouchStart}
        onTouchMove={handleGridTouchMove}
        onTouchEnd={handleGridTouchEnd}
        onTouchCancel={handleGridTouchEnd}
      >
        <PhotoToolbar
          album={currentAlbum}
          total={photoTotal}
          sort={sort}
          selectionMode={photoSelectionMode}
          selectedCount={selectedPhotoIds.length}
          gridColumns={gridColumns}
          isLocalAccess={isLocalAccess}
          isLoading={isLoading}
          onAddAlbum={handleAddAlbum}
          onRefresh={handleRefresh}
          onSortChange={handleSortChange}
          onGridColumnsChange={handleGridColumnsChange}
          onToggleSelection={() => setPhotoSelectionMode(!photoSelectionMode)}
          onConvertSelected={handleConvertSelected}
        />

        {notice ? (
          <div className={[styles.notice, styles[notice.tone]].join(' ')}>
            <span>{notice.message}</span>
            <button
              onClick={() => setNotice(null)}
              type="button"
              title={t('close')}
              aria-label={t('close')}
            >
              <CloseIcon width={14} height={14} />
            </button>
          </div>
        ) : null}

        {error ? <div className={styles.error}>{error}</div> : null}

        <PhotoMasonryGrid
          items={photoItems}
          isLoading={isLoading || isLoadingMore}
          selectionMode={photoSelectionMode}
          selectedPhotoIds={selectedPhotoIds}
          columns={gridColumns}
          onOpenPhoto={setPreviewPhoto}
          onTogglePhoto={toggleSelectedPhoto}
          onConvertPhoto={handleConvertOne}
        />
      </div>

      <PhotoSelectionBar
        selectedCount={selectedPhotoIds.length}
        isConverting={isConverting}
        onConvert={handleConvertSelected}
        onClear={clearSelectedPhotos}
      />

      <TextInputDialog
        isOpen={pathDialogOpen}
        title={t('photoAddAlbum')}
        label={t('photoPathPrompt')}
        placeholder={t('photoPathPlaceholder')}
        confirmLabel={t('photoAddAlbum')}
        isBusy={isAddingAlbum}
        onSubmit={submitAlbumPath}
        onClose={() => setPathDialogOpen(false)}
      />
    </div>
  );
}
