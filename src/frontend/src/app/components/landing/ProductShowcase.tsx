import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { Shield, HardDrive, Brain, Check } from "lucide-react";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

const PAUSE_MS = 650;
const MEMORY_GLOW_HOLD_MS = 2500;
const TYPE_MS = 35;

function Typewriter({
  text,
  onDone,
  reducedMotion,
}: {
  text: string;
  onDone?: () => void;
  reducedMotion: boolean;
}) {
  const [displayed, setDisplayed] = useState(reducedMotion ? text : "");
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;
  const doneRef = useRef(false);

  useEffect(() => {
    doneRef.current = false;

    if (reducedMotion) {
      setDisplayed(text);
      return;
    }

    setDisplayed("");
    let index = 0;
    const interval = setInterval(() => {
      index += 1;
      setDisplayed(text.slice(0, index));
      if (index >= text.length) {
        clearInterval(interval);
        if (!doneRef.current) {
          doneRef.current = true;
          onDoneRef.current?.();
        }
      }
    }, TYPE_MS);

    return () => clearInterval(interval);
  }, [text, reducedMotion]);

  return (
    <span aria-label={text}>
      <span aria-hidden="true">
        {displayed}
        {displayed.length < text.length && (
          <span
            className="inline-block w-[2px] h-[1em] align-middle ml-0.5 animate-pulse"
            style={{ background: "var(--app-accent)" }}
          />
        )}
      </span>
    </span>
  );
}

interface ProductShowcaseProps {
  /** Fullpage mode: start demo when this slide becomes active. */
  active?: boolean;
}

