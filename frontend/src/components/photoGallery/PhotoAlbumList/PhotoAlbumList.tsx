import { useCallback, useState } from 'react';

import { useTranslation } from 'react-i18next';
import { useShallow } from 'zustand/react/shallow';

import {
  addPhotoAlbum,
  browseFolder,
  deletePhotoAlbum,
  fetchPhotoAlbums,
  rescanPhotoAlbum,
} from '@/api';
import {
  CheckIcon,
  CloseIcon,
  DeleteIcon,
  FolderIcon,
  PlusIcon,
  ResetIcon,
} from '@/components/common/Icons';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { TextInputDialog } from '@/components/common/TextInputDialog';
import { useAppStore } from '@/store';
import type { PhotoAlbum } from '@/types';

import styles from './PhotoAlbumList.module.css';

export function PhotoAlbumList() {
  const { t } = useTranslation();
  const [isBusy, setIsBusy] = useState(false);
  const [pathDialogOpen, setPathDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<PhotoAlbum | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const {
    photoAlbums,
    currentPhotoAlbumId,
    isLocalAccess,
    setPhotoAlbums,
    setCurrentPhotoAlbum,
  } = useAppStore(
    useShallow((state) => ({
      photoAlbums: state.photoAlbums,
      currentPhotoAlbumId: state.currentPhotoAlbumId,
      isLocalAccess: state.isLocalAccess,
      setPhotoAlbums: state.setPhotoAlbums,
      setCurrentPhotoAlbum: state.setCurrentPhotoAlbum,
    })),
  );

  const refreshAlbums = useCallback(async () => {
    const response = await fetchPhotoAlbums();
    setPhotoAlbums(response.albums);
  }, [setPhotoAlbums]);

  const submitAlbumPath = useCallback(async (selectedPath: string) => {
    if (!selectedPath.trim() || isBusy) {
      return;
    }

    try {
      setIsBusy(true);
      setMessage(null);
      const result = await addPhotoAlbum({ path: selectedPath.trim(), recursive: true });
      if (result.success) {
        await refreshAlbums();
        setCurrentPhotoAlbum(result.album.id);
        setPathDialogOpen(false);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('photoAlbumAddFailed');
      setMessage(errorMessage);
    } finally {
      setIsBusy(false);
    }
  }, [isBusy, refreshAlbums, setCurrentPhotoAlbum, t]);

  const handleAddAlbum = useCallback(async () => {
    if (!isLocalAccess || isBusy) {
      return;
    }

    try {
      setIsBusy(true);
      setMessage(null);
      let selectedPath: string | undefined;

      try {
        const result = await browseFolder(t('photoSelectFolder'));
        if (result.success && result.path) {
          selectedPath = result.path;
        }
      } catch {
        // Fall back to manual path input below.
      }

      if (!selectedPath) {
        setPathDialogOpen(true);
        return;
      }

      await submitAlbumPath(selectedPath);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('photoAlbumAddFailed');
      setMessage(errorMessage);
    } finally {
      setIsBusy(false);
    }
  }, [isBusy, isLocalAccess, submitAlbumPath, t]);

  const handleDeleteAlbum = useCallback(async (
    event: React.MouseEvent<HTMLButtonElement>,
    album: PhotoAlbum,
  ) => {
    event.stopPropagation();
    setDeleteTarget(album);
  }, []);

  const confirmDeleteAlbum = useCallback(async () => {
    if (!deleteTarget) {
      return;
    }

    try {
      setIsBusy(true);
      setMessage(null);
      await deletePhotoAlbum(deleteTarget.id);
      await refreshAlbums();
      setDeleteTarget(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('photoAlbumDeleteFailed');
      setMessage(errorMessage);
    } finally {
      setIsBusy(false);
    }
  }, [deleteTarget, refreshAlbums, t]);

  const handleRescanAlbum = useCallback(async (
    event: React.MouseEvent<HTMLButtonElement>,
    album: PhotoAlbum,
  ) => {
    event.stopPropagation();
    try {
      setIsBusy(true);
      setMessage(null);
      const result = await rescanPhotoAlbum(album.id);
      if (result.success) {
        await refreshAlbums();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('photoAlbumScanFailed');
      setMessage(errorMessage);
    } finally {
      setIsBusy(false);
    }
  }, [refreshAlbums, t]);

  const handleAlbumKeyDown = useCallback((
    event: React.KeyboardEvent<HTMLDivElement>,
    albumId: string,
  ) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setCurrentPhotoAlbum(albumId);
    }
  }, [setCurrentPhotoAlbum]);

  return (
    <section className={styles.root} aria-label={t('photoAlbums')}>
      <div className={styles.header}>
        <div>
          <h2>{t('photoAlbums')}</h2>
          <p>{t('photoAlbumsHint')}</p>
        </div>
        <button
          className={styles.addBtn}
          onClick={handleAddAlbum}
          disabled={!isLocalAccess || isBusy}
          title={isLocalAccess ? t('photoAddAlbum') : t('photoLocalOnly')}
          aria-label={t('photoAddAlbum')}
          type="button"
        >
          <PlusIcon width={16} height={16} />
        </button>
      </div>

      {message ? (
        <div className={styles.notice}>
          <span>{message}</span>
          <button
            onClick={() => setMessage(null)}
            type="button"
            title={t('close')}
            aria-label={t('close')}
          >
            <CloseIcon width={13} height={13} />
          </button>
        </div>
      ) : null}

      {photoAlbums.length === 0 ? (
        <div className={styles.empty}>
          <FolderIcon width={28} height={28} />
          <p>{isLocalAccess ? t('photoNoAlbums') : t('photoNoAlbumsRemote')}</p>
          {isLocalAccess ? (
            <button className={styles.emptyBtn} onClick={handleAddAlbum} type="button">
              {t('photoAddAlbum')}
            </button>
          ) : null}
        </div>
      ) : (
        <div className={styles.list}>
          {photoAlbums.map((album) => {
            const isActive = album.id === currentPhotoAlbumId;
            return (
              <div
                key={album.id}
                className={[
                  styles.album,
                  isActive ? styles.albumActive : '',
                  album.scan_status === 'error' ? styles.albumError : '',
                ].filter(Boolean).join(' ')}
                onClick={() => setCurrentPhotoAlbum(album.id)}
                onKeyDown={(event) => handleAlbumKeyDown(event, album.id)}
                role="button"
                tabIndex={0}
                aria-current={isActive ? 'true' : undefined}
              >
                <div className={styles.cover}>
                  {album.cover_thumb_url ? (
                    <img src={album.cover_thumb_url} alt="" loading="lazy" decoding="async" />
                  ) : (
                    <FolderIcon width={22} height={22} />
                  )}
                </div>

                <div className={styles.info}>
                  <span className={styles.name}>{album.name}</span>
                  <span className={styles.meta}>
                    {album.scan_status === 'error'
                      ? t('photoAlbumUnavailable')
                      : t('photoCount', { count: album.photo_count ?? 0 })}
                  </span>
                </div>

                {isActive ? <CheckIcon className={styles.activeIcon} width={15} height={15} /> : null}

                {isLocalAccess ? (
                  <span className={styles.actions}>
                    <button
                      className={styles.iconBtn}
                      onClick={(event) => handleRescanAlbum(event, album)}
                      title={t('photoRescanAlbum')}
                      aria-label={t('photoRescanAlbum')}
                      type="button"
                    >
                      <ResetIcon width={13} height={13} />
                    </button>
                    <button
                      className={[styles.iconBtn, styles.deleteBtn].join(' ')}
                      onClick={(event) => handleDeleteAlbum(event, album)}
                      title={t('photoRemoveAlbum')}
                      aria-label={t('photoRemoveAlbum')}
                      type="button"
                    >
                      <DeleteIcon width={13} height={13} />
                    </button>
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      <TextInputDialog
        isOpen={pathDialogOpen}
        title={t('photoAddAlbum')}
        label={t('photoPathPrompt')}
        placeholder={t('photoPathPlaceholder')}
        confirmLabel={t('photoAddAlbum')}
        isBusy={isBusy}
        onSubmit={submitAlbumPath}
        onClose={() => setPathDialogOpen(false)}
      />

      <ConfirmDialog
        isOpen={Boolean(deleteTarget)}
        title={t('photoRemoveAlbum')}
        message={deleteTarget ? t('photoAlbumDeleteConfirm', {
          name: deleteTarget.name,
        }) : ''}
        confirmLabel={t('photoRemoveAlbum')}
        isBusy={isBusy}
        danger
        onConfirm={confirmDeleteAlbum}
        onClose={() => setDeleteTarget(null)}
      />
    </section>
  );
}
