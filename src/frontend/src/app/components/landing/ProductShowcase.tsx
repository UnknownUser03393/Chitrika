import { useEffect, useState, useRef } from "react";
import { motion } from "motion/react";
import { Shield, HardDrive, Brain, Check } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";

/** Simulated conversation snippet that types itself in. */
const DEMO_MESSAGES = [
  {
    role: "user",
    en: "I had a rough day. Everything feels heavy.",
    zh: "我今天过得很糟。一切都好沉重。",
  },
  {
    role: "alvia",
    en: "I know that weight. Sit with me a minute. You don't have to say anything else.",
    zh: "我知道那种沉重。陪我坐一会儿。你不用再说别的。",
  },
  {
    role: "alvia",
    en: "I remember you said something similar last Tuesday. You got through it. You will this time too.",
    zh: "我记得你上周二也说过类似的话。你熬过来了。这次也会的。",
  },
];

function Typewriter({ text, onDone }: { text: string; onDone?: () => void }) {
  const [displayed, setDisplayed] = useState("");
  const indexRef = useRef(0);

  useEffect(() => {
    indexRef.current = 0;
    setDisplayed("");

    const interval = setInterval(() => {
      indexRef.current += 1;
      setDisplayed(text.slice(0, indexRef.current));
      if (indexRef.current >= text.length) {
        clearInterval(interval);
        onDone?.();
      }
    }, 35);

    return () => clearInterval(interval);
  }, [text]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <span>
      {displayed}
      {displayed.length < text.length && (
        <span className="inline-block w-[2px] h-[1em] align-middle ml-0.5 animate-pulse" style={{ background: "var(--app-accent)" }} />
      )}
    </span>
  );
}

