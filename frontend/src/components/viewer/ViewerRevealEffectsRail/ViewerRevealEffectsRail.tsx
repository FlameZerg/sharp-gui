import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import * as Icons from '@/components/common/Icons';
import {
  getRevealEffectOption,
  isRevealEffectEnabled,
  VIEWER_REVEAL_EFFECTS,
  type RevealEffectId,
} from '@/utils/viewerRevealEffects';
import styles from './ViewerRevealEffectsRail.module.css';

interface ViewerRevealEffectsRailProps {
  activeEffect: RevealEffectId;
  isInXr: boolean;
  onReplay: () => void;
  onSelectEffect: (effectId: RevealEffectId) => void;
}

function joinClasses(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

export function ViewerRevealEffectsRail({
  activeEffect,
  isInXr,
  onReplay,
  onSelectEffect,
}: ViewerRevealEffectsRailProps) {
  const { t } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mobileOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setMobileOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileOpen(false);
      }
    };

    window.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [mobileOpen]);

  if (isInXr) return null;

  const activeIndex = VIEWER_REVEAL_EFFECTS.findIndex((effect) => effect.id === activeEffect);
  const hasActiveSelection = activeIndex >= 0;
  const activeOption = getRevealEffectOption(activeEffect);
  const canGoUp = activeIndex > 0;
  const canGoDown = activeIndex >= 0 && activeIndex < VIEWER_REVEAL_EFFECTS.length - 1;
  const replayDisabled = !isRevealEffectEnabled(activeEffect);

  const handleSelect = (effectId: RevealEffectId) => {
    onSelectEffect(effectId);
    setMobileOpen(false);
  };

  const handleMobileSelect = (effectId: RevealEffectId) => {
    setMobileOpen(false);
    requestAnimationFrame(() => {
      onSelectEffect(effectId);
    });
  };

  const renderRailControls = ({
    selectEffect,
    replayAction,
  }: {
    selectEffect: (effectId: RevealEffectId) => void;
    replayAction: () => void;
  }) => (
    <>
      <div className={styles.railPanel}>
        <button
          type="button"
          className={styles.railNavButton}
          aria-label={t('revealEffectsPrevious')}
          disabled={!canGoUp}
          onClick={() => {
            if (!canGoUp) return;
            selectEffect(VIEWER_REVEAL_EFFECTS[activeIndex - 1].id);
          }}
        >
          <Icons.ChevronUpIcon />
        </button>

        <div className={styles.railTrack}>
          {VIEWER_REVEAL_EFFECTS.map((effect, index) => {
            const isActive = effect.id === activeEffect;
            const isNeighbor = hasActiveSelection && Math.abs(index - activeIndex) === 1;

            return (
              <button
                key={effect.id}
                type="button"
                className={styles.railItem}
                aria-label={t('revealEffectsSelectAria', { effect: t(effect.labelKey) })}
                aria-pressed={isActive}
                onClick={() => selectEffect(effect.id)}
              >
                <span
                  className={joinClasses(
                    styles.railLine,
                    isActive && styles.railLineActive,
                    !isActive && isNeighbor && styles.railLineNeighbor,
                  )}
                />
                {isActive ? <span className={styles.railIndicatorDot} /> : null}
                <span className={styles.tooltip}>
                  <span className={styles.tooltipTitle}>{t(effect.labelKey)}</span>
                  <span className={styles.tooltipSubtitle}>{effect.shortLabel}</span>
                </span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          className={styles.railNavButton}
          aria-label={t('revealEffectsNext')}
          disabled={!canGoDown}
          onClick={() => {
            if (!canGoDown) return;
            selectEffect(VIEWER_REVEAL_EFFECTS[activeIndex + 1].id);
          }}
        >
          <Icons.ChevronDownIcon />
        </button>
      </div>

      <button
        type="button"
        className={styles.replayButton}
        aria-label={t('revealEffectsReplay')}
        disabled={replayDisabled}
        onClick={replayAction}
      >
        <Icons.ResetIcon />
        <span className={styles.tooltip}>
          <span className={styles.tooltipTitle}>{t('revealEffectsReplay')}</span>
          <span className={styles.tooltipSubtitle}>Replay</span>
        </span>
      </button>
    </>
  );

  return (
    <div ref={rootRef} className={styles.root}>
      <div className={styles.desktopRail} aria-label={t('revealEffectsTitle')}>
        {renderRailControls({
          selectEffect: handleSelect,
          replayAction: onReplay,
        })}
      </div>

      <div className={styles.mobileRail}>
        <div
          id="viewer-reveal-effects-panel"
          className={joinClasses(styles.mobilePopup, mobileOpen && styles.mobilePopupOpen)}
          aria-hidden={!mobileOpen}
        >
          <div className={styles.mobilePopupContent}>
            {renderRailControls({
              selectEffect: handleMobileSelect,
              replayAction: onReplay,
            })}
          </div>
        </div>

        <button
          type="button"
          className={styles.mobileTrigger}
          aria-expanded={mobileOpen}
          aria-controls="viewer-reveal-effects-panel"
          aria-label={t('revealEffectsOpenAria', { effect: t(activeOption.labelKey) })}
          onClick={() => setMobileOpen((value) => !value)}
        >
          <Icons.SparklesIcon />
        </button>
      </div>
    </div>
  );
}
