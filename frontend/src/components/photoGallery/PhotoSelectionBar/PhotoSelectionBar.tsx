import { useTranslation } from 'react-i18next';

import { CloseIcon, DownloadIcon, SparklesIcon } from '@/components/common/Icons';

import styles from './PhotoSelectionBar.module.css';

interface PhotoSelectionBarProps {
  selectedCount: number;
  convertCount: number;
  videoCount: number;
  canConvert: boolean;
  canReconstructVideo: boolean;
  isConverting: boolean;
  isDownloading: boolean;
  onConvert: () => void;
  onReconstructVideo: () => void;
  onDownload: () => void;
  onClear: () => void;
}

export function PhotoSelectionBar({
  selectedCount,
  convertCount,
  videoCount,
  canConvert,
  canReconstructVideo,
  isConverting,
  isDownloading,
  onConvert,
  onReconstructVideo,
  onDownload,
  onClear,
}: PhotoSelectionBarProps) {
  const { t } = useTranslation();

  if (selectedCount === 0) {
    return null;
  }

  return (
    <div
      className={[styles.bar, videoCount > 0 ? styles.withVideo : ''].filter(Boolean).join(' ')}
      role="status"
      aria-live="polite"
    >
      <span className={styles.count} aria-label={t('photoSelectedCount', { count: selectedCount })}>
        <strong>{selectedCount}</strong>
        <span>{t('photoSelectedLabel')}</span>
      </span>
      <button
        className={styles.primaryBtn}
        onClick={onConvert}
        disabled={isConverting || !canConvert}
        data-tooltip={canConvert ? t('photoConvertSelected') : t('photoConvertPhotosOnly')}
        type="button"
      >
        <SparklesIcon width={16} height={16} />
        <span>
          {isConverting
            ? t('converting')
            : canConvert
              ? t('photoConvertSelectedShort', { count: convertCount })
              : t('photoConvertPhotosOnly')}
        </span>
      </button>
      {videoCount > 0 ? (
        <button
          className={styles.primaryBtn}
          onClick={onReconstructVideo}
          disabled={isConverting || !canReconstructVideo}
          data-tooltip={canReconstructVideo ? t('videoReconGenerate3d') : t('videoReconSingleVideoOnly')}
          type="button"
        >
          <SparklesIcon width={16} height={16} />
          <span>
            {canReconstructVideo
              ? t('videoReconGenerate3d')
              : t('videoReconSingleVideoOnly')}
          </span>
        </button>
      ) : null}
      <button
        className={styles.iconBtn}
        onClick={onDownload}
        disabled={isDownloading}
        type="button"
        data-tooltip={isDownloading ? t('photoDownloadingSelected') : t('photoDownloadSelected')}
        aria-label={isDownloading ? t('photoDownloadingSelected') : t('photoDownloadSelected')}
      >
        <DownloadIcon width={16} height={16} />
      </button>
      <button className={styles.clearBtn} onClick={onClear} type="button" aria-label={t('photoClearSelection')}>
        <CloseIcon width={16} height={16} />
      </button>
    </div>
  );
}
