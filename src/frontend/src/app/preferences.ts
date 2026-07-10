import { useEffect, useState } from "react";

const STORAGE_KEY = "chitrika.preferences";

export type ThemeId = "midnight" | "graphite" | "dawn";

export const themes: Array<{
  id: ThemeId;
  label: string;
  colors: [string, string, string];
}> = [
  { id: "midnight", label: "Midnight", colors: ["#121417", "#20252a", "#d38367"] },
  { id: "graphite", label: "Graphite", colors: ["#151617", "#2b2f31", "#7fbea5"] },
  { id: "dawn", label: "Dawn", colors: ["#f7f3ee", "#fffaf4", "#c56b58"] },
];

export interface Preferences {
  theme: ThemeId;
  fontSize: string;
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

  const setPreference = <K extends keyof Preferences>(
    key: K,
    value: Preferences[K]
  ) => {
    setPreferences((prev) => ({ ...prev, [key]: value }));
  };

  return { preferences, setPreference };
}
