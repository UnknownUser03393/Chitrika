import { motion } from "motion/react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

interface Props {
  active?: boolean;
}

export function TimelineSection({ active }: Props = {}) {
  const { lang } = useLang();
  const t = translations.timeline;
  const events = t.events;
  const reduce = usePrefersReducedMotion();
  const { ref, isVisible } = useScrollReveal({ skip: reduce, active });

  return (
    <section
      ref={ref}
      className="relative py-16 md:py-24 px-6 min-h-full"
      style={{ background: "var(--app-panel)" }}
    >
      <div className="text-center mb-16 md:mb-20">
        <h2
          className="text-3xl md:text-4xl font-bold tracking-tight"
          style={{ color: "var(--app-text)" }}
        >
          {t.heading[lang]}
        </h2>
        <p className="mt-3 text-lg" style={{ color: "var(--app-muted)" }}>
          {t.subtitle[lang]}
        </p>
      </div>

      <div className="relative max-w-2xl mx-auto">
        <div
          className="absolute left-4 md:left-1/2 md:-translate-x-px top-0 bottom-0 w-px"
          style={{ background: "var(--app-border)" }}
          aria-hidden="true"
        />

        <div className="flex flex-col gap-12">
          {events.map((entry, i) => {
            const isAccent = i === 3;
            const isPositive = i === 4;
            const dotColor = isAccent
              ? "var(--app-accent)"
              : isPositive
                ? "#4ade80"
                : "var(--app-muted)";
            const ringColor = isAccent
              ? "color-mix(in srgb, var(--app-accent) 20%, transparent)"
              : isPositive
                ? "color-mix(in srgb, #4ade80 20%, transparent)"
                : "color-mix(in srgb, var(--app-border) 60%, transparent)";
            const borderColor = isAccent
              ? "color-mix(in srgb, var(--app-accent) 30%, transparent)"
              : isPositive
                ? "color-mix(in srgb, #4ade80 25%, transparent)"
                : "var(--app-border)";

            return (
              <motion.div
                key={i}
                initial={reduce ? false : { opacity: 0, y: 40 }}
                animate={reduce || isVisible ? { opacity: 1, y: 0 } : {}}
                transition={
                  reduce
                    ? { duration: 0 }
                    : {
                        duration: 0.5,
                        delay: 0.15 * i,
                        ease: [0.25, 0.46, 0.45, 0.94],
                      }
                }
                className={`relative pl-12 md:pl-0 md:w-1/2 ${
                  i % 2 === 0 ? "md:pr-12 md:text-right md:ml-0" : "md:pl-12 md:ml-auto"
                }`}
              >
                <div
                  className={`absolute top-1.5 w-3 h-3 rounded-full ${
                    i % 2 === 0
                      ? "left-[10px] md:left-auto md:right-[-7px]"
                      : "left-[10px] md:left-[-7px]"
                  }`}
                  style={{
                    background: dotColor,
                    boxShadow: `0 0 0 4px ${ringColor}`,
                  }}
                  aria-hidden="true"
                />

                <div
                  className="p-5 rounded-xl border"
                  style={{
                    background: "var(--app-bg)",
                    borderColor,
                  }}
                >
                  <span
                    className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: dotColor }}
                  >
                    {entry.date[lang]}
                  </span>
                  <h3
                    className="mt-2 text-base font-semibold"
                    style={{ color: "var(--app-text)" }}
                  >
                    {entry.title[lang]}
                  </h3>
                  <p
                    className="mt-2 text-sm leading-relaxed"
                    style={{ color: "var(--app-muted)" }}
                  >
                    {entry.body[lang]}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
