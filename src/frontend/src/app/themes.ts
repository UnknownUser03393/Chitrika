/**
 * Data-driven theme system.
 *
 * A theme is a plain object of color tokens — no CSS files, no backend. This
 * makes themes previewable in a grid, creatable by the user, and shareable as
 * a single JSON blob (the "theme plugin" surface). `applyTheme` injects the
 * tokens as `--app-*` custom properties on <html>, replacing the old
 * `[data-theme=x]` CSS blocks.
 */

export type ColorScheme = "light" | "dark";

export interface ThemeTokens {
  bg: string;
  panel: string;
  panelStrong: string;
  elevated: string;
  border: string;
  text: string;
  muted: string;
  subtle: string;
  accent: string;
  accentStrong: string;
  accentSoft: string; // rgba
  userBubble: string;
  assistantBubble: string;
  danger: string;
  shadow: string; // full CSS box-shadow value
  hover: string; // rgba overlay
}

export interface Theme {
  id: string;
  label: string;
  scheme: ColorScheme;
  tokens: ThemeTokens;
  /**
   * Multiplies the whole Tailwind corner-radius ladder (see theme.css). 1 = the
   * app's default roundness; higher = more rounded ("expressive") everywhere.
   */
  radiusScale: number;
  builtin: boolean;
}

/* -- Color math (pure, hex/rgba in → hex/rgba out) ---------------- */

interface RGB {
  r: number;
  g: number;
  b: number;
}

