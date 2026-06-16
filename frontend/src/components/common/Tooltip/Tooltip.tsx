import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import styles from './Tooltip.module.css';

const SHOW_DELAY_MS = 320;
const EDGE_GAP = 8;
const TARGET_OFFSET = 10;

/**
 * GlobalTooltip renders a single glass-morphism tooltip for any element carrying
 * a non-empty `data-tooltip` attribute. It uses event delegation on the document
 * so components only need to set `data-tooltip="..."` (no wrapper component), and
 * a portal so the bubble is never clipped by `overflow: hidden` ancestors.
 */
export function GlobalTooltip() {
  const [text, setText] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  const bubbleRef = useRef<HTMLDivElement>(null);
  const targetRef = useRef<HTMLElement | null>(null);
  const showTimerRef = useRef<number | undefined>(undefined);

  const clearShowTimer = useCallback(() => {
    if (showTimerRef.current !== undefined) {
      window.clearTimeout(showTimerRef.current);
      showTimerRef.current = undefined;
    }
  }, []);

  const hide = useCallback(() => {
    clearShowTimer();
    targetRef.current = null;
    setVisible(false);
    setText(null);
  }, [clearShowTimer]);

  const positionBubble = useCallback(() => {
    const bubble = bubbleRef.current;
    const target = targetRef.current;
    if (!bubble || !target || !target.isConnected) {
      return;
    }

    const rect = target.getBoundingClientRect();
    const bubbleWidth = bubble.offsetWidth;
    const bubbleHeight = bubble.offsetHeight;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let top = rect.top - bubbleHeight - TARGET_OFFSET;
    if (top < EDGE_GAP) {
      top = rect.bottom + TARGET_OFFSET;
    }

    let left = rect.left + rect.width / 2 - bubbleWidth / 2;
    left = Math.min(Math.max(left, EDGE_GAP), viewportWidth - bubbleWidth - EDGE_GAP);
    top = Math.min(Math.max(top, EDGE_GAP), viewportHeight - bubbleHeight - EDGE_GAP);

    bubble.style.left = `${Math.round(left)}px`;
    bubble.style.top = `${Math.round(top)}px`;
  }, []);

  useLayoutEffect(() => {
    if (text !== null) {
      positionBubble();
    }
  }, [text, positionBubble]);

  useEffect(() => {
    const resolveTarget = (node: EventTarget | null): HTMLElement | null => {
      if (!(node instanceof Element)) {
        return null;
      }
      const match = node.closest<HTMLElement>('[data-tooltip]');
      if (!match) {
        return null;
      }
      const value = match.getAttribute('data-tooltip');
      return value && value.trim() ? match : null;
    };

    const handlePointerEnter = (event: MouseEvent) => {
      const target = resolveTarget(event.target);
      if (!target || target === targetRef.current) {
        return;
      }
      clearShowTimer();
      targetRef.current = target;
      const value = target.getAttribute('data-tooltip') ?? '';
      showTimerRef.current = window.setTimeout(() => {
        if (targetRef.current !== target || !target.isConnected) {
          return;
        }
        setText(value);
        setVisible(true);
      }, SHOW_DELAY_MS);
    };

    const handlePointerLeave = (event: MouseEvent) => {
      const leaving = resolveTarget(event.target);
      if (leaving && leaving === targetRef.current) {
        const related = event.relatedTarget;
        if (related instanceof Node && leaving.contains(related)) {
          return;
        }
        hide();
      }
    };

    const handleFocusIn = (event: FocusEvent) => {
      const target = resolveTarget(event.target);
      if (!target) {
        return;
      }
      clearShowTimer();
      targetRef.current = target;
      setText(target.getAttribute('data-tooltip') ?? '');
      setVisible(true);
    };

    const handleFocusOut = (event: FocusEvent) => {
      if (resolveTarget(event.target) === targetRef.current) {
        hide();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        hide();
      }
    };

    document.addEventListener('mouseover', handlePointerEnter);
    document.addEventListener('mouseout', handlePointerLeave);
    document.addEventListener('focusin', handleFocusIn);
    document.addEventListener('focusout', handleFocusOut);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', hide, true);
    window.addEventListener('resize', hide);
    window.addEventListener('wheel', hide, { passive: true });

    return () => {
      clearShowTimer();
      document.removeEventListener('mouseover', handlePointerEnter);
      document.removeEventListener('mouseout', handlePointerLeave);
      document.removeEventListener('focusin', handleFocusIn);
      document.removeEventListener('focusout', handleFocusOut);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', hide, true);
      window.removeEventListener('resize', hide);
      window.removeEventListener('wheel', hide);
    };
  }, [clearShowTimer, hide]);

  if (text === null) {
    return null;
  }

  return createPortal(
    <div
      ref={bubbleRef}
      className={[styles.bubble, visible ? styles.visible : ''].filter(Boolean).join(' ')}
      role="tooltip"
    >
      {text}
    </div>,
    document.body,
  );
}

GlobalTooltip.displayName = 'GlobalTooltip';
