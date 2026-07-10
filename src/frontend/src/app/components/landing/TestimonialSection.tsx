import { motion } from "motion/react";
import { Quote } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";

export function TestimonialSection() {
  const { lang } = useLang();
  const t = translations.testimonials;

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
      </div>

      {/* Main quote */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={isVisible ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="max-w-2xl mx-auto mb-16 text-center"
      >
        <Quote
          size={40}
          className="mx-auto mb-6 opacity-30"
          style={{ color: "var(--app-accent)" }}
        />
        <blockquote
          className="text-xl md:text-2xl leading-relaxed font-medium"
          style={{ color: "var(--app-text)" }}
        >
          &ldquo;{t.main.text[lang]}&rdquo;
        </blockquote>
        <div className="mt-6">
          <span className="text-sm font-semibold" style={{ color: "var(--app-accent)" }}>
            {t.main.author[lang]}
          </span>
          <span className="text-sm ml-2" style={{ color: "var(--app-muted)" }}>
            — {t.main.role[lang]}
          </span>
        </div>
      </motion.div>

      {/* Supporting quotes */}
      <div className="max-w-4xl mx-auto grid gap-6 md:grid-cols-3">
        {t.supporting.map((q, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 30 }}
            animate={isVisible ? { opacity: 1, y: 0 } : {}}
            transition={{
              duration: 0.5,
              delay: 0.3 + 0.12 * i,
              ease: [0.25, 0.46, 0.45, 0.94],
            }}
            className="p-5 rounded-xl border"
            style={{
              background: "color-mix(in srgb, var(--app-panel) 60%, transparent)",
              borderColor: "var(--app-border)",
            }}
          >
            <p className="text-sm leading-relaxed italic" style={{ color: "var(--app-muted)" }}>
              &ldquo;{q.text[lang]}&rdquo;
            </p>
            <span
              className="block mt-3 text-xs font-semibold"
              style={{ color: "var(--app-accent)" }}
            >
              — {q.author[lang]}
            </span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