export function ProductShowcase({ active }: ProductShowcaseProps = {}) {
  const { lang } = useLang();
  const t = translations.showcase;
  const reduce = usePrefersReducedMotion();
  const sectionRef = useRef<HTMLElement>(null);

  const [hasEntered, setHasEntered] = useState(false);
  /** -1 idle, 0 user typing, 1 alvia1, 2 alvia2 typing, 3 complete */
  const [step, setStep] = useState(-1);
  const [memoryGlow, setMemoryGlow] = useState(false);
  const [playKey, setPlayKey] = useState(0);

  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const schedule = useCallback((fn: () => void, ms: number) => {
    const id = setTimeout(fn, ms);
    timersRef.current.push(id);
  }, []);

  // Enter once: controlled by fullpage `active`, reduced-motion, or IntersectionObserver
  useEffect(() => {
    if (reduce) {
      setHasEntered(true);
      return;
    }

    if (active !== undefined) {
      if (active) setHasEntered(true);
      return;
    }

    const node = sectionRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setHasEntered(true);
          observer.unobserve(node);
        }
      },
      { threshold: 0.25 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [reduce, active]);

  // Start / restart demo when first entered or language changes after enter
  useEffect(() => {
    if (!hasEntered) return;

    clearTimers();

    if (reduce) {
      setStep(3);
      setMemoryGlow(false);
      return;
    }

    setStep(0);
    setMemoryGlow(false);
    setPlayKey((k) => k + 1);

    return () => clearTimers();
  }, [hasEntered, lang, reduce, clearTimers]);

  const onUserDone = useCallback(() => {
    schedule(() => setStep(1), PAUSE_MS);
  }, [schedule]);

  const onAlvia1Done = useCallback(() => {
    schedule(() => {
      setMemoryGlow(true);
      setStep(2);
    }, PAUSE_MS);
  }, [schedule]);

  const onAlvia2Done = useCallback(() => {
    setStep(3);
    schedule(() => setMemoryGlow(false), MEMORY_GLOW_HOLD_MS);
  }, [schedule]);

  const userText = t.messages.user[lang];
  const alvia1Text = t.messages.alvia1[lang];
  const alvia2Text = t.messages.alvia2[lang];

  const revealProps = reduce
    ? {}
    : {
        initial: { opacity: 0, y: 16 } as const,
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: "-80px" as const },
        transition: { duration: 0.5 },
      };

  const chatRevealProps = reduce
    ? {}
    : {
        initial: { opacity: 0, y: 30 } as const,
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: "-60px" as const },
        transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] as const },
      };

  const trustRevealProps = reduce
    ? {}
    : {
        initial: { opacity: 0, y: 12 } as const,
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true },
        transition: { duration: 0.5, delay: 0.5 },
      };

  const msgMotion = (fromRight: boolean) =>
    reduce
      ? {}
      : {
          initial: { opacity: 0, x: fromRight ? 40 : -40 } as const,
          animate: { opacity: 1, x: 0 },
          transition: { duration: 0.35, ease: "easeOut" as const },
        };

  return (
    <section
      ref={sectionRef}
      className="relative py-16 md:py-24 px-6 overflow-hidden min-h-full flex flex-col justify-center"
      style={{
        background: "linear-gradient(180deg, transparent 0%, var(--app-panel) 40%, var(--app-panel) 100%)",
      }}
    >
      <div className="max-w-4xl mx-auto">
        <motion.div {...revealProps} className="text-center mb-10">
          <span
            className="inline-block px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase"
            style={{
              background: "var(--app-accent-soft)",
              color: "var(--app-accent)",
            }}
          >
            {t.label[lang]}
          </span>
        </motion.div>

        <motion.div
          {...chatRevealProps}
          className="relative mx-auto rounded-2xl overflow-hidden shadow-2xl"
          style={{
            background: "var(--app-panel)",
            border: "1px solid var(--app-border)",
            maxWidth: "600px",
            boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
          }}
        >
          <div
            className="flex items-center gap-3 px-5 py-3.5 border-b"
            style={{ borderColor: "var(--app-border)", background: "var(--app-panel-strong)" }}
          >
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-white shrink-0"
              style={{ background: "var(--app-accent)", fontSize: "14px", fontWeight: 700 }}
              aria-hidden="true"
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
                  aria-hidden="true"
                />
                <span style={{ color: "var(--app-muted)", fontSize: "11px" }}>
                  {t.online[lang]}
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
              <HardDrive size={11} aria-hidden="true" />
              {t.local[lang]}
            </div>
          </div>

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
            {hasEntered && step >= 0 && (
              <motion.div {...msgMotion(true)} className="flex justify-end">
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
                    <Typewriter
                      key={`user-${playKey}`}
                      text={userText}
                      onDone={onUserDone}
                      reducedMotion={reduce}
                    />
                  ) : (
                    userText
                  )}
                </div>
              </motion.div>
            )}

            {hasEntered && step >= 1 && (
              <motion.div {...msgMotion(false)} className="flex justify-start gap-2">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0"
                  style={{ background: "var(--app-accent)", fontSize: "11px", fontWeight: 700 }}
                  aria-hidden="true"
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
                    <Typewriter
                      key={`alvia1-${playKey}`}
                      text={alvia1Text}
                      onDone={onAlvia1Done}
                      reducedMotion={reduce}
                    />
                  ) : (
                    alvia1Text
                  )}
                </div>
              </motion.div>
            )}

            {hasEntered && step >= 2 && (
              <motion.div {...msgMotion(false)} className="flex justify-start gap-2">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0"
                  style={{ background: "var(--app-accent)", fontSize: "11px", fontWeight: 700 }}
                  aria-hidden="true"
                >
                  A
                </div>
                <div className="max-w-[75%] space-y-2">
                  {memoryGlow && (
                    <motion.div
                      initial={reduce ? false : { opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="flex items-center gap-1.5 px-2 py-1 rounded-md"
                      style={{
                        background: "color-mix(in srgb, var(--app-accent) 14%, transparent)",
                        fontSize: "11px",
                        color: "var(--app-accent)",
                      }}
                    >
                      <Brain size={12} aria-hidden="true" />
                      {t.memoryRecalled[lang]}
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
                      <Typewriter
                        key={`alvia2-${playKey}`}
                        text={alvia2Text}
                        onDone={onAlvia2Done}
                        reducedMotion={reduce}
                      />
                    ) : (
                      alvia2Text
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>

        <motion.div
          {...trustRevealProps}
          className="flex flex-wrap justify-center gap-6 mt-8"
        >
          <div className="flex items-center gap-2" style={{ color: "var(--app-muted)", fontSize: "13px" }}>
            <Shield size={14} style={{ color: "var(--success)" }} aria-hidden="true" />
            {t.trustTelemetry[lang]}
          </div>
          <div className="flex items-center gap-2" style={{ color: "var(--app-muted)", fontSize: "13px" }}>
            <HardDrive size={14} style={{ color: "var(--success)" }} aria-hidden="true" />
            {t.trustData[lang]}
          </div>
          <div className="flex items-center gap-2" style={{ color: "var(--app-muted)", fontSize: "13px" }}>
            <Check size={14} style={{ color: "var(--success)" }} aria-hidden="true" />
            {t.trustUnshutdownable[lang]}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
