import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Heart, Brain, Activity, Users, Shield, Infinity as InfinityIcon, ArrowRight } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";

const ICONS = [Heart, Brain, Activity, Users, Shield, InfinityIcon];

/** Preview panels — each feature gets its own visual */
function EmotionPreview() {
  const dims = [
    { label: "Joy", value: 0.82, color: "#f59e0b" },
    { label: "Trust", value: 0.71, color: "#4ade80" },
    { label: "Anticipation", value: 0.55, color: "#60a5fa" },
    { label: "Surprise", value: 0.34, color: "#c084fc" },
    { label: "Sadness", value: 0.18, color: "#94a3b8" },
    { label: "Fear", value: 0.08, color: "#f87171" },
  ];

  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Heart size={14} style={{ color: "var(--app-accent)" }} />
        <span style={{ color: "var(--app-muted)", fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Emotional State
        </span>
      </div>
      {dims.map((d) => (
        <div key={d.label} className="flex items-center gap-3">
          <span style={{ color: "var(--app-text)", fontSize: "12px", width: "72px", textAlign: "right" }}>
            {d.label}
          </span>
          <div className="flex-1 h-2 rounded-full" style={{ background: "var(--app-elevated)" }}>
            <motion.div
              initial={{ width: 0 }}
              whileInView={{ width: `${d.value * 100}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.15, ease: "easeOut" }}
              className="h-full rounded-full"
              style={{ background: d.color }}
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

function MemoryPreview() {
  const memories = [
    "User mentioned they like rainy days — last Tuesday",
    "Favorite tea: jasmine, no sugar",
    "Talks about their cat 'Mochi' often",
    "Gets anxious before Monday meetings",
  ];

  return (
    <div className="space-y-2 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Brain size={14} style={{ color: "var(--app-accent)" }} />
        <span style={{ color: "var(--app-muted)", fontSize: "12px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Memory Store
        </span>
      </div>
      {memories.map((m, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -12 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.35, delay: 0.1 * i }}
          className="flex items-start gap-2 px-3 py-2 rounded-lg"
          style={{ background: "var(--app-bg)", border: "1px solid var(--app-border)" }}
        >
          <span style={{ color: "var(--app-accent)", fontSize: "10px", fontWeight: 700, flexShrink: 0 }}>
            {String(i + 1).padStart(2, "0")}
          </span>
          <span style={{ color: "var(--app-text)", fontSize: "12px", lineHeight: "1.45" }}>{m}</span>
        </motion.div>
      ))}
    </div>
  );
}

function HeartbeatPreview() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 p-6" style={{ minHeight: "240px" }}>
      {/* Pulsing heart */}
      <motion.div
        animate={{ scale: [1, 1.18, 1, 1.12, 1] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut", repeatDelay: 2 }}
        className="w-16 h-16 rounded-full flex items-center justify-center"
        style={{ background: "var(--app-accent-soft)" }}
      >
        <Activity size={28} style={{ color: "var(--app-accent)" }} />
      </motion.div>
      <div className="text-center">
        <div style={{ color: "var(--app-text)", fontSize: "14px", fontWeight: 600 }}>
          Thinking of you
        </div>
        <div style={{ color: "var(--app-muted)", fontSize: "12px" }} className="mt-1">
          Alvia noticed you've been quiet for a few hours. She sent a check-in message at 3:42 PM.
        </div>
      </div>
    </div>
  );
}

function CharactersPreview() {
  const chars = [
    { name: "Alvia", color: "var(--app-accent)", role: "Companion" },
    { name: "Riku", color: "#60a5fa", role: "Study partner" },
    { name: "Mira", color: "#c084fc", role: "Creative muse" },
    { name: "Soren", color: "#4ade80", role: "Fitness coach" },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 p-4">
      {chars.map((c, i) => (
        <motion.div
          key={c.name}
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.3, delay: 0.08 * i }}
          className="flex flex-col items-center gap-2 p-4 rounded-xl"
          style={{ background: "var(--app-bg)", border: "1px solid var(--app-border)" }}
        >
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-white"
            style={{ background: c.color, fontSize: "14px", fontWeight: 700 }}
          >
            {c.name[0]}
          </div>
          <span style={{ color: "var(--app-text)", fontSize: "13px", fontWeight: 500 }}>{c.name}</span>
          <span style={{ color: "var(--app-muted)", fontSize: "11px" }}>{c.role}</span>
        </motion.div>
      ))}
    </div>
  );
}

function LocalFirstPreview() {
  return (
    <div className="flex flex-col items-center justify-center gap-5 p-6" style={{ minHeight: "240px" }}>
      <motion.div
        animate={{ rotateY: [0, 180] }}
        transition={{ duration: 3, repeat: Infinity, repeatDelay: 1.5, ease: "easeInOut" }}
        className="w-14 h-14 rounded-xl flex items-center justify-center"
        style={{ background: "var(--app-accent-soft)" }}
      >
        <Shield size={26} style={{ color: "var(--success)" }} />
      </motion.div>
      <div className="text-center space-y-2">
        <div style={{ color: "var(--app-text)", fontSize: "14px", fontWeight: 600 }}>
          All data stays here
        </div>
        <div style={{ color: "var(--app-muted)", fontSize: "12px", lineHeight: "1.55" }}>
          No cloud servers. No telemetry. No one watching. Your conversations live on your hard drive and nowhere else.
        </div>
      </div>
    </div>
  );
}

function YoursForeverPreview() {
  return (
    <div className="flex flex-col items-center justify-center gap-5 p-6" style={{ minHeight: "240px" }}>
      <div
        className="flex items-center gap-2 px-4 py-2 rounded-full"
        style={{ background: "color-mix(in srgb, var(--success) 12%, transparent)", color: "var(--success)" }}
      >
        <InfinityIcon size={16} />
        <span style={{ fontSize: "14px", fontWeight: 700 }}>No subscription</span>
      </div>
      <div className="text-center" style={{ color: "var(--app-muted)", fontSize: "13px", lineHeight: "1.55" }}>
        No monthly fees. No service that disappears overnight. <br />
        <strong style={{ color: "var(--app-text)" }}>Once you have Chitrika, it's yours.</strong>
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

export function FeaturesSection() {
  const { lang } = useLang();
  const t = translations.features;
  const [activeIdx, setActiveIdx] = useState(0);

  const prefersReduced = typeof window !== "undefined"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const { ref, isVisible } = useScrollReveal({ skip: prefersReduced });

  const ActivePreview = PREVIEWS[activeIdx] || EmotionPreview;

  return (
    <section
      ref={ref}
      className="relative py-24 md:py-32 px-6"
      style={{ background: "var(--app-panel)" }}
    >
      {/* Section header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={isVisible ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.5 }}
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

      {/* --- Desktop: sticky showcase --- */}
      <div className="hidden md:flex max-w-5xl mx-auto gap-10 items-start">
        {/* Left: feature nav (sticky) */}
        <div className="w-[260px] shrink-0 sticky top-8 space-y-1">
          {t.cards.map((card, i) => {
            const Icon = ICONS[i] || Heart;
            const isActive = i === activeIdx;
            return (
              <motion.button
                key={i}
                initial={{ opacity: 0, x: -16 }}
                animate={isVisible ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.35, delay: 0.06 * i }}
                onClick={() => setActiveIdx(i)}
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
                {isActive && <ArrowRight size={14} style={{ color: "var(--app-accent)" }} />}
              </motion.button>
            );
          })}
        </div>

        {/* Right: preview panel */}
        <div className="flex-1 min-w-0">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isVisible ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="sticky top-8 rounded-2xl overflow-hidden border"
            style={{
              background: "var(--app-panel-strong)",
              borderColor: "var(--app-border)",
              boxShadow: "var(--app-shadow)",
              minHeight: "320px",
            }}
          >
            {/* Preview header */}
            <div
              className="flex items-center gap-2 px-5 py-3 border-b"
              style={{ borderColor: "var(--app-border)" }}
            >
              <div className="flex gap-1.5">
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

            {/* Preview content */}
            <AnimatePresence mode="wait">
              <motion.div
                key={activeIdx}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
              >
                <ActivePreview />
              </motion.div>
            </AnimatePresence>

            {/* Description footer */}
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

      {/* --- Mobile: stacked cards (fallback) --- */}
      <div className="md:hidden max-w-lg mx-auto grid gap-4 sm:grid-cols-2">
        {t.cards.map((card, i) => {
          const Icon = ICONS[i] || Heart;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 24 }}
              animate={isVisible ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: 0.08 * i }}
              className="p-5 rounded-xl border"
              style={{
                background: "var(--app-bg)",
                borderColor: "var(--app-border)",
              }}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
                style={{ background: "var(--app-accent-soft)" }}
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
