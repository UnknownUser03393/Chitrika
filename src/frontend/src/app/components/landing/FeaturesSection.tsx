import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Heart, Brain, Activity, Users, Shield, Infinity as InfinityIcon, ArrowRight } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

const ICONS = [Heart, Brain, Activity, Users, Shield, InfinityIcon];

const TAB_IDS = [
  "feature-tab-emotions",
  "feature-tab-memory",
  "feature-tab-heartbeat",
  "feature-tab-characters",
  "feature-tab-local",
  "feature-tab-yours",
] as const;

const PANEL_IDS = [
  "feature-panel-emotions",
  "feature-panel-memory",
  "feature-panel-heartbeat",
  "feature-panel-characters",
  "feature-panel-local",
  "feature-panel-yours",
] as const;

const EMOTION_DIMS = [
  { key: "joy" as const, value: 0.82, color: "#f59e0b" },
  { key: "trust" as const, value: 0.71, color: "#4ade80" },
  { key: "anticipation" as const, value: 0.55, color: "#60a5fa" },
  { key: "surprise" as const, value: 0.34, color: "#c084fc" },
  { key: "sadness" as const, value: 0.18, color: "#94a3b8" },
  { key: "fear" as const, value: 0.08, color: "#f87171" },
];

const CHAR_META = [
  { name: "Alvia", color: "var(--app-accent)", roleKey: "companion" as const },
  { name: "Riku", color: "#60a5fa", roleKey: "study" as const },
  { name: "Mira", color: "#c084fc", roleKey: "muse" as const },
  { name: "Soren", color: "#4ade80", roleKey: "coach" as const },
];

