import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { usePrefersReducedMotion } from "./components/landing/usePrefersReducedMotion";
import chitrikaIntroAnimated from "../../../../icon/chitrika-knot-dark-separated-move.svg";

interface HeroIntroProps {
  onDone: () => void;
}

const INTRO_MARK_DURATION_MS = 900;
// Includes the SVG's reveal, brief hold, and reverse exit animation.
const SVG_INTRO_DURATION_MS = 5300;
const INTRO_DURATION_MS = INTRO_MARK_DURATION_MS + SVG_INTRO_DURATION_MS;

export function HeroIntro({ onDone }: HeroIntroProps) {
  const reduce = usePrefersReducedMotion();
  const [showLogo, setShowLogo] = useState(false);

  useEffect(() => {
    if (reduce) {
      onDone();
      return;
    }

    const logoId = window.setTimeout(() => setShowLogo(true), INTRO_MARK_DURATION_MS);
    const doneId = window.setTimeout(onDone, INTRO_DURATION_MS);
    return () => {
      window.clearTimeout(logoId);
      window.clearTimeout(doneId);
    };
  }, [onDone, reduce]);

  if (reduce) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.42, ease: [0.25, 0.46, 0.45, 0.94] } }}
      className="fixed inset-0 z-[60] flex items-center justify-center overflow-hidden"
      style={{
        background:
          "radial-gradient(circle at 50% 42%, color-mix(in srgb, var(--app-accent) 10%, transparent), transparent 26rem), linear-gradient(180deg, color-mix(in srgb, var(--app-bg) 94%, #070B14 6%), var(--app-bg))",
      }}
      aria-label="Hero intro"
    >
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div
          className="absolute left-1/2 top-1/2 h-[38rem] w-[38rem] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[140px]"
          style={{
            background: "color-mix(in srgb, var(--app-accent) 16%, transparent)",
            opacity: 0.72,
          }}
        />
      </div>

      {!showLogo ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: [0, 1, 1, 0], y: [8, 0, 0, -4] }}
          transition={{ duration: 0.82, times: [0, 0.22, 0.72, 1], ease: "easeOut" }}
          className="relative flex items-center gap-4 text-3xl font-semibold tracking-[0.08em] md:text-4xl"
          style={{ color: "var(--app-text)" }}
        >
          <span>Introducing</span>
          <motion.span
            className="block size-2.5 rounded-full"
            style={{
              background: "#ffffff",
              boxShadow: "0 0 0 6px rgba(255,255,255,.1), 0 0 28px rgba(255,255,255,.55)",
            }}
            animate={{ scale: [1, 1.24, 1], opacity: [0.75, 1, 0.75] }}
            transition={{ duration: 0.9, repeat: Infinity, ease: "easeInOut" }}
            aria-hidden="true"
          />
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.972, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="relative w-[min(88vw,960px)]"
        >
          <img
            src={chitrikaIntroAnimated}
            alt="Chitrika"
            className="h-auto w-full select-none"
            draggable={false}
          />
        </motion.div>
      )}
    </motion.div>
  );
}
