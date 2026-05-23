import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';

import { useTranslation } from 'react-i18next';

import {
  CheckIcon,
  ChevronDownIcon,
  GridIcon,
  PlusIcon,
  ResetIcon,
  SparklesIcon,
} from '@/components/common/Icons';
import { SelectMenu } from '@/components/common/SelectMenu';
import type { PhotoAlbum } from '@/types';

import styles from './PhotoToolbar.module.css';

interface PhotoToolbarProps {
  album: PhotoAlbum | null;
  total: number;
  sort: string;
  selectionMode: boolean;
  selectedCount: number;
  gridColumns: number;
  isLocalAccess: boolean;
  isLoading: boolean;
  onAddAlbum: () => void;
  onRefresh: () => void;
  onSortChange: (sort: string) => void;
  onGridColumnsChange: (columns: number) => void;
  onToggleSelection: () => void;
  onConvertSelected: () => void;
}

export function PhotoToolbar({
  album,
  total,
  sort,
  selectionMode,
  selectedCount,
  gridColumns,
  isLocalAccess,
  isLoading,
  onAddAlbum,
  onRefresh,
  onSortChange,
  onGridColumnsChange,
  onToggleSelection,
  onConvertSelected,
}: PhotoToolbarProps) {
  const { t } = useTranslation();
  const densityControlRef = useRef<HTMLDivElement | null>(null);
  const [densityOpen, setDensityOpen] = useState(false);
  const sortOptions = [
    { value: 'mtime_desc', label: t('photoSortModifiedNewest') },
    { value: 'mtime_asc', label: t('photoSortModifiedOldest') },
    { value: 'ctime_desc', label: t('photoSortCreatedNewest') },
    { value: 'ctime_asc', label: t('photoSortCreatedOldest') },
    { value: 'name_asc', label: t('photoSortNameAsc') },
    { value: 'name_desc', label: t('photoSortNameDesc') },
    { value: 'size_desc', label: t('photoSortSizeDesc') },
    { value: 'size_asc', label: t('photoSortSizeAsc') },
  ];
  const densityOptions = [
    { value: '1', label: t('photoGridDensityPoster') },
    { value: '2', label: t('photoGridDensityLarge') },
    { value: '3', label: t('photoGridDensityComfort') },
    { value: '4', label: t('photoGridDensityStandard') },
    { value: '5', label: t('photoGridDensityCompact') },
    { value: '6', label: t('photoGridDensityDense') },
    { value: '7', label: t('photoGridDensityOverview') },
    { value: '8', label: t('photoGridDensityScan') },
  ];
  const currentDensity = densityOptions.find((option) => option.value === String(gridColumns)) ?? densityOptions[3];
  const densityProgress = `${((gridColumns - 1) / 7) * 100}%`;

  useEffect(() => {
    if (!densityOpen) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!densityControlRef.current?.contains(event.target as Node)) {
        setDensityOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDensityOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [densityOpen]);

  return (
    <header className={styles.toolbar}>
      <div className={styles.titleBlock}>
        <span className={styles.eyebrow}>{t('photoView')}</span>
        <h1>{album?.name ?? t('photoNoAlbumSelected')}</h1>
        <p>{album ? t('photoTotalCount', { count: total }) : t('photoChooseAlbumHint')}</p>
      </div>

      <div className={styles.actions}>
        <SelectMenu
          className={styles.sortMenu}
          value={sort}
          options={sortOptions}
          onChange={onSortChange}
          ariaLabel={t('photoSort')}
          compact
          disabled={!album}
        />

        <div ref={densityControlRef} className={styles.densityControl}>
          <button
            className={styles.densityTrigger}
            onClick={() => setDensityOpen((current) => !current)}
            disabled={!album}
            title={t('photoGridColumns')}
            aria-label={t('photoGridColumns')}
            aria-expanded={densityOpen}
            aria-haspopup="dialog"
            type="button"
          >
            <GridIcon width={14} height={14} />
            <ChevronDownIcon width={14} height={14} />
          </button>

          {densityOpen ? (
            <div className={styles.densityPopover} role="dialog" aria-label={t('photoGridColumns')}>
              <div className={styles.densityTitle}>{t('photoGridColumns')}</div>
              <div className={styles.densitySliderWrap}>
                <input
                  className={styles.densitySlider}
                  style={{ '--density-progress': densityProgress } as CSSProperties}
                  type="range"
                  min="1"
                  max="8"
                  step="1"
                  value={gridColumns}
                  aria-label={t('photoGridColumns')}
                  onChange={(event) => onGridColumnsChange(Number(event.target.value))}
                />
                <div className={styles.densityTicks} aria-hidden="true">
                  {densityOptions.map((option) => (
                    <span
                      key={option.value}
                      className={Number(option.value) <= gridColumns ? styles.densityTickActive : ''}
                    />
                  ))}
                </div>
              </div>
              <div className={styles.densityCurrent}>{currentDensity.label}</div>
            </div>
          ) : null}
        </div>

        <button
          className={styles.iconBtn}
          onClick={onRefresh}
          disabled={!album || isLoading}
          title={t('photoRefresh')}
          aria-label={t('photoRefresh')}
          type="button"
        >
          <ResetIcon width={16} height={16} />
        </button>

        <button
          className={[styles.textBtn, selectionMode ? styles.textBtnActive : ''].filter(Boolean).join(' ')}
          onClick={onToggleSelection}
          disabled={!album}
          type="button"
        >
          <CheckIcon width={15} height={15} />
          <span>{selectionMode ? t('photoDoneSelecting') : t('photoSelect')}</span>
        </button>

        <button
          className={styles.primaryBtn}
          onClick={selectedCount > 0 ? onConvertSelected : onToggleSelection}
          disabled={!album}
          type="button"
        >
          <SparklesIcon width={16} height={16} />
          <span>
            {selectedCount > 0
              ? t('photoConvertSelectedShort', { count: selectedCount })
              : t('photoConvertTo3d')}
          </span>
        </button>

        {isLocalAccess ? (
          <button className={styles.iconBtn} onClick={onAddAlbum} title={t('photoAddAlbum')} type="button">
            <PlusIcon width={16} height={16} />
          </button>
        ) : null}
      </div>
    </header>
  );
}
