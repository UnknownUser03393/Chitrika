import { motion } from "motion/react";
import { Zap } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

interface Props {
  onGetStarted: () => void;
  active?: boolean;
}

export function FooterSection({ onGetStarted, active }: Props) {
  const { lang } = useLang();
  const f = translations.footer;
  const reduce = usePrefersReducedMotion();
  const { ref, isVisible } = useScrollReveal({ skip: reduce, active });

  return (
    <section
      ref={ref}
      className="relative py-16 md:py-24 px-6 text-center min-h-full flex flex-col justify-center"
      style={{ background: "var(--app-panel)" }}
    >
      <div className="absolute inset-0 pointer-events-none flex items-center justify-center" aria-hidden="true">
        {reduce ? (
          <div
            className="w-[400px] h-[400px] rounded-full blur-[100px]"
            style={{
              background: "color-mix(in srgb, var(--app-accent) 14%, transparent)",
              opacity: 0.9,
            }}
          />
        ) : (
          <motion.div
            className="w-[400px] h-[400px] rounded-full blur-[100px]"
            style={{ background: "color-mix(in srgb, var(--app-accent) 14%, transparent)" }}
            animate={{ scale: [1, 1.06, 1] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          />
        )}
      </div>

      <motion.div
        initial={reduce ? false : { opacity: 0, y: 30 }}
        animate={reduce || isVisible ? { opacity: 1, y: 0 } : {}}
        transition={reduce ? { duration: 0 } : { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="relative"
      >
        <h2
          className="text-3xl md:text-4xl font-bold tracking-tight"
          style={{ color: "var(--app-text)" }}
        >
          {f.heading[lang]}
        </h2>
        <p
          className="mt-6 text-lg max-w-lg mx-auto"
          style={{ color: "var(--app-muted)" }}
        >
          {f.subtitle[lang]}
        </p>
        <button
          onClick={onGetStarted}
          className="relative mt-10 inline-flex items-center gap-2 px-10 py-4 rounded-xl text-lg font-bold transition-all hover:scale-[1.04] active:scale-[0.98]"
          style={{
            background: "var(--app-accent)",
            color: "#fff",
            boxShadow: "0 0 48px color-mix(in srgb, var(--app-accent) 35%, transparent)",
          }}
        >
          <Zap size={20} aria-hidden="true" />
          {f.cta[lang]}
        </button>
      </motion.div>

      <motion.div
        initial={reduce ? false : { opacity: 0 }}
        animate={reduce || isVisible ? { opacity: 1 } : {}}
        transition={reduce ? { duration: 0 } : { duration: 0.5, delay: 0.4 }}
        className="relative mt-20 pt-8 border-t"
        style={{ borderColor: "var(--app-border)" }}
      >
        <p
          className="text-sm font-medium tracking-wide uppercase"
          style={{ color: "var(--app-subtle)" }}
        >
          {f.tagline[lang]}
        </p>
        <p className="mt-2 text-xs" style={{ color: "var(--app-subtle)" }}>
          {f.brand[lang]}
        </p>
      </motion.div>
    </section>
  );
}
