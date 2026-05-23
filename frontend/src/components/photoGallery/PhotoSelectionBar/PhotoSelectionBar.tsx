import { useTranslation } from 'react-i18next';

import { CloseIcon, SparklesIcon } from '@/components/common/Icons';

import styles from './PhotoSelectionBar.module.css';

interface PhotoSelectionBarProps {
  selectedCount: number;
  isConverting: boolean;
  onConvert: () => void;
  onClear: () => void;
}

export function PhotoSelectionBar({
  selectedCount,
  isConverting,
  onConvert,
  onClear,
}: PhotoSelectionBarProps) {
  const { t } = useTranslation();

  if (selectedCount === 0) {
    return null;
  }

  return (
    <div className={styles.bar} role="status" aria-live="polite">
      <span className={styles.count}>{t('photoSelectedCount', { count: selectedCount })}</span>
      <button
        className={styles.primaryBtn}
        onClick={onConvert}
        disabled={isConverting}
        type="button"
      >
        <SparklesIcon width={16} height={16} />
        <span>{isConverting ? t('converting') : t('photoConvertSelected')}</span>
      </button>
      <button className={styles.clearBtn} onClick={onClear} type="button" aria-label={t('photoClearSelection')}>
        <CloseIcon width={16} height={16} />
      </button>
    </div>
  );
}

