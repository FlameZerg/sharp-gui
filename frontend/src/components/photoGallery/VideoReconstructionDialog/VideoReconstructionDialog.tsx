import { useEffect, useMemo, useState } from 'react';

import { useTranslation } from 'react-i18next';
import { useShallow } from 'zustand/react/shallow';

import { ApiError, createVideoReconstruction, fetchTasks, fetchVideoReconstructionStatus } from '@/api';
import { Button } from '@/components/common/Button';
import { ChevronDownIcon, SparklesIcon } from '@/components/common/Icons';
import { Modal } from '@/components/common/Modal';
import { useAppStore } from '@/store';
import type {
  VideoReconstructionEngine,
  VideoReconstructionMode,
  VideoReconstructionQuality,
} from '@/types';

import styles from './VideoReconstructionDialog.module.css';

const MAX_OUTPUT_NAME_LENGTH = 120;

const MODE_OPTIONS: VideoReconstructionMode[] = ['auto', 'object', 'environment'];
const QUALITY_OPTIONS: VideoReconstructionQuality[] = ['preview', 'high', 'extreme'];
const ENGINE_OPTIONS: VideoReconstructionEngine[] = ['auto', 'stable', 'experimental'];

function deriveOutputName(filename: string): string {
  const withoutExtension = filename.replace(/\.[^.]+$/, '');
  return Array.from(withoutExtension)
    .map((char) => (char.charCodeAt(0) < 32 || '<>:"/\\|?*'.includes(char) ? '_' : char))
    .join('')
    .trim()
    .slice(0, MAX_OUTPUT_NAME_LENGTH);
}

