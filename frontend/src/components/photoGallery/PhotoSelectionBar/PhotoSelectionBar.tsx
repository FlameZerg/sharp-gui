import { useTranslation } from 'react-i18next';

import { CloseIcon, DownloadIcon, SparklesIcon } from '@/components/common/Icons';

import styles from './PhotoSelectionBar.module.css';

interface PhotoSelectionBarProps {
  selectedCount: number;
  convertCount: number;
  canConvert: boolean;
  isConverting: boolean;
  isDownloading: boolean;
  onConvert: () => void;
  onDownload: () => void;
  onClear: () => void;
}

export function PhotoSelectionBar({
  selectedCount,
  convertCount,
  canConvert,
  isConverting,
  isDownloading,
  onConvert,
  onDownload,
  onClear,
}: PhotoSelectionBarProps) {
  const { t } = useTranslation();

  if (selectedCount === 0) {
    return null;
  }

  return (
    <div className={styles.bar} role="status" aria-live="polite">
      <span className={styles.count} aria-label={t('photoSelectedCount', { count: selectedCount })}>
        <strong>{selectedCount}</strong>
        <span>{t('photoSelectedLabel')}</span>
      </span>
      <button
        className={styles.primaryBtn}
        onClick={onConvert}
        disabled={isConverting || !canConvert}
        title={canConvert ? t('photoConvertSelected') : t('photoConvertPhotosOnly')}
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
      <button
        className={styles.iconBtn}
        onClick={onDownload}
        disabled={isDownloading}
        type="button"
        title={isDownloading ? t('photoDownloadingSelected') : t('photoDownloadSelected')}
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
