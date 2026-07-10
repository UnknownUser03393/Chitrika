import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import type { Lang } from "./i18n";

const STORAGE_KEY = "chitrika.landingLang";

function detectLang(): Lang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "zh" || stored === "en") return stored;
  } catch { /* SSR or blocked storage */ }

  // Detect browser language
  if (typeof navigator !== "undefined") {
    const nav = navigator.language.toLowerCase();
    if (nav.startsWith("zh")) return "zh";
  }

  return "en";
}

interface Ctx {
  lang: Lang;
  toggle: () => void;
}

const LanguageContext = createContext<Ctx>({ lang: "en", toggle: () => {} });

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(detectLang);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch { /* noop */ }
    document.documentElement.lang = lang;
  }, [lang]);

  const toggle = () => setLang((prev) => (prev === "en" ? "zh" : "en"));

  return (
    <LanguageContext.Provider value={{ lang, toggle }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLang() {
  return useContext(LanguageContext);
}
