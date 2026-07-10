import { useEffect, useRef, useState } from "react";

interface UseScrollRevealOptions {
  threshold?: number;
  rootMargin?: string;
  /** If true, skip the intersection observer and always report visible. */
  skip?: boolean;
}

export function useScrollReveal(options: UseScrollRevealOptions = {}) {
  const { threshold = 0.15, rootMargin = "0px 0px -60px 0px", skip = false } = options;
  const [isVisible, setIsVisible] = useState(skip);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (skip) {
      setIsVisible(true);
      return;
    }

    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(node);
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold, rootMargin, skip]);

  return { ref, isVisible };
}
