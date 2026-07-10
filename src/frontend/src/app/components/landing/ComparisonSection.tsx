import { motion } from "motion/react";
import { Check, X, Server, Shield, Users, Eye, CreditCard, Bell, Database } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

const ICONS = [Database, Shield, Server, Users, Eye, CreditCard, Bell];

interface Props {
  active?: boolean;
}

export function ComparisonSection({ active }: Props = {}) {
  const { lang } = useLang();
  const t = translations.comparison;
  const reduce = usePrefersReducedMotion();
  const { ref, isVisible } = useScrollReveal({ skip: reduce, active });

  return (
    <section ref={ref} className="relative py-16 md:py-24 px-6 min-h-full">
      <div className="text-center mb-16">
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

      <div className="max-w-4xl mx-auto mb-6 hidden md:grid grid-cols-[1fr_1fr_1fr] gap-4">
        <div />
        <div
          className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold"
          style={{
            background: "color-mix(in srgb, var(--app-danger) 10%, transparent)",
            color: "var(--app-danger)",
          }}
        >
          <X size={16} aria-hidden="true" />
          {t.cloudHeader[lang]}
        </div>
        <div
          className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold"
          style={{
            background: "color-mix(in srgb, var(--success) 10%, transparent)",
            color: "var(--success)",
          }}
        >
          <Check size={16} aria-hidden="true" />
          {t.chitrikaHeader[lang]}
        </div>
      </div>

      <div className="max-w-4xl mx-auto flex flex-col gap-3">
        {t.rows.map((row, i) => {
          const Icon = ICONS[i] || Database;
          return (
            <motion.div
              key={i}
              initial={reduce ? false : { opacity: 0, y: 20 }}
              animate={reduce || isVisible ? { opacity: 1, y: 0 } : {}}
              transition={
                reduce
                  ? { duration: 0 }
                  : {
                      duration: 0.4,
                      delay: 0.08 * i,
                      ease: [0.25, 0.46, 0.45, 0.94],
                    }
              }
              className="p-4 rounded-xl border"
              style={{
                background: "color-mix(in srgb, var(--app-panel) 60%, transparent)",
                borderColor: "var(--app-border)",
              }}
            >
              <div className="hidden md:grid grid-cols-[1fr_1fr_1fr] gap-4 items-center">
                <div className="flex items-center gap-3">
                  <Icon size={16} style={{ color: "var(--app-accent)" }} aria-hidden="true" />
                  <span
                    className="text-sm font-medium"
                    style={{ color: "var(--app-text)" }}
                  >
                    {row.label[lang]}
                  </span>
                </div>
                <div className="text-sm leading-relaxed px-3" style={{ color: "var(--app-muted)" }}>
                  {row.cloud[lang]}
                </div>
                <div
                  className="text-sm leading-relaxed font-medium px-3"
                  style={{ color: "var(--app-text)" }}
                >
                  {row.chitrika[lang]}
                </div>
              </div>

              <div className="md:hidden flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <Icon size={16} style={{ color: "var(--app-accent)" }} aria-hidden="true" />
                  <span
                    className="text-sm font-semibold"
                    style={{ color: "var(--app-text)" }}
                  >
                    {row.label[lang]}
                  </span>
                </div>
                <div
                  className="flex items-start gap-2 text-sm rounded-lg px-3 py-2"
                  style={{
                    background: "color-mix(in srgb, var(--app-danger) 8%, transparent)",
                    color: "var(--app-muted)",
                  }}
                >
                  <X size={14} className="shrink-0 mt-0.5" style={{ color: "var(--app-danger)" }} aria-hidden="true" />
                  <span>{row.cloud[lang]}</span>
                </div>
                <div
                  className="flex items-start gap-2 text-sm rounded-lg px-3 py-2 font-medium"
                  style={{
                    background: "color-mix(in srgb, var(--success) 8%, transparent)",
                    color: "var(--app-text)",
                  }}
                >
                  <Check size={14} className="shrink-0 mt-0.5" style={{ color: "var(--success)" }} aria-hidden="true" />
                  <span>{row.chitrika[lang]}</span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
