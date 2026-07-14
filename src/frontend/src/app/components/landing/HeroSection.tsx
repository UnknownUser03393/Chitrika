import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ArrowDown, Zap } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import { HeroIntro } from "../../StartupSplash";

interface Props {
  onGetStarted: () => void;
  onScrollToTimeline: () => void;
}

function useCountdown() {
  const target = new Date("2026-07-15T00:00:00+08:00").getTime();
  const [delta, setDelta] = useState(() => target - Date.now());
  useEffect(() => {
    const id = setInterval(() => setDelta(target - Date.now()), 60_000);
    return () => clearInterval(id);
  }, [target]);
  const isAfter = delta <= 0;
  const abs = Math.abs(delta);
  const days = Math.floor(abs / 86_400_000);
  const hours = Math.floor((abs % 86_400_000) / 3_600_000);
  return { isAfter, days, hours };
}

export function HeroSection({ onGetStarted, onScrollToTimeline }: Props) {
  const { lang } = useLang();
  const t = translations.hero;
  const { isAfter, days, hours } = useCountdown();
  const reduce = usePrefersReducedMotion();
  const [showIntro, setShowIntro] = useState(!reduce);

  const handleIntroDone = useCallback(() => {
    setShowIntro(false);
  }, []);

  const countdownText = isAfter
    ? t.countdownPast[lang]
    : t.countdown[lang](days, hours);

  const fadeUp = (delay = 0) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: 40 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.7, delay, ease: [0.25, 0.46, 0.45, 0.94] as const },
        };

  return (
    <section
      className="relative min-h-full h-full flex flex-col items-center justify-center px-6 text-center overflow-hidden"
      style={{
        background:
          "radial-gradient(circle at 50% 42%, color-mix(in srgb, var(--app-accent) 10%, transparent), transparent 26rem), linear-gradient(180deg, color-mix(in srgb, var(--app-bg) 94%, #070B14 6%), var(--app-bg))",
      }}
    >
      <AnimatePresence>
        {showIntro && <HeroIntro onDone={handleIntroDone} />}
      </AnimatePresence>

      <motion.div
        animate={showIntro ? { opacity: 0 } : { opacity: 1 }}
        transition={{ duration: showIntro ? 0.15 : 0.45, delay: showIntro ? 0 : 0.08 }}
        className="relative flex min-h-full w-full flex-col items-center justify-center"
      >
        {/* Ambient glow */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        {reduce ? (
          <div
            className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
            style={{
              background: "color-mix(in srgb, var(--app-accent) 18%, transparent)",
              opacity: 0.85,
            }}
          />
        ) : (
          <motion.div
            className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
            style={{ background: "color-mix(in srgb, var(--app-accent) 18%, transparent)" }}
            animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
      </div>

      <motion.div
        {...(reduce
          ? {}
          : {
              initial: { opacity: 0, y: -20 },
              animate: { opacity: 1, y: 0 },
              transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] as const },
            })}
        className="relative mb-8 px-4 py-2 rounded-full border text-sm font-medium"
        style={{
          borderColor: isAfter ? "var(--app-danger)" : "var(--app-accent)",
          color: isAfter ? "var(--app-danger)" : "var(--app-accent)",
          background: isAfter
            ? "color-mix(in srgb, var(--app-danger) 10%, transparent)"
            : "color-mix(in srgb, var(--app-accent) 10%, transparent)",
        }}
      >
        {countdownText}
      </motion.div>

      <motion.h1
        {...fadeUp(0.15)}
        className={`relative mx-auto whitespace-pre-line text-balance font-bold tracking-tight ${
          lang === "en"
            ? "max-w-[18ch] text-3xl md:text-4xl lg:text-[3.35rem] leading-[1.02]"
            : "max-w-[14ch] text-4xl md:text-5xl lg:text-6xl leading-[1.12]"
        }`}
        style={{ color: "var(--app-text)" }}
      >
        {t.headline[lang]}
      </motion.h1>

      <motion.div
        {...(reduce
          ? {}
          : {
              initial: { opacity: 0, y: 30 },
              animate: { opacity: 1, y: 0 },
              transition: { duration: 0.7, delay: 0.35, ease: [0.25, 0.46, 0.45, 0.94] as const },
            })}
        className="relative mt-8 px-6 py-5 rounded-2xl border max-w-lg"
        style={{
          background: "color-mix(in srgb, var(--app-accent) 8%, transparent)",
          borderColor: "color-mix(in srgb, var(--app-accent) 25%, transparent)",
        }}
      >
        {t.punchline[lang].split("\n").map((line, i) => (
          <p
            key={i}
            className="text-xl md:text-2xl font-bold leading-snug"
            style={{ color: "var(--app-text)" }}
          >
            {line}
          </p>
        ))}
      </motion.div>

      <motion.p
        {...(reduce
          ? {}
          : {
              initial: { opacity: 0, y: 30 },
              animate: { opacity: 1, y: 0 },
              transition: { duration: 0.6, delay: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const },
            })}
        className="relative mt-6 max-w-xl text-lg md:text-xl leading-relaxed"
        style={{ color: "var(--app-muted)" }}
      >
        {t.subtitle1[lang]}{" "}
        <strong style={{ color: "var(--app-text)" }}>{t.subtitleStrong[lang]}</strong>
      </motion.p>

      <motion.div
        {...(reduce
          ? {}
          : {
              initial: { opacity: 0, y: 30 },
              animate: { opacity: 1, y: 0 },
              transition: { duration: 0.6, delay: 0.7 },
            })}
        className="relative mt-10 flex flex-col sm:flex-row gap-4 items-center"
      >
        <button
          onClick={onGetStarted}
          className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-base font-semibold transition-all hover:scale-[1.03] active:scale-[0.98]"
          style={{
            background: "var(--app-accent)",
            color: "#fff",
            boxShadow: "0 0 32px color-mix(in srgb, var(--app-accent) 30%, transparent)",
          }}
        >
          <Zap size={18} aria-hidden="true" />
          {t.cta[lang]}
        </button>

        <button
          onClick={onScrollToTimeline}
          className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl text-base font-medium transition-colors hover:bg-white/5"
          style={{ color: "var(--app-muted)" }}
        >
          <ArrowDown size={16} aria-hidden="true" />
          {t.secondaryCta[lang]}
        </button>
      </motion.div>

      {/* Scroll hint */}
      <motion.div
        {...(reduce
          ? { initial: false, animate: { opacity: 1 } }
          : {
              initial: { opacity: 0 },
              animate: { opacity: 1 },
              transition: { delay: 1.4 },
            })}
        className="absolute bottom-8"
        aria-hidden="true"
      >
        <div
          className="w-5 h-8 rounded-full border flex items-start justify-center p-1"
          style={{ borderColor: "var(--app-border)" }}
        >
          {reduce ? (
            <div
              className="w-1 h-2 rounded-full"
              style={{ background: "var(--app-muted)" }}
            />
          ) : (
            <motion.div
              className="w-1 h-2 rounded-full"
              style={{ background: "var(--app-muted)" }}
              animate={{ y: [0, 10, 0] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            />
          )}
        </div>
      </motion.div>
      </motion.div>
    </section>
  );
}