function EmotionPreview({ reduce }: { reduce: boolean }) {
  const { lang } = useLang();
  const p = translations.features.previews.emotion;

  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Heart size={14} style={{ color: "var(--app-accent)" }} aria-hidden="true" />
        <span style={{ color: "var(--app-muted)", fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {p.title[lang]}
        </span>
      </div>
      {EMOTION_DIMS.map((d) => (
        <div key={d.key} className="flex items-center gap-3">
          <span style={{ color: "var(--app-text)", fontSize: "12px", width: "72px", textAlign: "right" }}>
            {p.dims[d.key][lang]}
          </span>
          <div className="flex-1 h-2 rounded-full" style={{ background: "var(--app-elevated)" }}>
            <motion.div
              initial={reduce ? false : { width: 0 }}
              whileInView={{ width: `${d.value * 100}%` }}
              viewport={{ once: true }}
              transition={reduce ? { duration: 0 } : { duration: 0.7, delay: 0.15, ease: "easeOut" }}
              className="h-full rounded-full"
              style={{
                background: d.color,
                width: reduce ? `${d.value * 100}%` : undefined,
              }}
            />
          </div>
          <span style={{ color: "var(--app-muted)", fontSize: "11px", width: "28px" }}>
            {Math.round(d.value * 100)}%
          </span>
        </div>
      ))}
    </div>
  );
}

function MemoryPreview({ reduce }: { reduce: boolean }) {
  const { lang } = useLang();
  const p = translations.features.previews.memory;

  return (
    <div className="space-y-2 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Brain size={14} style={{ color: "var(--app-accent)" }} aria-hidden="true" />
        <span style={{ color: "var(--app-muted)", fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {p.title[lang]}
        </span>
      </div>
      {p.items.map((m, i) => (
        <motion.div
          key={i}
          initial={reduce ? false : { opacity: 0, x: -12 }}
          whileInView={reduce ? undefined : { opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={reduce ? { duration: 0 } : { duration: 0.35, delay: 0.1 * i }}
          className="flex items-start gap-2 px-3 py-2 rounded-lg"
          style={{ background: "var(--app-bg)", border: "1px solid var(--app-border)" }}
        >
          <span style={{ color: "var(--app-accent)", fontSize: "10px", fontWeight: 700, flexShrink: 0 }} aria-hidden="true">
            {String(i + 1).padStart(2, "0")}
          </span>
          <span style={{ color: "var(--app-text)", fontSize: "12px", lineHeight: "1.45" }}>{m[lang]}</span>
        </motion.div>
      ))}
    </div>
  );
}

function HeartbeatPreview({ reduce }: { reduce: boolean }) {
  const { lang } = useLang();
  const p = translations.features.previews.heartbeat;

  return (
    <div className="flex flex-col items-center justify-center gap-4 p-6" style={{ minHeight: "240px" }}>
      <motion.div
        animate={reduce ? undefined : { scale: [1, 1.18, 1, 1.12, 1] }}
        transition={reduce ? undefined : { duration: 2.4, repeat: Infinity, ease: "easeInOut", repeatDelay: 2 }}
        className="w-16 h-16 rounded-full flex items-center justify-center"
        style={{ background: "var(--app-accent-soft)" }}
      >
        <Activity size={28} style={{ color: "var(--app-accent)" }} aria-hidden="true" />
      </motion.div>
      <div className="text-center">
        <div style={{ color: "var(--app-text)", fontSize: "14px", fontWeight: 600 }}>
          {p.title[lang]}
        </div>
        <div style={{ color: "var(--app-muted)", fontSize: "12px" }} className="mt-1">
          {p.body[lang]}
        </div>
      </div>
    </div>
  );
}

function CharactersPreview({ reduce }: { reduce: boolean }) {
  const { lang } = useLang();
  const roles = translations.features.previews.characters.roles;

  return (
    <div className="grid grid-cols-2 gap-3 p-4">
      {CHAR_META.map((c, i) => (
        <motion.div
          key={c.name}
          initial={reduce ? false : { opacity: 0, scale: 0.9 }}
          whileInView={reduce ? undefined : { opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={reduce ? { duration: 0 } : { duration: 0.3, delay: 0.08 * i }}
          className="flex flex-col items-center gap-2 p-4 rounded-xl"
          style={{ background: "var(--app-bg)", border: "1px solid var(--app-border)" }}
        >
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-white"
            style={{ background: c.color, fontSize: "14px", fontWeight: 700 }}
            aria-hidden="true"
          >
            {c.name[0]}
          </div>
          <span style={{ color: "var(--app-text)", fontSize: "13px", fontWeight: 500 }}>{c.name}</span>
          <span style={{ color: "var(--app-muted)", fontSize: "11px" }}>{roles[c.roleKey][lang]}</span>
        </motion.div>
      ))}
    </div>
  );
}

function LocalFirstPreview({ reduce }: { reduce: boolean }) {
  const { lang } = useLang();
  const p = translations.features.previews.localFirst;

  return (
    <div className="flex flex-col items-center justify-center gap-5 p-6" style={{ minHeight: "240px" }}>
      <motion.div
        animate={reduce ? undefined : { rotateY: [0, 180] }}
        transition={reduce ? undefined : { duration: 3, repeat: Infinity, repeatDelay: 1.5, ease: "easeInOut" }}
        className="w-14 h-14 rounded-xl flex items-center justify-center"
        style={{ background: "var(--app-accent-soft)" }}
      >
        <Shield size={26} style={{ color: "var(--success)" }} aria-hidden="true" />
      </motion.div>
      <div className="text-center space-y-2">
        <div style={{ color: "var(--app-text)", fontSize: "14px", fontWeight: 600 }}>
          {p.title[lang]}
        </div>
        <div style={{ color: "var(--app-muted)", fontSize: "12px", lineHeight: "1.55" }}>
          {p.body[lang]}
        </div>
      </div>
    </div>
  );
}

function YoursForeverPreview({ reduce: _reduce }: { reduce: boolean }) {
  const { lang } = useLang();
  const p = translations.features.previews.yoursForever;

  return (
    <div className="flex flex-col items-center justify-center gap-5 p-6" style={{ minHeight: "240px" }}>
      <div
        className="flex items-center gap-2 px-4 py-2 rounded-full"
        style={{ background: "color-mix(in srgb, var(--success) 12%, transparent)", color: "var(--success)" }}
      >
        <InfinityIcon size={16} aria-hidden="true" />
        <span style={{ fontSize: "14px", fontWeight: 700 }}>{p.badge[lang]}</span>
      </div>
      <div className="text-center" style={{ color: "var(--app-muted)", fontSize: "13px", lineHeight: "1.55" }}>
        {p.body[lang]}
        <br />
        <strong style={{ color: "var(--app-text)" }}>{p.strong[lang]}</strong>
      </div>
    </div>
  );
}

const PREVIEWS = [
  EmotionPreview,
  MemoryPreview,
  HeartbeatPreview,
  CharactersPreview,
  LocalFirstPreview,
  YoursForeverPreview,
];

interface FeaturesSectionProps {
  active?: boolean;
  autoPlay?: boolean;
}

export function FeaturesSection({ active, autoPlay = false }: FeaturesSectionProps = {}) {
  const { lang } = useLang();
  const t = translations.features;
  const reduce = usePrefersReducedMotion();
  const { ref, isVisible } = useScrollReveal({ skip: reduce, active });
  const [activeIdx, setActiveIdx] = useState(0);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (!autoPlay || !active) return;

    setActiveIdx(0);
    const interval = window.setInterval(() => {
      setActiveIdx((current) => Math.min(current + 1, t.cards.length - 1));
    }, 1100);

    return () => window.clearInterval(interval);
  }, [active, autoPlay, t.cards.length]);

  const selectTab = useCallback((index: number) => {
    setActiveIdx(index);
    tabRefs.current[index]?.focus();
  }, []);

  const onTabListKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      const count = t.cards.length;
      let next = activeIdx;

      switch (e.key) {
        case "ArrowDown":
        case "ArrowRight":
          e.preventDefault();
          next = (activeIdx + 1) % count;
          break;
        case "ArrowUp":
        case "ArrowLeft":
          e.preventDefault();
          next = (activeIdx - 1 + count) % count;
          break;
        case "Home":
          e.preventDefault();
          next = 0;
          break;
        case "End":
          e.preventDefault();
          next = count - 1;
          break;
        default:
          return;
      }

      selectTab(next);
    },
    [activeIdx, selectTab, t.cards.length],
  );

  const ActivePreview = PREVIEWS[activeIdx] || EmotionPreview;
  const enter = (extra?: { delay?: number; y?: number; x?: number }) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, y: extra?.y ?? 20, x: extra?.x ?? 0 },
          animate: isVisible ? { opacity: 1, y: 0, x: 0 } : {},
          transition: { duration: 0.5, delay: extra?.delay ?? 0 },
        };

  return (
    <section
      ref={ref}
      className="relative py-16 md:py-24 px-6 min-h-full"
      style={{ background: "var(--app-panel)" }}
    >
      <motion.div
        {...enter()}
        className="text-center mb-14 md:mb-20"
      >
        <h2
          className="text-3xl md:text-4xl font-bold tracking-tight"
          style={{ color: "var(--app-text)" }}
        >
          {t.heading[lang]}
        </h2>
        <p className="mt-3 text-lg" style={{ color: "var(--app-muted)" }}>
          {t.subtitle[lang]}
        </p>
      </motion.div>

      {/* Desktop: sticky showcase with tabs */}
      <div className="hidden md:flex max-w-5xl mx-auto gap-10 items-start">
        <div
          role="tablist"
          aria-orientation="vertical"
          aria-label={t.heading[lang]}
          onKeyDown={onTabListKeyDown}
          className="w-[260px] shrink-0 sticky top-8 space-y-1"
        >
          {t.cards.map((card, i) => {
            const Icon = ICONS[i] || Heart;
            const isActive = i === activeIdx;
            return (
              <motion.button
                key={TAB_IDS[i]}
                ref={(el) => {
                  tabRefs.current[i] = el;
                }}
                role="tab"
                id={TAB_IDS[i]}
                aria-selected={isActive}
                aria-controls={PANEL_IDS[i]}
                tabIndex={isActive ? 0 : -1}
                type="button"
                initial={reduce ? false : { opacity: 0, x: -16 }}
                animate={reduce || isVisible ? { opacity: 1, x: 0 } : {}}
                transition={reduce ? { duration: 0 } : { duration: 0.35, delay: 0.06 * i }}
                onClick={() => selectTab(i)}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-colors group"
                style={{
                  background: isActive
                    ? "var(--app-accent-soft)"
                    : "transparent",
                  border: isActive
                    ? "1px solid var(--app-accent)"
                    : "1px solid transparent",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = "var(--app-hover)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = "transparent";
                  }
                }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors"
                  style={{
                    background: isActive ? "var(--app-accent-soft)" : "transparent",
                  }}
                  aria-hidden="true"
                >
                  <Icon
                    size={16}
                    style={{ color: isActive ? "var(--app-accent)" : "var(--app-muted)" }}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div
                    className="text-sm font-semibold truncate"
                    style={{ color: isActive ? "var(--app-text)" : "var(--app-muted)" }}
                  >
                    {card.title[lang]}
                  </div>
                </div>
                {isActive && <ArrowRight size={14} style={{ color: "var(--app-accent)" }} aria-hidden="true" />}
              </motion.button>
            );
          })}
        </div>

        <div className="flex-1 min-w-0">
          <motion.div
            {...enter({ delay: 0.2 })}
            layout="size"
            className="sticky top-8 rounded-2xl overflow-hidden border"
            style={{
              background: "var(--app-panel-strong)",
              borderColor: "var(--app-border)",
              boxShadow: "var(--app-shadow)",
              minHeight: "320px",
            }}
          >
            <div
              className="flex items-center gap-2 px-5 py-3 border-b"
              style={{ borderColor: "var(--app-border)" }}
            >
              <div className="flex gap-1.5" aria-hidden="true">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#ef6a78" }} />
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#f59e0b" }} />
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: "#4ade80" }} />
              </div>
              <span
                className="flex-1 text-center text-xs font-medium"
                style={{ color: "var(--app-muted)" }}
              >
                Chitrika — {t.cards[activeIdx].title[lang]}
              </span>
            </div>

            <div
              role="tabpanel"
              id={PANEL_IDS[activeIdx]}
              aria-labelledby={TAB_IDS[activeIdx]}
            >
              {reduce ? (
                <ActivePreview reduce={reduce} />
              ) : (
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeIdx}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{
                      opacity: { duration: 0.2, ease: "easeOut" },
                      y: { duration: 0.2, ease: "easeOut" },
                      layout: { duration: 0.38, ease: [0.25, 0.46, 0.45, 0.94] },
                    }}
                  >
                    <ActivePreview reduce={reduce} />
                  </motion.div>
                </AnimatePresence>
              )}
            </div>

            <div
              className="px-5 py-4 border-t"
              style={{ borderColor: "var(--app-border)", background: "var(--app-panel)" }}
            >
              <p style={{ color: "var(--app-muted)", fontSize: "13px", lineHeight: "1.6" }}>
                {t.cards[activeIdx].body[lang]}
              </p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Mobile: stacked cards */}
      <div className="md:hidden max-w-lg mx-auto grid gap-4 sm:grid-cols-2">
        {t.cards.map((card, i) => {
          const Icon = ICONS[i] || Heart;
          return (
            <motion.div
              key={i}
              initial={reduce ? false : { opacity: 0, y: 24 }}
              animate={reduce || isVisible ? { opacity: 1, y: 0 } : {}}
              transition={reduce ? { duration: 0 } : { duration: 0.4, delay: 0.08 * i }}
              className="p-5 rounded-xl border"
              style={{
                background: "var(--app-bg)",
                borderColor: "var(--app-border)",
              }}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                style={{ background: "var(--app-accent-soft)" }}
                aria-hidden="true"
              >
                <Icon size={20} style={{ color: "var(--app-accent)" }} />
              </div>
              <h3 className="text-base font-semibold mb-2" style={{ color: "var(--app-text)" }}>
                {card.title[lang]}
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--app-muted)" }}>
                {card.body[lang]}
              </p>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
