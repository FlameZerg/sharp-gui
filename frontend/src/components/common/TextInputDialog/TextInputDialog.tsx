import { useEffect, useId, useRef } from 'react';

import { useTranslation } from 'react-i18next';

import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';

import styles from './TextInputDialog.module.css';

interface TextInputDialogProps {
  isOpen: boolean;
  title: string;
  label: string;
  placeholder?: string;
  confirmLabel?: string;
  initialValue?: string;
  isBusy?: boolean;
  onSubmit: (value: string) => void;
  onClose: () => void;
}

export function TextInputDialog({
  isOpen,
  title,
  label,
  placeholder,
  confirmLabel,
  initialValue = '',
  isBusy = false,
  onSubmit,
  onClose,
}: TextInputDialogProps) {
  const { t } = useTranslation();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    window.setTimeout(() => inputRef.current?.focus(), 40);
  }, [isOpen]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="md">
      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          const trimmedValue = inputRef.current?.value.trim() ?? '';
          if (trimmedValue) {
            onSubmit(trimmedValue);
          }
        }}
      >
        <label className={styles.label} htmlFor={inputId}>
          {label}
        </label>
        <input
          ref={inputRef}
          id={inputId}
          className={styles.input}
          defaultValue={initialValue}
          placeholder={placeholder}
          disabled={isBusy}
        />
        <div className={styles.actions}>
          <Button variant="secondary" onClick={onClose} disabled={isBusy} type="button">
            {t('cancel')}
          </Button>
          <Button variant="primary" disabled={isBusy} type="submit">
            {confirmLabel ?? t('confirm')}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
