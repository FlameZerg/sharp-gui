import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import { CheckIcon, ChevronDownIcon } from '@/components/common/Icons';

import styles from './SelectMenu.module.css';

export interface SelectMenuOption {
  value: string;
  label: string;
  icon?: ReactNode;
}

interface SelectMenuProps {
  value: string;
  options: SelectMenuOption[];
  onChange: (value: string) => void;
  ariaLabel: string;
  icon?: ReactNode;
  compact?: boolean;
  showSelectedLabel?: boolean;
  disabled?: boolean;
  className?: string;
}

export function SelectMenu({
  value,
  options,
  onChange,
  ariaLabel,
  icon,
  compact = false,
  showSelectedLabel = true,
  disabled = false,
  className = '',
}: SelectMenuProps) {
  const listboxId = useId();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? options[0],
    [options, value],
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = useCallback((nextValue: string) => {
    onChange(nextValue);
    setIsOpen(false);
  }, [onChange]);

  return (
    <div
      ref={rootRef}
      className={[
        styles.root,
        compact ? styles.compact : '',
        !showSelectedLabel ? styles.iconOnly : '',
        className,
      ].filter(Boolean).join(' ')}
    >
      <button
        className={styles.trigger}
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        disabled={disabled}
        onClick={() => setIsOpen((current) => !current)}
      >
        {icon ? <span className={styles.triggerIcon}>{icon}</span> : null}
        {showSelectedLabel ? <span className={styles.triggerLabel}>{selectedOption?.label}</span> : null}
        {showSelectedLabel && selectedOption?.icon ? (
          <span className={styles.triggerDirection}>{selectedOption.icon}</span>
        ) : null}
        <ChevronDownIcon width={15} height={15} />
      </button>

      {isOpen ? (
        <div id={listboxId} className={styles.menu} role="listbox" aria-label={ariaLabel}>
          {options.map((option) => {
            const isSelected = option.value === value;
            return (
              <button
                key={option.value}
                className={[styles.option, isSelected ? styles.optionSelected : ''].filter(Boolean).join(' ')}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(option.value)}
              >
                <span className={styles.optionLabel}>
                  {option.icon ? <span className={styles.optionDirection}>{option.icon}</span> : null}
                  <span className={styles.optionText}>{option.label}</span>
                </span>
                {isSelected ? <CheckIcon width={15} height={15} /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
