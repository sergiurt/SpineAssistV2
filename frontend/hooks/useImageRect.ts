import { useEffect, useRef, useState, RefObject } from "react";

export interface ImageRect {
  offsetTop: number;
  offsetLeft: number;
  renderedWidth: number;
  renderedHeight: number;
}

const EMPTY: ImageRect = {
  offsetTop: 0,
  offsetLeft: 0,
  renderedWidth: 0,
  renderedHeight: 0,
};

export function useImageRect(
  containerRef: RefObject<HTMLDivElement | null>,
  naturalWidth: number,
  naturalHeight: number
): ImageRect {
  const [rect, setRect] = useState<ImageRect>(EMPTY);
  // Keep a stable ref to the latest containerRef.current so the effect
  // doesn't need to re-run every time the wrapper object changes identity.
  const containerNodeRef = useRef<Element | null>(null);
  containerNodeRef.current = containerRef.current;

  useEffect(() => {
    const container = containerNodeRef.current;
    if (!container || !naturalWidth || !naturalHeight) {
      setRect(EMPTY);
      return;
    }

    const compute = (): ImageRect => {
      const { width: cw, height: ch } = container.getBoundingClientRect();
      const imgAspect = naturalWidth / naturalHeight;
      const containerAspect = cw / ch;

      let rw: number, rh: number;
      if (imgAspect > containerAspect) {
        // wider than container — letterbox top/bottom
        rw = cw;
        rh = cw / imgAspect;
      } else {
        // taller than container — pillarbox left/right
        rh = ch;
        rw = ch * imgAspect;
      }

      return {
        offsetTop: (ch - rh) / 2,
        offsetLeft: (cw - rw) / 2,
        renderedWidth: rw,
        renderedHeight: rh,
      };
    };

    const update = () => {
      const next = compute();
      setRect((prev) => {
        if (
          prev.renderedWidth === next.renderedWidth &&
          prev.renderedHeight === next.renderedHeight &&
          prev.offsetTop === next.offsetTop &&
          prev.offsetLeft === next.offsetLeft
        ) {
          return prev; // bail out — no change, avoids infinite loop
        }
        return next;
      });
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(container);
    return () => ro.disconnect();
  }, [naturalWidth, naturalHeight]); // container accessed via stable ref

  return rect;
}
