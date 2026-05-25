import { BellOff, Download, KeyRound, LockKeyhole, ShieldAlert, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import styles from './AccessSetupPrompt.module.css';

interface AccessSetupPromptProps {
  open: boolean;
  onOpenSettings: () => void;
  onDismiss: () => void;
  onNeverRemind: () => void;
}

export function AccessSetupPrompt({ open, onOpenSettings, onDismiss, onNeverRemind }: AccessSetupPromptProps) {
  const { t } = useTranslation();

  if (!open) {
    return null;
  }

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" aria-labelledby="access-setup-title">
      <section className={styles.panel}>
        <div className={styles.header}>
          <div className={styles.iconWrap}>
            <ShieldAlert size={26} />
          </div>
          <div>
            <span className={styles.kicker}>{t('accessSetupPromptKicker')}</span>
            <h2 id="access-setup-title" className={styles.title}>
              {t('accessSetupPromptTitle')}
            </h2>
          </div>
        </div>
        <p className={styles.description}>{t('accessSetupPromptDescription')}</p>
        <div className={styles.points}>
          <div className={styles.point}>
            <span className={styles.pointIcon}><LockKeyhole size={17} /></span>
            <p>{t('accessSetupPromptPrivateResources')}</p>
          </div>
          <div className={styles.point}>
            <span className={styles.pointIcon}><Sparkles size={17} /></span>
            <p>{t('accessSetupPromptRemoteBoundary')}</p>
          </div>
          <div className={styles.point}>
            <span className={styles.pointIcon}><Download size={17} /></span>
            <p>{t('accessSetupPromptHttpsHint')}</p>
          </div>
        </div>
        <div className={styles.actions}>
          <button type="button" className={styles.ghostBtn} onClick={onNeverRemind}>
            <BellOff size={16} />
            <span>{t('accessSetupPromptNever')}</span>
          </button>
          <button type="button" className={styles.secondaryBtn} onClick={onDismiss}>
            {t('accessSetupPromptLater')}
          </button>
          <button type="button" className={styles.primaryBtn} onClick={onOpenSettings}>
            <KeyRound size={18} />
            <span>{t('accessSetupPromptSetNow')}</span>
          </button>
        </div>
      </section>
    </div>
  );
}