function parseHex(hex: string): RGB {
  let value = hex.trim().replace(/^#/, "");
  if (value.length === 3) {
    value = value
      .split("")
      .map((c) => c + c)
      .join("");
  }
  const int = parseInt(value, 16);
  return { r: (int >> 16) & 255, g: (int >> 8) & 255, b: int & 255 };
}

function toHex({ r, g, b }: RGB): string {
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
  return "#" + [r, g, b].map((n) => clamp(n).toString(16).padStart(2, "0")).join("");
}

/** Linear blend between two hex colors. `t=0` → `a`, `t=1` → `b`. */
function mix(a: string, b: string, t: number): string {
  const ca = parseHex(a);
  const cb = parseHex(b);
  return toHex({
    r: ca.r + (cb.r - ca.r) * t,
    g: ca.g + (cb.g - ca.g) * t,
    b: ca.b + (cb.b - ca.b) * t,
  });
}

function rgba(hex: string, alpha: number): string {
  const { r, g, b } = parseHex(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function isHexColor(value: string): boolean {
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value.trim());
}

/* -- Contrast audit (WCAG relative luminance) -------------------- */

function relativeLuminance(hex: string): number {
  const { r, g, b } = parseHex(hex);
  const channel = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** WCAG contrast ratio (1–21) between two hex colors. */
export function contrastRatio(a: string, b: string): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

export interface ContrastCheck {
  label: string;
  ratio: number;
  ok: boolean;
}

// The app paints white text on user bubbles and accent-filled buttons, so those
// pairings are the ones that actually break when a theme's colors are too light.
const ON_ACCENT_TEXT = "#ffffff";

/** Audit the color pairings the UI really renders; used to warn in the editor. */
export function auditContrast(tokens: ThemeTokens): ContrastCheck[] {
  const check = (label: string, fg: string, bg: string, min: number): ContrastCheck => {
    if (!isHexColor(fg) || !isHexColor(bg)) return { label, ratio: min, ok: true };
    const ratio = contrastRatio(fg, bg);
    return { label, ratio, ok: ratio >= min };
  };
  return [
    check("Body text on background", tokens.text, tokens.bg, 4.5),
    check("White text on your bubble", ON_ACCENT_TEXT, tokens.userBubble, 4.5),
    check("White text on accent buttons", ON_ACCENT_TEXT, tokens.accent, 4.5),
    check("Muted text on background", tokens.muted, tokens.bg, 3),
  ];
}

/* -- Derive a full token ladder from 3 base colors --------------- */

export interface ThemeSeed {
  scheme: ColorScheme;
  base: string; // darkest (dark) / lightest (light) surface
  text: string;
  accent: string;
}

const TINT = "#ffffff";
const SHADE = "#0a0a0a";

/**
 * Generate a consistent surface/text/accent ladder from a seed. Dark schemes
 * lighten surfaces toward white; light schemes brighten the panel and darken
 * the deeper surfaces. Keeps custom themes on the same rhythm as the built-ins.
 */
export function deriveTokens(seed: ThemeSeed): ThemeTokens {
  const { scheme, base, text, accent } = seed;
  const dark = scheme === "dark";

  const panel = dark ? mix(base, TINT, 0.05) : mix(base, TINT, 0.6);
  const panelStrong = dark ? mix(base, TINT, 0.09) : mix(base, SHADE, 0.05);
  const elevated = dark ? mix(base, TINT, 0.13) : mix(base, SHADE, 0.09);
  const border = dark ? mix(base, TINT, 0.2) : mix(base, SHADE, 0.16);

  return {
    bg: base,
    panel,
    panelStrong,
    elevated,
    border,
    text,
    muted: mix(text, base, 0.4),
    subtle: mix(text, base, 0.6),
    accent,
    accentStrong: dark ? mix(accent, TINT, 0.22) : mix(accent, SHADE, 0.22),
    accentSoft: rgba(accent, dark ? 0.15 : 0.13),
    userBubble: dark ? mix(accent, SHADE, 0.18) : accent,
    assistantBubble: panelStrong,
    danger: dark ? "#f0697a" : "#c2415a",
    shadow: dark ? "0 22px 54px rgba(0, 0, 0, 0.45)" : "0 16px 40px rgba(90, 62, 44, 0.16)",
    hover: dark ? "rgba(255, 255, 255, 0.06)" : "rgba(44, 37, 33, 0.06)",
  };
}

/* -- Built-in catalog (9 themes, each a mood of the companion) --- */

function builtin(
  id: string,
  label: string,
  scheme: ColorScheme,
  tokens: ThemeTokens,
  radiusScale = 1,
): Theme {
  return { id, label, scheme, tokens, radiusScale, builtin: true };
}

export const builtinThemes: Theme[] = [
  builtin("midnight", "Midnight", "dark", {
    bg: "#14151d",
    panel: "#1c1e29",
    panelStrong: "#232634",
    elevated: "#2b2f40",
    border: "#383d51",
    text: "#eef0f8",
    muted: "#9aa2ba",
    subtle: "#6a7186",
    accent: "#ec8468",
    accentStrong: "#ffa384",
    accentSoft: "rgba(236, 132, 104, 0.15)",
    userBubble: "#c96a52",
    assistantBubble: "#232634",
    danger: "#f0697a",
    shadow: "0 22px 54px rgba(6, 8, 18, 0.5)",
    hover: "rgba(255, 255, 255, 0.06)",
  }),
  builtin("graphite", "Graphite", "dark", {
    bg: "#131517",
    panel: "#1b1e20",
    panelStrong: "#23262a",
    elevated: "#2a2e32",
    border: "#373c42",
    text: "#eef1f2",
    muted: "#9aa2a6",
    subtle: "#6b7378",
    accent: "#5ec9b0",
    accentStrong: "#86e3cd",
    accentSoft: "rgba(94, 201, 176, 0.15)",
    userBubble: "#3a8676",
    assistantBubble: "#23262a",
    danger: "#ef6a78",
    shadow: "0 22px 54px rgba(0, 0, 0, 0.45)",
    hover: "rgba(255, 255, 255, 0.06)",
  }),
  builtin("nocturne", "Nocturne", "dark", {
    bg: "#17121b",
    panel: "#1f1826",
    panelStrong: "#271f30",
    elevated: "#30273b",
    border: "#40354d",
    text: "#f2ecf5",
    muted: "#b0a3bb",
    subtle: "#7d7089",
    accent: "#e069a4",
    accentStrong: "#f58cc0",
    accentSoft: "rgba(224, 105, 164, 0.15)",
    userBubble: "#b3527f",
    assistantBubble: "#271f30",
    danger: "#f0697a",
    shadow: "0 22px 54px rgba(10, 4, 16, 0.5)",
    hover: "rgba(255, 255, 255, 0.06)",
  }),
  builtin("abyss", "Abyss", "dark", {
    bg: "#0f1719",
    panel: "#162225",
    panelStrong: "#1c2b2f",
    elevated: "#233438",
    border: "#2f4449",
    text: "#e9f2f2",
    muted: "#93a8a8",
    subtle: "#647878",
    accent: "#3fc7d4",
    accentStrong: "#6fe0eb",
    accentSoft: "rgba(63, 199, 212, 0.15)",
    userBubble: "#2f8791",
    assistantBubble: "#1c2b2f",
    danger: "#ef6a78",
    shadow: "0 22px 54px rgba(0, 6, 8, 0.5)",
    hover: "rgba(255, 255, 255, 0.06)",
  }),
  builtin("fern", "Fern", "dark", {
    bg: "#12160f",
    panel: "#1a2015",
    panelStrong: "#21281a",
    elevated: "#283020",
    border: "#37432c",
    text: "#eef2e6",
    muted: "#a3ac95",
    subtle: "#727b63",
    accent: "#d99a3c",
    accentStrong: "#f0b85c",
    accentSoft: "rgba(217, 154, 60, 0.15)",
    userBubble: "#9c7028",
    assistantBubble: "#21281a",
    danger: "#ef7272",
    shadow: "0 22px 54px rgba(4, 8, 2, 0.5)",
    hover: "rgba(255, 255, 255, 0.06)",
  }),
  builtin("dawn", "Dawn", "light", {
    bg: "#f5efe6",
    panel: "#fffdf9",
    panelStrong: "#f0e7d9",
    elevated: "#ebe0d0",
    border: "#e0d2be",
    text: "#2c2521",
    muted: "#786c5f",
    subtle: "#a89a89",
    accent: "#c8623f",
    accentStrong: "#a5462a",
    accentSoft: "rgba(200, 98, 63, 0.13)",
    userBubble: "#c8623f",
    assistantBubble: "#fffdf9",
    danger: "#c2415a",
    shadow: "0 16px 40px rgba(90, 62, 40, 0.16)",
    hover: "rgba(44, 37, 33, 0.06)",
  }),
  builtin("sakura", "Sakura", "light", {
    bg: "#faf3f4",
    panel: "#fffdfd",
    panelStrong: "#f5e7ea",
    elevated: "#f0dde1",
    border: "#e6cdd3",
    text: "#33262a",
    muted: "#82707a",
    subtle: "#b09aa2",
    accent: "#d75c7e",
    accentStrong: "#b23e60",
    accentSoft: "rgba(215, 92, 126, 0.12)",
    userBubble: "#d75c7e",
    assistantBubble: "#fffdfd",
    danger: "#c2415a",
    shadow: "0 16px 40px rgba(120, 60, 80, 0.14)",
    hover: "rgba(51, 38, 42, 0.06)",
  }),
  builtin("mist", "Mist", "light", {
    bg: "#eef1f5",
    panel: "#ffffff",
    panelStrong: "#e2e8f0",
    elevated: "#d9e1ea",
    border: "#cbd5e1",
    text: "#1e293b",
    muted: "#64748b",
    subtle: "#94a3b8",
    accent: "#4f7cc4",
    accentStrong: "#2f5da3",
    accentSoft: "rgba(79, 124, 196, 0.12)",
    userBubble: "#4f7cc4",
    assistantBubble: "#ffffff",
    danger: "#c2415a",
    shadow: "0 16px 40px rgba(40, 60, 90, 0.14)",
    hover: "rgba(30, 41, 59, 0.06)",
  }),
  builtin("sand", "Sand", "light", {
    bg: "#f2ece0",
    panel: "#fdfaf3",
    panelStrong: "#eae1d0",
    elevated: "#e3d8c3",
    border: "#d6c8ae",
    text: "#2e2820",
    muted: "#7a6f5c",
    subtle: "#a89a80",
    accent: "#7d8c3f",
    accentStrong: "#5f6d28",
    accentSoft: "rgba(125, 140, 63, 0.13)",
    userBubble: "#6e7d33",
    assistantBubble: "#fdfaf3",
    danger: "#c2415a",
    shadow: "0 16px 40px rgba(90, 80, 50, 0.15)",
    hover: "rgba(46, 40, 32, 0.06)",
  }),
];

/* -- Apply / resolve --------------------------------------------- */

const TOKEN_TO_VAR: Record<keyof ThemeTokens, string> = {
  bg: "--app-bg",
  panel: "--app-panel",
  panelStrong: "--app-panel-strong",
  elevated: "--app-elevated",
  border: "--app-border",
  text: "--app-text",
  muted: "--app-muted",
  subtle: "--app-subtle",
  accent: "--app-accent",
  accentStrong: "--app-accent-strong",
  accentSoft: "--app-accent-soft",
  userBubble: "--app-user-bubble",
  assistantBubble: "--app-assistant-bubble",
  danger: "--app-danger",
  shadow: "--app-shadow",
  hover: "--app-hover",
};

/** Inject a theme's tokens as CSS custom properties on <html>. */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  (Object.keys(TOKEN_TO_VAR) as Array<keyof ThemeTokens>).forEach((key) => {
    root.style.setProperty(TOKEN_TO_VAR[key], theme.tokens[key]);
  });
  root.style.setProperty("--app-radius-scale", String(theme.radiusScale ?? 1));
  root.style.colorScheme = theme.scheme;
  root.classList.toggle("dark", theme.scheme === "dark");
  root.dataset.theme = theme.id;
}

/** Look up a theme by id across built-ins + user themes, with a safe fallback. */
export function resolveTheme(id: string, customThemes: Theme[] = []): Theme {
  return (
    [...builtinThemes, ...customThemes].find((theme) => theme.id === id) ??
    builtinThemes[0]
  );
}

/* -- Import / validate a shared theme JSON ----------------------- */

const TOKEN_KEYS = Object.keys(TOKEN_TO_VAR) as Array<keyof ThemeTokens>;

/**
 * Parse and validate a theme JSON blob (from paste/import). Returns the theme
 * or throws with a human-readable reason. Imported themes are always marked
 * non-builtin and get a fresh id to avoid clobbering the catalog.
 */
export function parseThemeJson(raw: string): Theme {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error("That's not valid JSON.");
  }
  if (typeof data !== "object" || data === null) {
    throw new Error("Theme must be a JSON object.");
  }
  const obj = data as Record<string, unknown>;
  const label = typeof obj.label === "string" && obj.label.trim() ? obj.label.trim() : "Imported theme";
  const scheme: ColorScheme = obj.scheme === "light" ? "light" : "dark";
  const tokens = obj.tokens;
  if (typeof tokens !== "object" || tokens === null) {
    throw new Error("Theme is missing its color tokens.");
  }
  const t = tokens as Record<string, unknown>;
  const missing = TOKEN_KEYS.filter((key) => typeof t[key] !== "string");
  if (missing.length > 0) {
    throw new Error(`Theme is missing tokens: ${missing.join(", ")}`);
  }
  const cleanTokens = {} as ThemeTokens;
  TOKEN_KEYS.forEach((key) => {
    cleanTokens[key] = String(t[key]);
  });
  const radiusScale =
    typeof obj.radiusScale === "number" && obj.radiusScale > 0 ? obj.radiusScale : 1;
  return { id: newThemeId(), label, scheme, tokens: cleanTokens, radiusScale, builtin: false };
}

/** Serialize a theme to a shareable JSON string (drops volatile fields). */
export function themeToJson(theme: Theme): string {
  return JSON.stringify(
    { label: theme.label, scheme: theme.scheme, radiusScale: theme.radiusScale, tokens: theme.tokens },
    null,
    2,
  );
}

let idCounter = 0;
/** Stable-unique id for a user theme. */
export function newThemeId(): string {
  idCounter += 1;
  return `custom-${Date.now()}-${idCounter}`;
}
