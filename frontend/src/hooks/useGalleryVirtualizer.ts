import type { MutableRefObject } from 'react';

import { useVirtualizer } from '@tanstack/react-virtual';

import { GALLERY_ROW_HEIGHT, GALLERY_VIRTUAL_OVERSCAN } from '@/utils';

interface UseGalleryVirtualizerOptions {
  count: number;
  getItemKey: (index: number) => string;
  scrollElementRef: MutableRefObject<HTMLDivElement | null>;
}

export function useGalleryVirtualizer({
  count,
  getItemKey,
  scrollElementRef,
}: UseGalleryVirtualizerOptions) {
  // eslint-disable-next-line react-hooks/incompatible-library -- Thin adapter keeps the TanStack dependency localized.
  return useVirtualizer({
    count,
    getItemKey,
    getScrollElement: () => scrollElementRef.current,
    estimateSize: () => GALLERY_ROW_HEIGHT,
    overscan: GALLERY_VIRTUAL_OVERSCAN,
  });
}