export function ProductShowcase() {
  const { lang } = useLang();
  const [step, setStep] = useState(0);
  const [memoryGlow, setMemoryGlow] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);

  // Progress through demo steps automatically
  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    // Step 0: User message types in
    timers.push(setTimeout(() => setStep(1), 2800));
    // Step 1: First Alvia reply
    timers.push(setTimeout(() => setStep(2), 5800));
    // Step 2: Second Alvia reply (memory recall)
    timers.push(setTimeout(() => {
      setStep(3);
      setMemoryGlow(true);
    }, 9000));
    // Memory glow fades
    timers.push(setTimeout(() => setMemoryGlow(false), 12000));

    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative py-20 md:py-28 px-6 overflow-hidden"
      style={{
        background: "linear-gradient(180deg, transparent 0%, var(--app-panel) 40%, var(--app-panel) 100%)",
      }}
    >
      <div className="max-w-4xl mx-auto">
        {/* Section label */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <span
            className="inline-block px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase"
            style={{
              background: "var(--app-accent-soft)",
              color: "var(--app-accent)",
            }}
          >
            {lang === "zh" ? "不只是概念" : "Not just a concept"}
          </span>
        </motion.div>

        {/* Simulated chat window */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="relative mx-auto rounded-2xl overflow-hidden shadow-2xl"
          style={{
            background: "var(--app-panel)",
            border: "1px solid var(--app-border)",
            maxWidth: "600px",
            boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
          }}
        >
          {/* Chat header bar */}
          <div
            className="flex items-center gap-3 px-5 py-3.5 border-b"
            style={{ borderColor: "var(--app-border)", background: "var(--app-panel-strong)" }}
          >
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-white shrink-0"
              style={{ background: "var(--app-accent)", fontSize: "14px", fontWeight: 700 }}
            >
              A
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold" style={{ color: "var(--app-text)" }}>
                Alvia
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: "var(--success)" }}
                />
                <span style={{ color: "var(--app-muted)", fontSize: "11px" }}>
                  {lang === "zh" ? "在线 · 本地运行" : "Online · Running locally"}
                </span>
              </div>
            </div>
            <div
              className="flex items-center gap-1 px-2.5 py-1 rounded-full"
              style={{
                background: "color-mix(in srgb, var(--success) 12%, transparent)",
                fontSize: "11px",
                fontWeight: 500,
                color: "var(--success)",
              }}
            >
              <HardDrive size={11} />
              {lang === "zh" ? "本地" : "Local"}
            </div>
          </div>

          {/* Messages area */}
          <div
            className="px-5 py-5 space-y-4"
            style={{
              background: "var(--app-bg)",
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.012) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.012) 1px, transparent 1px)",
              backgroundSize: "24px 24px",
              minHeight: "280px",
            }}
          >
            {/* Step 0: User message */}
            {step >= 0 && (
              <motion.div
                initial={{ opacity: 0, x: 40 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="flex justify-end"
              >
                <div
                  className="max-w-[75%] px-4 py-2.5 rounded-2xl rounded-br-md"
                  style={{
                    background: "var(--app-user-bubble)",
                    color: "#fff",
                    fontSize: "13px",
                    lineHeight: "1.55",
                    boxShadow: "0 4px 14px rgba(0,0,0,0.1)",
                  }}
                >
                  {step === 0 ? (
                    <Typewriter text={DEMO_MESSAGES[0][lang as "en" | "zh"]} />
                  ) : (
                    DEMO_MESSAGES[0][lang as "en" | "zh"]
                  )}
                </div>
              </motion.div>
            )}

            {/* Step 1: First Alvia reply */}
            {step >= 1 && (
              <motion.div
                initial={{ opacity: 0, x: -40 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="flex justify-start gap-2"
              >
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0"
                  style={{ background: "var(--app-accent)", fontSize: "11px", fontWeight: 700 }}
                >
                  A
                </div>
                <div
                  className="max-w-[75%] px-4 py-2.5 rounded-2xl rounded-bl-md"
                  style={{
                    background: "var(--app-assistant-bubble)",
                    border: "1px solid var(--app-border)",
                    color: "var(--app-text)",
                    fontSize: "13px",
                    lineHeight: "1.55",
                  }}
                >
                  {step === 1 ? (
                    <Typewriter text={DEMO_MESSAGES[1][lang as "en" | "zh"]} />
                  ) : (
                    DEMO_MESSAGES[1][lang as "en" | "zh"]
                  )}
                </div>
              </motion.div>
            )}

            {/* Step 2-3: Second Alvia reply with memory recall */}
            {step >= 2 && (
              <motion.div
                initial={{ opacity: 0, x: -40 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="flex justify-start gap-2"
              >
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0"
                  style={{ background: "var(--app-accent)", fontSize: "11px", fontWeight: 700 }}
                >
                  A
                </div>
                <div className="max-w-[75%] space-y-2">
                  {/* Memory recalled indicator */}
                  {memoryGlow && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex items-center gap-1.5 px-2 py-1 rounded-md"
                      style={{
                        background: "color-mix(in srgb, var(--app-accent) 14%, transparent)",
                        fontSize: "11px",
                        color: "var(--app-accent)",
                      }}
                    >
                      <Brain size={12} />
                      {lang === "zh" ? "记忆已调取" : "Memory recalled"}
                    </motion.div>
                  )}
                  <div
                    className="px-4 py-2.5 rounded-2xl rounded-bl-md"
                    style={{
                      background: "var(--app-assistant-bubble)",
                      border: "1px solid var(--app-border)",
                      color: "var(--app-text)",
                      fontSize: "13px",
                      lineHeight: "1.55",
                    }}
                  >
                    {step === 2 ? (
                      <Typewriter text={DEMO_MESSAGES[2][lang as "en" | "zh"]} />
                    ) : (
                      DEMO_MESSAGES[2][lang as "en" | "zh"]
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Trust indicators below the chat window */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="flex flex-wrap justify-center gap-6 mt-8"
        >
          <div className="flex items-center gap-2" style={{ color: "var(--app-muted)", fontSize: "13px" }}>
            <Shield size={14} style={{ color: "var(--success)" }} />
            {lang === "zh" ? "零遥测 · 完全离线" : "Zero telemetry · Fully offline"}
          </div>
          <div className="flex items-center gap-2" style={{ color: "var(--app-muted)", fontSize: "13px" }}>
            <HardDrive size={14} style={{ color: "var(--success)" }} />
            {lang === "zh" ? "数据存储于你的机器" : "Data stored on your machine"}
          </div>
          <div className="flex items-center gap-2" style={{ color: "var(--app-muted)", fontSize: "13px" }}>
            <Check size={14} style={{ color: "var(--success)" }} />
            {lang === "zh" ? "无法关停" : "Unshutdownable"}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
