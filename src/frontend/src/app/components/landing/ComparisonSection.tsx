import { motion } from "motion/react";
import { Check, X, Server, Shield, Users, Eye, CreditCard, Bell, Database } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";

const ICONS = [Database, Shield, Server, Users, Eye, CreditCard, Bell];

export function ComparisonSection() {
  const { lang } = useLang();
  const t = translations.comparison;

  const prefersReduced = typeof window !== "undefined"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const { ref, isVisible } = useScrollReveal({ skip: prefersReduced });

  return (
    <section ref={ref} className="relative py-24 md:py-32 px-6">
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

      {/* Column headers — visible md+ only */}
      <div className="max-w-4xl mx-auto mb-6 hidden md:grid grid-cols-[1fr_1fr_1fr] gap-4">
        <div />
        <div
          className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold"
          style={{
            background: "color-mix(in srgb, var(--app-danger) 10%, transparent)",
            color: "var(--app-danger)",
          }}
        >
          <X size={16} />
          {t.cloudHeader[lang]}
        </div>
        <div
          className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold"
          style={{
            background: "color-mix(in srgb, var(--success) 10%, transparent)",
            color: "var(--success)",
          }}
        >
          <Check size={16} />
          {t.chitrikaHeader[lang]}
        </div>
      </div>

      {/* Rows */}
      <div className="max-w-4xl mx-auto flex flex-col gap-3">
        {t.rows.map((row, i) => {
          const Icon = ICONS[i] || Database;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={isVisible ? { opacity: 1, y: 0 } : {}}
              transition={{
                duration: 0.4,
                delay: 0.08 * i,
                ease: [0.25, 0.46, 0.45, 0.94],
              }}
              className="p-4 rounded-xl border"
              style={{
                background: "color-mix(in srgb, var(--app-panel) 60%, transparent)",
                borderColor: "var(--app-border)",
              }}
            >
              {/* Desktop: 3-column grid */}
              <div className="hidden md:grid grid-cols-[1fr_1fr_1fr] gap-4 items-center">
                <div className="flex items-center gap-3">
                  <Icon size={16} style={{ color: "var(--app-accent)" }} />
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

              {/* Mobile: stacked vertical card */}
              <div className="md:hidden flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <Icon size={16} style={{ color: "var(--app-accent)" }} />
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
                  <X size={14} className="shrink-0 mt-0.5" style={{ color: "var(--app-danger)" }} />
                  <span>{row.cloud[lang]}</span>
                </div>
                <div
                  className="flex items-start gap-2 text-sm rounded-lg px-3 py-2 font-medium"
                  style={{
                    background: "color-mix(in srgb, var(--success) 8%, transparent)",
                    color: "var(--app-text)",
                  }}
                >
                  <Check size={14} className="shrink-0 mt-0.5" style={{ color: "var(--success)" }} />
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
