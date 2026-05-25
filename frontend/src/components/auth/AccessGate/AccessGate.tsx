import { useState } from 'react';
import type { FormEvent } from 'react';

import { LockKeyhole, ShieldCheck, Unlock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useShallow } from 'zustand/react/shallow';

import { ApiError, loginWithAccessCode } from '@/api';
import { useAppStore } from '@/store';

import styles from './AccessGate.module.css';

interface AccessGateProps {
  onUnlocked: () => Promise<void> | void;
}

export function AccessGate({ onUnlocked }: AccessGateProps) {
  const { t } = useTranslation();
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { authStatus, setAuthStatus } = useAppStore(
    useShallow((state) => ({
      authStatus: state.authStatus,
      setAuthStatus: state.setAuthStatus,
    })),
  );

  const setupRequired = authStatus?.setup_required ?? false;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (setupRequired || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const nextStatus = await loginWithAccessCode({ password });
      setAuthStatus(nextStatus);
      setPassword('');
      await onUnlocked();
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.data?.code === 'ACCESS_SETUP_REQUIRED'
          ? t('accessGateSetupRequired')
          : t('accessGateInvalidCode'));
      } else {
        setError(t('accessGateLoginFailed'));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className={styles.shell}>
      <section className={styles.panel}>
        <div className={styles.iconWrap}>
          {setupRequired ? <ShieldCheck size={28} /> : <LockKeyhole size={28} />}
        </div>
        <h1 className={styles.title}>{t('accessGateTitle')}</h1>
        <p className={styles.subtitle}>
          {setupRequired ? t('accessGateSetupRequired') : t('accessGateSubtitle')}
        </p>

        {!setupRequired && (
          <form className={styles.form} onSubmit={handleSubmit}>
            <label className={styles.label} htmlFor="access-code">
              {t('accessGateCodeLabel')}
            </label>
            <input
              id="access-code"
              className={styles.input}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t('accessGateCodePlaceholder')}
              disabled={isSubmitting}
              autoFocus
            />
            {error ? <p className={styles.error}>{error}</p> : null}
            <button className={styles.submit} type="submit" disabled={!password || isSubmitting}>
              <Unlock size={18} />
              <span>{isSubmitting ? t('accessGateUnlocking') : t('accessGateUnlock')}</span>
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
