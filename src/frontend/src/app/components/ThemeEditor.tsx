import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Trash2, Copy, Check, Download, Sparkles, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import {
  auditContrast,
  deriveTokens,
  isHexColor,
  newThemeId,
  parseThemeJson,
  themeToJson,
  type ColorScheme,
  type Theme,
  type ThemeTokens,
} from "../themes";

/* -- Shared mini chat preview ------------------------------------ */

/**
 * Renders a theme as a tiny chat mock — background, an assistant bubble, a user
 * bubble in the accent, and a few text bars — so a card shows exactly what the
 * theme looks like in use.
 */
export function ThemePreview({
  tokens,
  height = 96,
  radiusScale = 1,
}: {
  tokens: ThemeTokens;
  height?: number;
  radiusScale?: number;
}) {
  const bar = (w: number, color: string, opacity = 1) => (
    <span
      style={{ display: "block", height: 4, width: w, borderRadius: 3, background: color, opacity }}
    />
  );

  // Mirror the app's rounded corners; the small (3px) corner stays sharp so the
  // bubble keeps its chat "tail" even as the theme gets rounder.
  const r = Math.round(10 * radiusScale);

  return (
    <div
      style={{
        height,
        background: tokens.bg,
        borderRadius: 12,
        padding: "9px 10px",
        display: "flex",
        flexDirection: "column",
        gap: 7,
        overflow: "hidden",
      }}
    >
      {/* Assistant bubble (left) */}
      <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
        <span
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: tokens.accentSoft,
            flexShrink: 0,
          }}
        />
        <div
          style={{
            background: tokens.assistantBubble,
            border: `1px solid ${tokens.border}`,
            borderRadius: `3px ${r}px ${r}px ${r}px`,
            padding: "6px 8px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
            maxWidth: "72%",
          }}
        >
          {bar(34, tokens.text, 0.85)}
          {bar(22, tokens.muted)}
        </div>
      </div>
      {/* User bubble (right, accent) */}
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div
          style={{
            background: tokens.userBubble,
            borderRadius: `${r}px ${r}px 3px ${r}px`,
            padding: "6px 8px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
            maxWidth: "64%",
          }}
        >
          {bar(28, "#ffffff", 0.92)}
          {bar(18, "#ffffff", 0.6)}
        </div>
      </div>
    </div>
  );
}

/* -- Editor ------------------------------------------------------ */

interface SeedState {
  label: string;
  scheme: ColorScheme;
  base: string;
  text: string;
  accent: string;
  radiusScale: number;
}

const NEW_SEED: SeedState = {
  label: "My theme",
  scheme: "dark",
  base: "#14151d",
  text: "#eef0f8",
  accent: "#ec8468",
  radiusScale: 1,
};

function seedFromTheme(theme: Theme): SeedState {
  return {
    label: theme.label,
    scheme: theme.scheme,
    base: theme.tokens.bg,
    text: theme.tokens.text,
    accent: theme.tokens.accent,
    radiusScale: theme.radiusScale ?? 1,
  };
}

