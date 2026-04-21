import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import * as Icons from '@/components/common/Icons';
import { useAppStore } from '@/store';
import styles from './QuickControls.module.css';

interface QuickControlsProps {
  isInXr: boolean;
}

function toDegrees(radians: number): number {
  return (radians * 180) / Math.PI;
}

function toRadians(degrees: number): number {
  return (degrees * Math.PI) / 180;
}

function formatValue(value: number, fractionDigits = 2): string {
  return value.toFixed(fractionDigits);
}

export function QuickControls({ isInXr }: QuickControlsProps) {
  const { t } = useTranslation();
  const {
    currentModelUrl,
    quickControlsOpen,
    setQuickControlsOpen,
    toggleQuickControls,
    viewerTransformDraft,
    viewerInteractionDraft,
    setViewerTransformDraft,
    applyViewerTransformDraft,
    setViewerInteractionDraft,
    applyViewerInteractionDraft,
    applyOrientationPreset,
    resetViewerQuickControlsForCurrentModel,
  } = useAppStore();

  const hasActiveModel = Boolean(currentModelUrl);
  const controlsDisabled = !hasActiveModel || isInXr;
  const disabledHint = !hasActiveModel
    ? t('quickControlsNoModelHint')
    : isInXr
      ? t('quickControlsXrHint')
      : '';

  useEffect(() => {
    if (!hasActiveModel && quickControlsOpen) {
      setQuickControlsOpen(false);
    }
  }, [hasActiveModel, quickControlsOpen, setQuickControlsOpen]);

  useEffect(() => {
    if (!quickControlsOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setQuickControlsOpen(false);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [quickControlsOpen, setQuickControlsOpen]);

  const updateTransform = (patch: Partial<typeof viewerTransformDraft>) => {
    setViewerTransformDraft(patch);
    applyViewerTransformDraft();
  };

  const updateInteraction = (patch: Partial<typeof viewerInteractionDraft>) => {
    setViewerInteractionDraft(patch);
    applyViewerInteractionDraft();
  };

  const handlePreset = (preset: 'default' | 'openCv' | 'openGl' | 'zUp' | 'flipUpsideDown') => {
    applyOrientationPreset(preset);
  };

  return (
    <div className={styles.root}>
      <button
        className={styles.trigger}
        type="button"
        onClick={toggleQuickControls}
        title={quickControlsOpen ? t('quickControlsClose') : t('quickControlsOpen')}
        aria-label={quickControlsOpen ? t('quickControlsCloseAria') : t('quickControlsOpenAria')}
        aria-expanded={quickControlsOpen}
      >
        <Icons.SettingsIcon />
      </button>

      <section
        className={`${styles.panel} ${quickControlsOpen ? styles.panelOpen : ''}`}
        aria-hidden={!quickControlsOpen}
      >
        <header className={styles.panelHeader}>
          <h4>{t('quickControlsTitle')}</h4>
          <button
            className={styles.resetBtn}
            type="button"
            onClick={resetViewerQuickControlsForCurrentModel}
            disabled={controlsDisabled}
          >
            <Icons.ResetIcon />
            <span>{t('quickControlsResetAll')}</span>
          </button>
        </header>

        {controlsDisabled && (
          <p className={styles.disabledHint}>{disabledHint}</p>
        )}

        <div className={styles.section}>
          <div className={styles.sectionTitle}>{t('quickControlsTransform')}</div>

          <div className={styles.presetGrid}>
            <button type="button" className={styles.presetBtn} onClick={() => handlePreset('default')} disabled={controlsDisabled}>
              {t('quickControlsPresetDefault')}
            </button>
            <button type="button" className={styles.presetBtn} onClick={() => handlePreset('flipUpsideDown')} disabled={controlsDisabled}>
              {t('quickControlsPresetUpsideDown')}
            </button>
            <button type="button" className={styles.presetBtn} onClick={() => handlePreset('openGl')} disabled={controlsDisabled}>
              {t('quickControlsPresetOpenGl')}
            </button>
            <button type="button" className={styles.presetBtn} onClick={() => handlePreset('zUp')} disabled={controlsDisabled}>
              {t('quickControlsPresetZUp')}
            </button>
          </div>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t('quickControlsScale')}</span>
            <input
              type="range"
              min="0.2"
              max="8"
              step="0.01"
              value={viewerTransformDraft.scale}
              onChange={(event) => updateTransform({ scale: Number(event.target.value) })}
              disabled={controlsDisabled}
            />
            <span className={styles.fieldValue}>{formatValue(viewerTransformDraft.scale)}</span>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t('quickControlsPosX')}</span>
            <input
              type="range"
              min="-5"
              max="5"
              step="0.01"
              value={viewerTransformDraft.positionX}
              onChange={(event) => updateTransform({ positionX: Number(event.target.value) })}
              disabled={controlsDisabled}
            />
            <span className={styles.fieldValue}>{formatValue(viewerTransformDraft.positionX)}</span>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t('quickControlsPosY')}</span>
            <input
              type="range"
              min="-5"
              max="5"
              step="0.01"
              value={viewerTransformDraft.positionY}
              onChange={(event) => updateTransform({ positionY: Number(event.target.value) })}
              disabled={controlsDisabled}
            />
            <span className={styles.fieldValue}>{formatValue(viewerTransformDraft.positionY)}</span>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t('quickControlsPosZ')}</span>
            <input
              type="range"
              min="-5"
              max="5"
              step="0.01"
              value={viewerTransformDraft.positionZ}
              onChange={(event) => updateTransform({ positionZ: Number(event.target.value) })}
              disabled={controlsDisabled}
            />
            <span className={styles.fieldValue}>{formatValue(viewerTransformDraft.positionZ)}</span>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t('quickControlsRotX')}</span>
            <input
              type="range"
              min="-180"
              max="180"
              step="1"
              value={toDegrees(viewerTransformDraft.rotationX)}
              onChange={(event) => updateTransform({ rotationX: toRadians(Number(event.target.value)) })}
              disabled={controlsDisabled}
            />
            <span className={styles.fieldValue}>{formatValue(toDegrees(viewerTransformDraft.rotationX), 0)}°</span>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t('quickControlsRotY')}</span>
            <input
              type="range"
              min="-180"
              max="180"
              step="1"
              value={toDegrees(viewerTransformDraft.rotationY)}
              onChange={(event) => updateTransform({ rotationY: toRadians(Number(event.target.value)) })}
              disabled={controlsDisabled}
            />
            <span className={styles.fieldValue}>{formatValue(toDegrees(viewerTransformDraft.rotationY), 0)}°</span>
          </label>

          <label className={styles.field}>
            <span className={styles.fieldLabel}>{t('quickControlsRotZ')}</span>
            <input
              type="range"
              min="-180"
              max="180"
              step="1"
              value={toDegrees(viewerTransformDraft.rotationZ)}
              onChange={(event) => updateTransform({ rotationZ: toRadians(Number(event.target.value)) })}
              disabled={controlsDisabled}
            />
            <span className={styles.fieldValue}>{formatValue(toDegrees(viewerTransformDraft.rotationZ), 0)}°</span>
          </label>
        </div>

        <div className={styles.section}>
          <div className={styles.sectionTitle}>{t('quickControlsInteraction')}</div>

          <label className={styles.toggleField}>
            <input
              type="checkbox"
              checked={viewerInteractionDraft.reversePointerDirection}
              onChange={(event) => updateInteraction({ reversePointerDirection: event.target.checked })}
              disabled={controlsDisabled}
            />
            <span>{t('quickControlsReversePointer')}</span>
          </label>

          <label className={styles.toggleField}>
            <input
              type="checkbox"
              checked={viewerInteractionDraft.reversePointerSlide}
              onChange={(event) => updateInteraction({ reversePointerSlide: event.target.checked })}
              disabled={controlsDisabled}
            />
            <span>{t('quickControlsReverseSlide')}</span>
          </label>
        </div>
      </section>
    </div>
  );
}
