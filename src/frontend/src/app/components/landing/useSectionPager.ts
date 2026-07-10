import { useCallback, useEffect, useRef } from "react";

const COOLDOWN_MS = 750;
const WHEEL_THRESHOLD = 10;
const SWIPE_THRESHOLD = 48;

interface UseSectionPagerOptions {
  enabled: boolean;
  count: number;
  index: number;
  onChange: (next: number, direction: 1 | -1) => void;
  /** Active slide's scroll container — used to allow inner scroll before paging. */
  getActiveScrollEl: () => HTMLElement | null;
}

function isScrollable(el: HTMLElement): boolean {
  return el.scrollHeight > el.clientHeight + 2;
}

function atScrollBoundary(el: HTMLElement, deltaY: number): boolean {
  const { scrollTop, scrollHeight, clientHeight } = el;
  if (deltaY > 0) {
    return scrollTop + clientHeight >= scrollHeight - 2;
  }
  return scrollTop <= 1;
}

export function useSectionPager({
  enabled,
  count,
  index,
  onChange,
  getActiveScrollEl,
}: UseSectionPagerOptions) {
  const lockedRef = useRef(false);
  const indexRef = useRef(index);
  indexRef.current = index;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const getScrollRef = useRef(getActiveScrollEl);
  getScrollRef.current = getActiveScrollEl;
  const touchYRef = useRef(0);

  const go = useCallback(
    (next: number) => {
      if (!enabled) return;
      if (lockedRef.current) return;
      if (next < 0 || next >= count) return;
      if (next === indexRef.current) return;

      lockedRef.current = true;
      const direction: 1 | -1 = next > indexRef.current ? 1 : -1;
      onChangeRef.current(next, direction);

      window.setTimeout(() => {
        lockedRef.current = false;
      }, COOLDOWN_MS);
    },
    [enabled, count],
  );

  useEffect(() => {
    if (!enabled) return;

    const tryPage = (deltaY: number) => {
      const el = getScrollRef.current();
      if (el && isScrollable(el) && !atScrollBoundary(el, deltaY)) {
        return false;
      }
      if (deltaY > 0) go(indexRef.current + 1);
      else go(indexRef.current - 1);
      return true;
    };

    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) < WHEEL_THRESHOLD) return;

      const el = getScrollRef.current();
      if (el && isScrollable(el) && !atScrollBoundary(el, e.deltaY)) {
        // Let the slide scroll its own content.
        return;
      }

      e.preventDefault();
      tryPage(e.deltaY);
    };

    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      switch (e.key) {
        case "ArrowDown":
        case "PageDown":
          e.preventDefault();
          go(indexRef.current + 1);
          break;
        case "ArrowUp":
        case "PageUp":
          e.preventDefault();
          go(indexRef.current - 1);
          break;
        case " ":
          e.preventDefault();
          go(indexRef.current + (e.shiftKey ? -1 : 1));
          break;
        case "Home":
          e.preventDefault();
          go(0);
          break;
        case "End":
          e.preventDefault();
          go(count - 1);
          break;
        default:
          break;
      }
    };

    const onTouchStart = (e: TouchEvent) => {
      touchYRef.current = e.touches[0]?.clientY ?? 0;
    };

    const onTouchEnd = (e: TouchEvent) => {
      const endY = e.changedTouches[0]?.clientY ?? touchYRef.current;
      const dy = touchYRef.current - endY;
      if (Math.abs(dy) < SWIPE_THRESHOLD) return;

      const el = getScrollRef.current();
      if (el && isScrollable(el) && !atScrollBoundary(el, dy)) {
        return;
      }

      if (dy > 0) go(indexRef.current + 1);
      else go(indexRef.current - 1);
    };

    window.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchend", onTouchEnd, { passive: true });

    return () => {
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [enabled, go, count]);

  return { go };
}