export function ThemeEditor({
  initial,
  duplicate = false,
  onSubmit,
  onDelete,
  onClose,
}: {
  initial: Theme | null;
  /** Seed from `initial` but save as a brand-new theme (used by "Duplicate"). */
  duplicate?: boolean;
  onSubmit: (theme: Theme) => void;
  onDelete?: () => void;
  onClose: () => void;
}) {
  // Editing an existing custom theme reuses its id; duplicating or starting from
  // a built-in always creates a new one.
  const isEdit = !!initial && !initial.builtin && !duplicate;

  const [seed, setSeed] = useState<SeedState>(() => {
    if (!initial) return NEW_SEED;
    const base = seedFromTheme(initial);
    return duplicate ? { ...base, label: `${base.label} copy` } : base;
  });
  // Preserve the source theme's exact tokens until a color/scheme edit — so a
  // built-in's hand-tuned palette survives a duplicate unchanged.
  const [importedTokens, setImportedTokens] = useState<ThemeTokens | null>(
    initial ? initial.tokens : null,
  );
  const [importText, setImportText] = useState("");
  const [copied, setCopied] = useState(false);

  const setSeedField = <K extends keyof SeedState>(key: K, value: SeedState[K]) => {
    setSeed((prev) => ({ ...prev, [key]: value }));
    // A manual color/scheme edit means we can no longer trust imported tokens
    // verbatim; label and radius don't touch the palette, so they're safe.
    if (key !== "label" && key !== "radiusScale") setImportedTokens(null);
  };

  const tokens = useMemo(
    () => importedTokens ?? deriveTokens({ scheme: seed.scheme, base: seed.base, text: seed.text, accent: seed.accent }),
    [importedTokens, seed.scheme, seed.base, seed.text, seed.accent],
  );

  const previewTheme: Theme = {
    id: initial?.id ?? "preview",
    label: seed.label.trim() || "My theme",
    scheme: seed.scheme,
    tokens,
    radiusScale: seed.radiusScale,
    builtin: false,
  };

  const contrastIssues = useMemo(() => auditContrast(tokens).filter((c) => !c.ok), [tokens]);

  const handleSave = () => {
    onSubmit({
      id: isEdit ? initial!.id : newThemeId(),
      label: seed.label.trim() || "My theme",
      scheme: seed.scheme,
      tokens,
      radiusScale: seed.radiusScale,
      builtin: false,
    });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(themeToJson(previewTheme));
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      toast.error("Couldn't copy to clipboard.");
    }
  };

  const handleImport = () => {
    try {
      const parsed = parseThemeJson(importText);
      setSeed({
        label: parsed.label,
        scheme: parsed.scheme,
        base: parsed.tokens.bg,
        text: parsed.tokens.text,
        accent: parsed.tokens.accent,
        radiusScale: parsed.radiusScale,
      });
      setImportedTokens(parsed.tokens);
      setImportText("");
      toast.success(`Loaded "${parsed.label}"`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't read that theme.");
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ background: "var(--app-panel)" }}>
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3.5 shrink-0"
        style={{ borderBottom: "1px solid var(--app-border)" }}
      >
        <button
          onClick={onClose}
          className="p-1 rounded-full hover:bg-white/10 text-[var(--app-accent)] transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <span className="flex-1 text-[var(--app-text)]" style={{ fontSize: "18px", fontWeight: 700 }}>
          {isEdit ? "Edit theme" : "New theme"}
        </span>
        {isEdit && onDelete && (
          <button
            onClick={onDelete}
            className="p-1.5 rounded-lg hover:bg-red-500/10 text-[var(--app-muted)] hover:text-[var(--app-danger)] transition-colors"
            title="Delete theme"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-4">
        {/* Live preview */}
        <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--app-border)" }}>
          <ThemePreview tokens={tokens} height={140} radiusScale={seed.radiusScale} />
        </div>

        {/* Contrast warnings — the UI paints white text on bubbles/buttons, so a
            too-light color leaves text unreadable. Warn, don't block. */}
        {contrastIssues.length > 0 && (
          <div
            className="rounded-2xl px-3.5 py-3 space-y-1.5"
            style={{ background: "var(--app-accent-soft)", border: "1px solid var(--app-danger)" }}
          >
            <div className="flex items-center gap-2 text-[var(--app-danger)]">
              <AlertTriangle size={14} />
              <span style={{ fontSize: "12px", fontWeight: 700 }}>Low contrast</span>
            </div>
            {contrastIssues.map((issue) => (
              <div
                key={issue.label}
                className="flex items-center justify-between text-[var(--app-muted)]"
                style={{ fontSize: "11px" }}
              >
                <span>{issue.label}</span>
                <span style={{ fontFamily: "ui-monospace, monospace" }}>{issue.ratio.toFixed(1)}:1</span>
              </div>
            ))}
            <p className="text-[var(--app-subtle)]" style={{ fontSize: "10px", lineHeight: 1.5 }}>
              Text may be hard to read. Aim for 4.5:1 or higher.
            </p>
          </div>
        )}

        {/* Name */}
        <div>
          <FieldLabel label="Name" />
          <input
            value={seed.label}
            onChange={(e) => setSeedField("label", e.target.value)}
            placeholder="My theme"
            maxLength={40}
            className="w-full rounded-xl px-3 py-2 text-[var(--app-text)] text-sm outline-none"
            style={{ background: "var(--app-elevated)", border: "1px solid var(--app-border)" }}
          />
        </div>

        {/* Scheme */}
        <div>
          <FieldLabel label="Base scheme" />
          <div className="grid grid-cols-2 gap-2">
            {(["dark", "light"] as const).map((option) => {
              const active = seed.scheme === option;
              return (
                <button
                  key={option}
                  onClick={() => setSeedField("scheme", option)}
                  className="rounded-xl px-3 py-2 text-sm capitalize transition-colors"
                  style={{
                    background: active ? "var(--app-accent-soft)" : "var(--app-elevated)",
                    border: `1px solid ${active ? "var(--app-accent)" : "var(--app-border)"}`,
                    color: active ? "var(--app-accent)" : "var(--app-muted)",
                    fontWeight: active ? 600 : 500,
                  }}
                >
                  {option}
                </button>
              );
            })}
          </div>
        </div>

        {/* Color seeds */}
        <div className="space-y-2.5">
          <ColorRow
            label="Background"
            hint="Deepest surface"
            value={seed.base}
            onChange={(v) => setSeedField("base", v)}
          />
          <ColorRow
            label="Text"
            hint="Primary foreground"
            value={seed.text}
            onChange={(v) => setSeedField("text", v)}
          />
          <ColorRow
            label="Accent"
            hint="Highlight / your bubbles"
            value={seed.accent}
            onChange={(v) => setSeedField("accent", v)}
          />
          <p className="text-[var(--app-subtle)] px-1" style={{ fontSize: "11px", lineHeight: 1.5 }}>
            Panels, borders, and muted tones are generated from these three so the whole set stays consistent.
          </p>
        </div>

        {/* Roundness — scales every corner across the app */}
        <div>
          <div className="flex items-center justify-between">
            <FieldLabel label="Roundness" />
            <span
              className="text-[var(--app-muted)]"
              style={{ fontSize: "11px", fontFamily: "ui-monospace, monospace" }}
            >
              {seed.radiusScale.toFixed(1)}×
            </span>
          </div>
          <input
            type="range"
            min={0.5}
            max={2.5}
            step={0.1}
            value={seed.radiusScale}
            onChange={(e) => setSeedField("radiusScale", Number(e.target.value))}
            className="w-full"
            style={{ accentColor: "var(--app-accent)" }}
          />
          <div className="flex justify-between text-[var(--app-subtle)]" style={{ fontSize: "10px" }}>
            <span>Sharp</span>
            <span>Default</span>
            <span>Expressive</span>
          </div>
        </div>

        {/* Share / import */}
        <div className="rounded-2xl bg-white/[0.03] px-3.5 py-3.5 space-y-3">
          <div className="flex items-center gap-2 text-[var(--app-muted)]">
            <Sparkles size={14} />
            <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.6px", textTransform: "uppercase" }}>
              Share
            </span>
          </div>

          <button
            onClick={handleCopy}
            className="w-full flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors"
            style={{ background: "var(--app-elevated)", border: "1px solid var(--app-border)", color: "var(--app-text)" }}
          >
            {copied ? <Check size={15} /> : <Copy size={15} />}
            {copied ? "Copied!" : "Copy theme code"}
          </button>

          <div>
            <FieldLabel label="Import from code" />
            <textarea
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder='Paste a theme code here…'
              rows={3}
              className="w-full rounded-xl px-3 py-2 text-[var(--app-text)] outline-none resize-none"
              style={{ background: "var(--app-elevated)", border: "1px solid var(--app-border)", fontSize: "12px", fontFamily: "ui-monospace, monospace" }}
            />
            <button
              onClick={handleImport}
              disabled={!importText.trim()}
              className="mt-2 w-full flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm transition-colors disabled:opacity-50"
              style={{ background: "var(--app-elevated)", border: "1px solid var(--app-border)", color: "var(--app-text)" }}
            >
              <Download size={15} />
              Load pasted code
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="shrink-0 px-3 py-3 flex gap-2" style={{ borderTop: "1px solid var(--app-border)" }}>
        <button
          onClick={onClose}
          className="flex-1 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors"
          style={{ background: "var(--app-elevated)", color: "var(--app-muted)" }}
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition-colors"
          style={{ background: "var(--app-accent)" }}
        >
          {isEdit ? "Save theme" : "Create theme"}
        </button>
      </div>
    </div>
  );
}

