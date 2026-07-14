import { useEffect, useState } from "react";

const STORAGE_KEY = "chitrika.preferences";

export type ThemeId = "midnight" | "graphite" | "dawn";
export type FontSizeId = "Small" | "Medium" | "Large";

export const themes: Array<{
  id: ThemeId;
  label: string;
  colors: [string, string, string];
}> = [
  { id: "midnight", label: "Midnight", colors: ["#121417", "#20252a", "#d38367"] },
  { id: "graphite", label: "Graphite", colors: ["#151617", "#2b2f31", "#7fbea5"] },
  { id: "dawn", label: "Dawn", colors: ["#f7f3ee", "#fffaf4", "#c56b58"] },
];

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

export interface Preferences {
  theme: ThemeId;
  fontSize: FontSizeId;
  sendOnEnter: boolean;
  notifications: boolean;
  showTimestamps: boolean;
  streamResponses: boolean;
  landingSeen: boolean;
}

export const defaultPreferences: Preferences = {
  theme: "midnight",
  fontSize: "Medium",
  sendOnEnter: true,
  notifications: true,
  showTimestamps: true,
  streamResponses: true,
  landingSeen: false,
};

function normalizeTheme(value: unknown): ThemeId {
  if (value === "graphite" || value === "dawn" || value === "midnight") {
    return value;
  }
  if (value === "light") return "dawn";
  return "midnight";
}

function normalizeFontSize(value: unknown): FontSizeId {
  if (value === "Small" || value === "Medium" || value === "Large") {
    return value;
  }
  return "Medium";
}

export function usePreferences() {
  const [preferences, setPreferences] = useState<Preferences>(() => {
    if (typeof window === "undefined") return defaultPreferences;

    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultPreferences;
      const parsed = JSON.parse(raw);
      return {
        ...defaultPreferences,
        ...parsed,
        theme: normalizeTheme(parsed.theme),
        fontSize: normalizeFontSize(parsed.fontSize),
      };
    } catch {
      return defaultPreferences;
    }
  });

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  }, [preferences]);

  useEffect(() => {
    document.documentElement.dataset.theme = preferences.theme;
    document.documentElement.classList.toggle(
      "dark",
      preferences.theme !== "dawn"
    );
  }, [preferences.theme]);

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
