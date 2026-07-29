import { useState } from "react";
import { motion } from "motion/react";
import { Github, Zap, Download, Check, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useLang } from "./LanguageContext";
import { translations } from "./i18n";
import { useScrollReveal } from "./useScrollReveal";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";
import { importDoubao } from "../../services/api";

interface Props {
  onGetStarted: () => void;
  active?: boolean;
  promo?: boolean;
}

export function FooterSection({ onGetStarted, active, promo = false }: Props) {
  const { lang } = useLang();
  const f = translations.footer;
  const reduce = usePrefersReducedMotion();
  const { ref, isVisible } = useScrollReveal({ skip: reduce, active });

  // Import state
  const [importing, setImporting] = useState(false);
  const [importDone, setImportDone] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const handleImport = async () => {
    setImporting(true);
    setImportError(null);
    try {
      const result = await importDoubao("D:/Development/PythonProject/agentmsg-shify");
      setImportDone(true);
      toast.success(
        lang === "zh"
          ? `导入了 ${result.imported_conversations} 个对话`
          : `Imported ${result.imported_conversations} conversations`
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Import failed";
      setImportError(msg);
      toast.error(msg);
    } finally {
      setImporting(false);
    }
  };

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
          {promo
            ? lang === "zh"
              ? "模型会更迭。记忆不该归零。"
              : "Models change. Memories shouldn't reset."
            : f.heading[lang]}
        </h2>
        <p
          className="mt-6 text-lg max-w-lg mx-auto"
          style={{ color: "var(--app-muted)" }}
        >
          {promo
            ? lang === "zh"
              ? "让陪伴，不止发生在对话框里。"
              : "Let companionship continue beyond the chat box."
            : f.subtitle[lang]}
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
          {promo ? (lang === "zh" ? "开始一段不会被带走的关系" : "Start a relationship that stays") : f.cta[lang]}
        </button>

        {promo && (
          <div className="mx-auto mt-10 max-w-4xl">
            <p
              className="text-sm md:text-base font-medium"
              style={{ color: "var(--app-muted)" }}
            >
              {lang === "zh"
                ? "你的关系不必重来：支持豆包、通义千问与 DeepSeek 对话无痛迁移。"
                : "Your relationship does not need to restart: migrate conversations from Doubao, Qwen, and DeepSeek."}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2" aria-label="Supported migration sources">
              {["豆包 Doubao", "通义千问 Qwen", "DeepSeek"].map((provider) => (
                <span
                  key={provider}
                  className="rounded-full border px-3 py-1 text-xs font-semibold"
                  style={{
                    borderColor: "var(--app-border)",
                    background: "color-mix(in srgb, var(--app-panel-strong) 82%, transparent)",
                    color: "var(--app-text)",
                  }}
                >
                  {provider}
                </span>
              ))}
            </div>

            {/* One-click Doubao import */}
            <div className="mt-6 flex justify-center">
              <button
                onClick={handleImport}
                disabled={importing || importDone}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold transition-all hover:scale-[1.03] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
                style={{
                  background: importDone
                    ? "color-mix(in srgb, #6EC668 18%, transparent)"
                    : importError
                      ? "color-mix(in srgb, #e05555 14%, transparent)"
                      : "color-mix(in srgb, var(--app-accent) 15%, transparent)",
                  border: `1px solid ${
                    importDone ? "#6EC668" : importError ? "#e05555" : "var(--app-accent)"
                  }`,
                  color: importDone ? "#6EC668" : importError ? "#e05555" : "var(--app-accent)",
                }}
              >
                {importing ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : importDone ? (
                  <Check size={16} />
                ) : importError ? (
                  <AlertCircle size={16} />
                ) : (
                  <Download size={16} />
                )}
                {importing
                  ? (lang === "zh" ? "导入中..." : "Importing...")
                  : importDone
                    ? (lang === "zh" ? "导入完成" : "Imported")
                    : importError
                      ? (lang === "zh" ? "重试" : "Retry")
                      : (lang === "zh" ? "一键导入豆包对话" : "One-click Doubao Import")}
              </button>
              {importError && (
                <p className="mt-2 text-xs" style={{ color: "#e05555" }}>
                  {importError}
                </p>
              )}
            </div>

            <div className="mx-auto mt-8 max-w-2xl text-left">
              <GitHubSummaryCard
                owner="UnknownUser03393"
                repo="Chitrika"
                description="Desktop-native AI companion with persistent memory, evolving emotion, and proactive presence."
                mark="C"
                stats={[["1", "Contributor"], ["0", "Issues"], ["0", "Stars"], ["0", "Forks"]]}
              />
            </div>
          </div>
        )}
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

function GitHubSummaryCard({
  owner,
  repo,
  description,
  mark,
  stats,
}: {
  owner: string;
  repo: string;
  description: string;
  mark: string;
  stats: Array<[string, string]>;
}) {
  return (
    <a
      href="https://github.com/UnknownUser03393/Chitrika"
      target="_blank"
      rel="noreferrer"
      className="group relative block overflow-hidden rounded-2xl border px-7 pb-8 pt-7 transition-all hover:-translate-y-1"
      style={{
        borderColor: "rgba(15, 23, 42, 0.08)",
        background: "#f8f9fb",
        boxShadow: "0 22px 55px rgba(0, 0, 0, 0.22)",
      }}
    >
      <div className="flex min-h-28 items-start justify-between gap-6">
        <div className="min-w-0">
          <h3 className="text-2xl leading-tight tracking-tight" style={{ color: "#2f343b" }}>
            <span className="font-normal">{owner}/</span>
            <strong className="font-extrabold">{repo}</strong>
          </h3>
          <p className="mt-5 max-w-md text-sm leading-6" style={{ color: "#737b8a" }}>
            {description}
          </p>
        </div>
        <div
          className="grid h-16 w-16 shrink-0 place-items-center rounded-xl text-2xl font-black"
          style={{ background: "#eceef1", color: "#d08d73" }}
          aria-hidden="true"
        >
          {mark}
        </div>
      </div>
      <div className="mt-7 flex items-end gap-4">
        <div className="grid min-w-0 flex-1 grid-cols-4 gap-3">
          {stats.map(([value, label], index) => (
            <div key={label} className="min-w-0">
              <div className="flex items-center gap-1.5 text-base font-semibold" style={{ color: "#303640" }}>
                <span className="text-sm" style={{ color: "#7c8799" }} aria-hidden="true">
                  {index === 0 ? "♙" : index === 1 ? "⊙" : index === 2 ? "☆" : "⑂"}
                </span>
                {value}
              </div>
              <div className="mt-1 truncate text-[11px]" style={{ color: "#7c8799" }}>
                {label}
              </div>
            </div>
          ))}
        </div>
        <Github className="mb-1 shrink-0" size={24} style={{ color: "#8a96aa" }} />
      </div>
      <div
        className="absolute inset-x-0 bottom-0 h-1.5"
        style={{ background: "linear-gradient(90deg, #2286b9 0%, #2286b9 78%, #d08d73 78%, #d08d73 98%, #f0b64d 98%)" }}
      />
    </a>
  );
}
