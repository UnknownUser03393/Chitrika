import { useEffect, useState } from "react";
import {
  applyTheme,
  builtinThemes,
  resolveTheme,
  type Theme,
} from "./themes";

const STORAGE_KEY = "chitrika.preferences";

export type FontSizeId = "Small" | "Medium" | "Large";

export const fontSizeStyles: Record<FontSizeId, {
  body: string;
  label: string;
  meta: string;
  title: string;
  headline: string;
  input: string;
  bubble: string;
}> = {
  Small: {
    body: "13px",
    label: "13px",
    meta: "11px",
    title: "18px",
    headline: "20px",
    input: "13px",
    bubble: "13px",
  },
  Medium: {
    body: "14px",
    label: "14px",
    meta: "12px",
    title: "19px",
    headline: "21px",
    input: "14px",
    bubble: "14px",
  },
  Large: {
    body: "15px",
    label: "15px",
    meta: "13px",
    title: "20px",
    headline: "22px",
    input: "15px",
    bubble: "15px",
  },
};

export type TTSProvider = "openai" | "gptsovits";

export interface TTSPreferences {
  enabled: boolean;
  autoPlay: boolean;
  provider: TTSProvider;
  apiKey: string;
  baseUrl: string;
  model: string;
  voice: string;
  speed: number;
  /** GPT-SoVITS only: reference audio path + its transcription. */
  refAudioPath: string;
  promptText: string;
  textLang: string;
  promptLang: string;
}

export interface Preferences {
  theme: string; // built-in or custom theme id
  customThemes: Theme[];
  fontSize: FontSizeId;
  sendOnEnter: boolean;
  notifications: boolean;
  showTimestamps: boolean;
  streamResponses: boolean;
  tts: TTSPreferences;
  landingSeen: boolean;
}

export const defaultTTSPreferences: TTSPreferences = {
  enabled: false,
  autoPlay: false,
  provider: "openai",
  apiKey: "",
  baseUrl: "https://api.openai.com/v1",
  model: "gpt-4o-mini-tts",
  voice: "alloy",
  speed: 1,
  refAudioPath: "",
  promptText: "",
  textLang: "zh",
  promptLang: "zh",
};

export const defaultPreferences: Preferences = {
  theme: "midnight",
  customThemes: [],
  fontSize: "Medium",
  sendOnEnter: true,
  notifications: true,
  showTimestamps: true,
  streamResponses: true,
  tts: defaultTTSPreferences,
  landingSeen: false,
};

function normalizeCustomThemes(value: unknown): Theme[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (item): item is Theme =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as Theme).id === "string" &&
        typeof (item as Theme).tokens === "object",
    )
    .map((theme) => ({
      ...theme,
      // Themes saved before the radius dimension existed default to 1.
      radiusScale: typeof theme.radiusScale === "number" && theme.radiusScale > 0 ? theme.radiusScale : 1,
    }));
}

function normalizeTheme(value: unknown, customThemes: Theme[]): string {
  if (value === "light") return "dawn"; // legacy id
  const known = new Set([
    ...builtinThemes.map((theme) => theme.id),
    ...customThemes.map((theme) => theme.id),
  ]);
  if (typeof value === "string" && known.has(value)) return value;
  return "midnight";
}

function normalizeFontSize(value: unknown): FontSizeId {
  if (value === "Small" || value === "Medium" || value === "Large") {
    return value;
  }
  return "Medium";
}

function normalizeTTSPreferences(value: unknown): TTSPreferences {
  const raw = typeof value === "object" && value !== null ? value as Partial<TTSPreferences> : {};
  const provider = raw.provider === "gptsovits" ? "gptsovits" : "openai";
  const baseUrl =
    typeof raw.baseUrl === "string" && raw.baseUrl.trim()
      ? raw.baseUrl
      : provider === "gptsovits"
        ? "http://127.0.0.1:9880"
        : defaultTTSPreferences.baseUrl;
  return {
    ...defaultTTSPreferences,
    ...raw,
    provider,
    enabled: typeof raw.enabled === "boolean" ? raw.enabled : defaultTTSPreferences.enabled,
    autoPlay: typeof raw.autoPlay === "boolean" ? raw.autoPlay : defaultTTSPreferences.autoPlay,
    apiKey: typeof raw.apiKey === "string" ? raw.apiKey : "",
    baseUrl,
    model: typeof raw.model === "string" && raw.model.trim() ? raw.model : defaultTTSPreferences.model,
    voice: typeof raw.voice === "string" && raw.voice.trim() ? raw.voice : defaultTTSPreferences.voice,
    speed: typeof raw.speed === "number" && Number.isFinite(raw.speed) ? Math.min(4, Math.max(0.25, raw.speed)) : defaultTTSPreferences.speed,
    refAudioPath: typeof raw.refAudioPath === "string" ? raw.refAudioPath : "",
    promptText: typeof raw.promptText === "string" ? raw.promptText : "",
    textLang: typeof raw.textLang === "string" && raw.textLang.trim() ? raw.textLang : defaultTTSPreferences.textLang,
    promptLang: typeof raw.promptLang === "string" && raw.promptLang.trim() ? raw.promptLang : defaultTTSPreferences.promptLang,
  };
}

export function usePreferences() {
  const [preferences, setPreferences] = useState<Preferences>(() => {
    if (typeof window === "undefined") return defaultPreferences;

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultPreferences;
      const parsed = JSON.parse(raw);
      const customThemes = normalizeCustomThemes(parsed.customThemes);
      return {
        ...defaultPreferences,
        ...parsed,
        customThemes,
        theme: normalizeTheme(parsed.theme, customThemes),
        fontSize: normalizeFontSize(parsed.fontSize),
        tts: normalizeTTSPreferences(parsed.tts),
      };
    } catch {
      return defaultPreferences;
    }
  });

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  }, [preferences]);

  useEffect(() => {
    applyTheme(resolveTheme(preferences.theme, preferences.customThemes));
  }, [preferences.theme, preferences.customThemes]);

  useEffect(() => {
    const font = fontSizeStyles[preferences.fontSize];
    document.documentElement.style.setProperty("--app-font-body", font.body);
    document.documentElement.style.setProperty("--app-font-label", font.label);
    document.documentElement.style.setProperty("--app-font-meta", font.meta);
    document.documentElement.style.setProperty("--app-font-title", font.title);
    document.documentElement.style.setProperty("--app-font-headline", font.headline);
    document.documentElement.style.setProperty("--app-font-input", font.input);
    document.documentElement.style.setProperty("--app-font-bubble", font.bubble);
  }, [preferences.fontSize]);

  const setPreference = <K extends keyof Preferences>(
    key: K,
    value: Preferences[K]
  ) => {
    setPreferences((prev) => ({ ...prev, [key]: value }));
  };

  return { preferences, setPreference };
}
