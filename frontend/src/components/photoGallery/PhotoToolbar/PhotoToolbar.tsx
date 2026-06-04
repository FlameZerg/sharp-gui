import { useEffect, useRef, useState } from 'react';
import type { CSSProperties, DragEvent } from 'react';

import { useTranslation } from 'react-i18next';

import {
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CloudUploadIcon,
  GridIcon,
  PlusIcon,
  ResetIcon,
  SortIcon,
  SparklesIcon,
} from '@/components/common/Icons';
import { SelectMenu } from '@/components/common/SelectMenu';
import type { PhotoAlbum } from '@/types';

import styles from './PhotoToolbar.module.css';

export type PhotoToolbarMode = 'expanded' | 'compact' | 'mini';

interface PhotoToolbarProps {
  album: PhotoAlbum | null;
  total: number;
  sort: string;
  selectionMode: boolean;
  selectedCount: number;
  gridColumns: number;
  isLocalAccess: boolean;
  isLoading: boolean;
  canUploadPhotos: boolean;
  isUploadingPhotos: boolean;
  uploadingPhotoCount: number;
  mode: PhotoToolbarMode;
  onAddAlbum: () => void;
  onUploadPhotos: (files: FileList | File[]) => Promise<void> | void;
  onRefresh: () => void;
  onSortChange: (sort: string) => void;
  onGridColumnsChange: (columns: number) => void;
  onToggleSelection: () => void;
  onConvertSelected: () => void;
  onRequestExpand: () => void;
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
  canUploadPhotos,
  isUploadingPhotos,
  uploadingPhotoCount,
  mode,
  onAddAlbum,
  onUploadPhotos,
  onRefresh,
  onSortChange,
  onGridColumnsChange,
  onToggleSelection,
  onConvertSelected,
  onRequestExpand,
}: PhotoToolbarProps) {
  const { t } = useTranslation();
  const densityControlRef = useRef<HTMLDivElement | null>(null);
  const uploadControlRef = useRef<HTMLDivElement | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const [densityOpen, setDensityOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [isUploadDragActive, setIsUploadDragActive] = useState(false);
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
  const title = album?.name ?? t('photoNoAlbumSelected');
  const subtitle = album ? t('photoTotalCount', { count: total }) : t('photoChooseAlbumHint');
  const compactTitle = album ? `${album.name} · ${total}` : t('photoNoAlbumSelected');
  const uploadDisabled = !album || !canUploadPhotos || isUploadingPhotos;

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

  useEffect(() => {
    if (!uploadOpen) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!uploadControlRef.current?.contains(event.target as Node)) {
        setUploadOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setUploadOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [uploadOpen]);

  const handleUploadFiles = (files: FileList | File[] | null) => {
    if (!files || files.length === 0 || uploadDisabled) {
      return;
    }

    void Promise.resolve(onUploadPhotos(files)).finally(() => {
      setUploadOpen(false);
      setIsUploadDragActive(false);
      if (uploadInputRef.current) {
        uploadInputRef.current.value = '';
      }
    });
  };

  const handleUploadDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsUploadDragActive(false);
    handleUploadFiles(event.dataTransfer.files);
  };

  return (
    <header className={[styles.toolbar, styles[mode]].filter(Boolean).join(' ')}>
      <button
        className={styles.miniHandle}
        onClick={onRequestExpand}
        type="button"
        title={t('photoExpandToolbar')}
        aria-label={t('photoExpandToolbar')}
      >
        <ChevronUpIcon width={18} height={18} />
      </button>
      <div className={styles.titleBlock}>
        <span className={styles.eyebrow}>{t('photoView')}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
        <span className={styles.compactTitle}>{compactTitle}</span>
      </div>

      <div className={styles.actions}>
        <SelectMenu
          className={styles.sortMenu}
          value={sort}
          options={sortOptions}
          onChange={onSortChange}
          ariaLabel={t('photoSort')}
          icon={<SortIcon width={14} height={14} />}
          compact
          showSelectedLabel={mode === 'expanded'}
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
          className={[styles.iconBtn, styles.refreshBtn].join(' ')}
          onClick={onRefresh}
          disabled={!album || isLoading}
          title={t('photoRefresh')}
          aria-label={t('photoRefresh')}
          type="button"
        >
          <ResetIcon width={16} height={16} />
        </button>

        {canUploadPhotos ? (
          <div ref={uploadControlRef} className={styles.uploadControl}>
            <button
              className={[
                styles.textBtn,
                styles.uploadBtn,
                uploadOpen ? styles.textBtnActive : '',
              ].filter(Boolean).join(' ')}
              onClick={() => setUploadOpen((current) => !current)}
              disabled={uploadDisabled}
              title={t('photoUpload')}
              aria-label={t('photoUpload')}
              aria-expanded={uploadOpen}
              aria-haspopup="dialog"
              type="button"
            >
              <CloudUploadIcon width={15} height={15} />
              <span className={styles.uploadLabel}>
                {isUploadingPhotos ? t('photoUploading') : t('photoUpload')}
              </span>
            </button>

            <input
              ref={uploadInputRef}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(event) => handleUploadFiles(event.target.files)}
            />

            {uploadOpen ? (
              <div className={styles.uploadPopover} role="dialog" aria-label={t('photoUpload')}>
                <div
                  className={[
                    styles.uploadDrop,
                    isUploadDragActive ? styles.uploadDropActive : '',
                  ].filter(Boolean).join(' ')}
                  onDragEnter={(event) => {
                    event.preventDefault();
                    setIsUploadDragActive(true);
                  }}
                  onDragOver={(event) => {
                    event.preventDefault();
                    setIsUploadDragActive(true);
                  }}
                  onDragLeave={() => setIsUploadDragActive(false)}
                  onDrop={handleUploadDrop}
                >
                  <CloudUploadIcon width={22} height={22} />
                  <span>{t('photoUploadDropTitle')}</span>
                  <button
                    className={styles.uploadBrowseBtn}
                    onClick={() => uploadInputRef.current?.click()}
                    type="button"
                  >
                    {t('photoUploadChooseFiles')}
                  </button>
                </div>

                {isUploadingPhotos ? (
                  <div className={styles.uploadStatus} role="status" aria-live="polite">
                    <span>{t('photoUploadPendingCount', { count: uploadingPhotoCount })}</span>
                    <div className={styles.uploadProgress} />
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        <button
          className={[
            styles.textBtn,
            styles.selectAction,
            selectionMode ? styles.textBtnActive : '',
          ].filter(Boolean).join(' ')}
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
          <span className={styles.primaryLabel}>
            {selectedCount > 0
              ? t('photoConvertSelectedShort', { count: selectedCount })
              : t('photoConvertTo3d')}
          </span>
          <span className={styles.primaryShortLabel}>3D</span>
        </button>

        {isLocalAccess ? (
          <button className={[styles.iconBtn, styles.addBtn].join(' ')} onClick={onAddAlbum} title={t('photoAddAlbum')} type="button">
            <PlusIcon width={16} height={16} />
          </button>
        ) : null}
      </div>
    </header>
  );
}
