import { useReducedMotion } from "motion/react";

/** Shared prefers-reduced-motion hook (re-exports motion/react). */
export function usePrefersReducedMotion(): boolean {
  return Boolean(useReducedMotion());
}
