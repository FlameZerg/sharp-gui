import { memo } from 'react';
import type { CSSProperties } from 'react';

import { useTranslation } from 'react-i18next';

import {
  CheckIcon,
  GalleryIcon,
  SparklesIcon,
} from '@/components/common/Icons';
import type { PhotoItem } from '@/types';

import styles from './PhotoMasonryGrid.module.css';

interface PhotoMasonryGridProps {
  items: PhotoItem[];
  isLoading: boolean;
  selectionMode: boolean;
  selectedPhotoIds: string[];
  columns: number;
  onOpenPhoto: (photo: PhotoItem) => void;
  onTogglePhoto: (photoId: string) => void;
  onConvertPhoto: (photo: PhotoItem) => void;
}

export const PhotoMasonryGrid = memo(function PhotoMasonryGrid({
  items,
  isLoading,
  selectionMode,
  selectedPhotoIds,
  columns,
  onOpenPhoto,
  onTogglePhoto,
  onConvertPhoto,
}: PhotoMasonryGridProps) {
  const { t } = useTranslation();

  if (!isLoading && items.length === 0) {
    return (
      <div className={styles.empty}>
        <GalleryIcon width={42} height={42} />
        <h2>{t('photoGridEmptyTitle')}</h2>
        <p>{t('photoGridEmptyHint')}</p>
      </div>
    );
  }

  const rootStyle = {
    '--photo-grid-columns': String(columns),
  } as CSSProperties;

  return (
    <div className={styles.root} style={rootStyle} aria-label={t('photoGrid')} role="list">
      {items.map((photo) => {
        const isSelected = selectedPhotoIds.includes(photo.id);
        const ratio = photo.width && photo.height
          ? `${photo.width} / ${photo.height}`
          : '4 / 3';

        return (
          <article
            key={photo.id}
            className={[
              styles.card,
              isSelected ? styles.selected : '',
            ].filter(Boolean).join(' ')}
            style={{ aspectRatio: ratio }}
            role="listitem"
          >
            <button
              className={styles.imageBtn}
              onClick={() => selectionMode ? onTogglePhoto(photo.id) : onOpenPhoto(photo)}
              type="button"
              aria-label={selectionMode ? t('photoToggleSelection', { name: photo.name }) : t('photoOpen', { name: photo.name })}
            >
              {photo.thumb_url ? (
                <img
                  src={photo.thumb_url}
                  alt={photo.name}
                  loading="lazy"
                  decoding="async"
                  draggable={false}
                />
              ) : (
                <span className={styles.fallback}>{t('galleryThumbUnavailableShort')}</span>
              )}
            </button>

            <div className={styles.topActions}>
              <button
                className={[
                  styles.selectBtn,
                  isSelected ? styles.selectBtnActive : '',
                ].filter(Boolean).join(' ')}
                onClick={() => onTogglePhoto(photo.id)}
                type="button"
                title={t('photoSelect')}
                aria-label={t('photoToggleSelection', { name: photo.name })}
              >
                {isSelected ? <CheckIcon width={14} height={14} /> : null}
              </button>
            </div>

            <div className={styles.footer}>
              <span>{photo.name}</span>
              <button
                className={styles.convertBtn}
                onClick={() => onConvertPhoto(photo)}
                type="button"
                title={t('photoConvertOne')}
                aria-label={t('photoConvertOne')}
              >
                <SparklesIcon width={14} height={14} />
              </button>
            </div>
          </article>
        );
      })}

      {isLoading ? (
        <div className={styles.skeleton} aria-hidden="true" />
      ) : null}
    </div>
  );
});

PhotoMasonryGrid.displayName = 'PhotoMasonryGrid';