export function VideoReconstructionDialog() {
  const { t } = useTranslation();
  const {
    isOpen,
    target,
    dependencies,
    config,
    submitting,
    closeDialog,
    setStatus,
    setSubmitting,
    setTasks,
  } = useAppStore(
    useShallow((state) => ({
      isOpen: state.videoReconstructionDialogOpen,
      target: state.videoReconstructionTarget,
      dependencies: state.videoReconstructionDependencies,
      config: state.videoReconstructionConfig,
      submitting: state.videoReconstructionSubmitting,
      closeDialog: state.closeVideoReconstructionDialog,
      setStatus: state.setVideoReconstructionStatus,
      setSubmitting: state.setVideoReconstructionSubmitting,
      setTasks: state.setTasks,
    })),
  );
  const [mode, setMode] = useState<VideoReconstructionMode>('auto');
  const [quality, setQuality] = useState<VideoReconstructionQuality>('high');
  const [engine, setEngine] = useState<VideoReconstructionEngine>('auto');
  const [outputName, setOutputName] = useState('');
  const [keepIntermediateFiles, setKeepIntermediateFiles] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [message, setMessage] = useState<{ tone: 'error' | 'success' | 'warning'; text: string } | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !target) {
      return;
    }

    setMode('auto');
    setQuality(config.default_quality);
    setEngine(config.default_engine);
    setOutputName(deriveOutputName(target.name));
    setKeepIntermediateFiles(config.keep_intermediate_files);
    setAdvancedOpen(false);
    setMessage(null);
  }, [config.default_engine, config.default_quality, config.keep_intermediate_files, isOpen, target]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    let cancelled = false;
    setStatusLoading(true);
    void fetchVideoReconstructionStatus()
      .then((status) => {
        if (!cancelled) {
          setStatus(status.dependencies, status.config);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          const text = error instanceof Error ? error.message : t('videoReconStatusLoadFailed');
          setMessage({ tone: 'error', text });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setStatusLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, setStatus, t]);

  const stableAvailable = Boolean(dependencies?.summary.stable_available);
  const experimentalAvailable = Boolean(dependencies?.summary.experimental_available);
  const canSubmit = Boolean(target)
    && target?.media_type === 'video'
    && !submitting
    && stableAvailable
    && outputName.trim().length > 0
    && outputName.trim().length <= MAX_OUTPUT_NAME_LENGTH
    && !(engine === 'experimental' && !experimentalAvailable);

  const dependencyMessage = useMemo(() => {
    if (!dependencies) {
      return statusLoading ? t('videoReconCheckingDependencies') : null;
    }
    if (!dependencies.required.available) {
      return t('videoReconRequiredMissing');
    }
    if (!dependencies.stable.available) {
      return t('videoReconStableMissing');
    }
    if (!dependencies.experimental.available) {
      return t('videoReconExperimentalUnavailableStableOk');
    }
    return t('videoReconDependenciesReady');
  }, [dependencies, statusLoading, t]);

  const handleSubmit = async () => {
    if (!target || !canSubmit) {
      return;
    }

    setSubmitting(true);
    setMessage(null);
    try {
      const response = await createVideoReconstruction({
        video_id: target.id,
        mode,
        quality,
        engine,
        output_name: outputName.trim(),
        keep_intermediate_files: keepIntermediateFiles,
      });
      if (response.task) {
        const tasksResponse = await fetchTasks();
        setTasks(tasksResponse.tasks, tasksResponse.has_active);
      }
      setMessage({ tone: 'success', text: t('videoReconQueued') });
      window.setTimeout(() => closeDialog(), 260);
    } catch (error) {
      const text = error instanceof ApiError && error.data?.code
        ? t(`videoReconError.${error.data.code}`, { defaultValue: error.message })
        : error instanceof Error
          ? error.message
          : t('videoReconCreateFailed');
      setMessage({ tone: 'error', text });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={submitting ? () => undefined : closeDialog}
      title={t('videoReconDialogTitle')}
      size="lg"
    >
      <div className={styles.root}>
        <div className={styles.summary}>
          <SparklesIcon width={18} height={18} />
          <div>
            <strong>{target?.name ?? t('photoVideo')}</strong>
            <span>{dependencyMessage}</span>
          </div>
        </div>

        <fieldset className={styles.fieldset} disabled={submitting}>
          <label className={styles.label}>{t('videoReconModeLabel')}</label>
          <div className={styles.segmented}>
            {MODE_OPTIONS.map((option) => (
              <button
                key={option}
                className={[styles.segmentBtn, mode === option ? styles.segmentActive : ''].filter(Boolean).join(' ')}
                onClick={() => setMode(option)}
                type="button"
              >
                {t(`videoReconMode.${option}`)}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className={styles.fieldset} disabled={submitting}>
          <label className={styles.label}>{t('videoReconQualityLabel')}</label>
          <div className={styles.segmented}>
            {QUALITY_OPTIONS.map((option) => (
              <button
                key={option}
                className={[styles.segmentBtn, quality === option ? styles.segmentActive : ''].filter(Boolean).join(' ')}
                onClick={() => setQuality(option)}
                type="button"
              >
                <span>{t(`videoReconQuality.${option}`)}</span>
                {config.default_quality === option ? <small>{t('videoReconRecommended')}</small> : null}
              </button>
            ))}
          </div>
        </fieldset>

        <div className={styles.fieldset}>
          <label className={styles.label} htmlFor="video-recon-output-name">
            {t('videoReconOutputName')}
          </label>
          <input
            id="video-recon-output-name"
            className={styles.input}
            value={outputName}
            maxLength={MAX_OUTPUT_NAME_LENGTH}
            disabled={submitting}
            onChange={(event) => setOutputName(event.target.value)}
            placeholder={t('videoReconOutputPlaceholder')}
          />
        </div>

        <button
          className={styles.advancedToggle}
          type="button"
          onClick={() => setAdvancedOpen((current) => !current)}
          aria-expanded={advancedOpen}
        >
          <span>{t('videoReconAdvanced')}</span>
          <ChevronDownIcon
            width={15}
            height={15}
            className={advancedOpen ? styles.advancedChevronOpen : ''}
          />
        </button>

        {advancedOpen ? (
          <div className={styles.advancedPanel}>
            <fieldset className={styles.fieldset} disabled={submitting}>
              <label className={styles.label}>{t('videoReconEngineLabel')}</label>
              <div className={styles.segmented}>
                {ENGINE_OPTIONS.map((option) => (
                  <button
                    key={option}
                    className={[
                      styles.segmentBtn,
                      engine === option ? styles.segmentActive : '',
                      option === 'experimental' && !experimentalAvailable ? styles.segmentDisabled : '',
                    ].filter(Boolean).join(' ')}
                    disabled={option === 'experimental' && !experimentalAvailable}
                    onClick={() => setEngine(option)}
                    type="button"
                  >
                    {t(`videoReconEngine.${option}`)}
                  </button>
                ))}
              </div>
            </fieldset>

            <label className={styles.toggleRow}>
              <span>
                <strong>{t('videoReconKeepIntermediate')}</strong>
                <small>{t('videoReconKeepIntermediateHint')}</small>
              </span>
              <input
                type="checkbox"
                checked={keepIntermediateFiles}
                disabled={submitting}
                onChange={(event) => setKeepIntermediateFiles(event.target.checked)}
              />
            </label>

            <div className={styles.budgetHint}>
              <span>{t('videoReconVramBudget')}</span>
              <strong>{t(`videoReconVram.${config.vram_budget}`)}</strong>
            </div>
          </div>
        ) : null}

        {message ? (
          <div className={[styles.message, styles[message.tone]].join(' ')} role="status" aria-live="polite">
            {message.text}
          </div>
        ) : dependencyMessage ? (
          <div className={[styles.message, stableAvailable ? styles.success : styles.error].join(' ')}>
            {dependencyMessage}
          </div>
        ) : null}

        <div className={styles.actions}>
          <Button variant="secondary" type="button" onClick={closeDialog} disabled={submitting}>
            {t('cancel')}
          </Button>
          <Button
            variant="primary"
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            icon={<SparklesIcon width={16} height={16} />}
          >
            {submitting ? t('videoReconSubmitting') : t('videoReconStart')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