function FieldLabel({ label }: { label: string }) {
  return (
    <div
      className="text-[var(--app-muted)] mb-1.5"
      style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.6px", textTransform: "uppercase" }}
    >
      {label}
    </div>
  );
}

function ColorRow({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [text, setText] = useState(value);

  // Keep the text field in sync when the seed changes from elsewhere (e.g. import).
  useEffect(() => {
    setText(value);
  }, [value]);

  const commit = (raw: string) => {
    setText(raw);
    if (isHexColor(raw)) onChange(raw.trim());
  };

  return (
    <div className="flex items-center gap-3">
      <label
        className="relative shrink-0 rounded-lg overflow-hidden cursor-pointer"
        style={{ width: 40, height: 40, border: "1px solid var(--app-border)" }}
      >
        <span style={{ position: "absolute", inset: 0, background: value }} />
        <input
          type="color"
          value={isHexColor(value) && value.length === 7 ? value : "#000000"}
          onChange={(e) => commit(e.target.value)}
          style={{ opacity: 0, width: "100%", height: "100%", cursor: "pointer" }}
        />
      </label>
      <div className="flex-1 min-w-0">
        <div className="text-[var(--app-text)]" style={{ fontSize: "13px", fontWeight: 500 }}>
          {label}
        </div>
        <div className="text-[var(--app-subtle)]" style={{ fontSize: "11px" }}>
          {hint}
        </div>
      </div>
      <input
        value={text}
        onChange={(e) => commit(e.target.value)}
        onBlur={() => setText(value)}
        spellCheck={false}
        className="w-24 rounded-lg px-2 py-1.5 text-[var(--app-text)] outline-none"
        style={{
          background: "var(--app-elevated)",
          border: `1px solid ${isHexColor(text) ? "var(--app-border)" : "var(--app-danger)"}`,
          fontSize: "12px",
          fontFamily: "ui-monospace, monospace",
        }}
      />
    </div>
  );
}
