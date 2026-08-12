import { useState, useEffect, useMemo } from "react";
import {
  ArrowLeft,
  Moon,
  Sun,
  Globe,
  Trash2,
  Cpu,
  Plus,
  Pencil,
  Eye,
  EyeOff,
  Sliders,
  Brain,
  Puzzle,
  Bug,
  LayoutGrid,
  Check,
  Palette,
  Copy,
  Volume2,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import type { AIModel } from "./mockData";
import {
  fetchCharacters,
  characterToModel,
  createCharacter,
  updateCharacter,
  deleteCharacter,
  fetchProviders,
  createProvider,
  updateProvider,
  deleteProvider,
  fetchSettings,
  updateSettings,
  fetchPlugins,
  fetchProviderTypes,
} from "../services/api";
import type {
  Character,
  LLMProvider,
  LLMProviderCreate,
  LLMProviderUpdate,
  AppSettings,
  PluginInfo,
  ProviderType,
} from "../services/api";
import { CharacterForm } from "./CharacterForm";
import { ProviderForm } from "./ProviderForm";
import { PluginPanel } from "./PluginPanel";
import { CompanionMindView } from "./CompanionMindView";
import { DebugPanel } from "./DebugPanel";
import type { Preferences } from "../preferences";
import { builtinThemes, type Theme } from "../themes";
import { ThemeEditor, ThemePreview } from "./ThemeEditor";
import {
  NavItem,
  SectionLabel,
  SwitchToggle,
} from "./settings/SettingsControls";
import { AppSettingsPanel } from "./settings/AppSettingsPanel";
import { PreferencesSettings } from "./settings/PreferencesSettings";
import { PluginSettings } from "./settings/PluginSettings";

interface Props {
  onBack: () => void;
  showForm?: (form: React.ReactNode | null) => void;
  prefs: Preferences;
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
}
type Category = "main" | "theme" | "preferences" | "tts" | "provider" | "models" | "mind" | "app" | "plugins" | "debug";

export function SettingsView({ onBack, showForm, prefs, setPref }: Props) {
  const [category, setCategory] = useState<Category>("main");
  const [models, setModels] = useState<AIModel[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [providerTypes, setProviderTypes] = useState<ProviderType[]>([]);
  const [loading, setLoading] = useState(false);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);

  // Fetch characters, providers, and settings from backend
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchCharacters(),
      fetchProviders(),
      fetchProviderTypes().catch(() => []),
      fetchSettings().catch(() => null),
      fetchPlugins().catch(() => []),
    ])
      .then(([chars, provs, types, settings, discoveredPlugins]) => {
        setCharacters(chars);
        setModels(chars.map(characterToModel));
        setProviders(provs);
        setProviderTypes(types);
        if (settings) setAppSettings(settings);
        setPlugins(discoveredPlugins);
        setLoading(false);
      })
      .catch(() => {
        // Fall back to empty lists if backend is not available
        setLoading(false);
      });
  }, []);

  const toggleModel = (id: string) => {
    // Optimistic update
    setModels((prev) =>
      prev.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m))
    );
    // Persist to backend
    const model = models.find((m) => m.id === id);
    if (model) {
      updateCharacter(id, { enabled: !model.enabled }).catch(() => {
        // Revert on failure
        setModels((prev) =>
          prev.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m))
        );
      });
    }
  };

  const handleCreateCharacter = async (data: {
    name: string;
    display_name: string;
    personality_prompt: string;
    initials: string;
    color: string;
    provider: string;
  }) => {
    try {
      const created = await createCharacter(data);
      const model = characterToModel(created);
      setCharacters((prev) => [...prev, created]);
      setModels((prev) => [...prev, model]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create character";
      toast.error(msg);
    }
  };

  const handleUpdateCharacter = async (id: string, data: {
    name: string;
    display_name: string;
    personality_prompt: string;
    initials: string;
    color: string;
    provider: string;
  }) => {
    try {
      const updated = await updateCharacter(id, {
        display_name: data.display_name,
        personality_prompt: data.personality_prompt,
        initials: data.initials,
        color: data.color,
        provider: data.provider,
      });
      setCharacters((prev) => prev.map((c) => (c.id === id ? updated : c)));
      setModels((prev) => prev.map((m) => (m.id === id ? characterToModel(updated) : m)));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to update character";
      toast.error(msg);
    }
  };

  const handleDeleteCharacter = async (id: string) => {
    try {
      await deleteCharacter(id);
      setCharacters((prev) => prev.map((c) => (c.id === id ? { ...c, enabled: false } : c)));
      setModels((prev) => prev.map((m) => (m.id === id ? { ...m, enabled: false } : m)));
      toast.success("Character disabled");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to delete character";
      toast.error(msg);
    }
  };

  const handleCreateProvider = async (data: LLMProviderCreate) => {
    try {
      const created = await createProvider(data);
      setProviders((prev) => [...prev, created]);
      toast.success("Provider created");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create provider";
      toast.error(msg);
    }
  };

  const handleUpdateProvider = async (id: string, data: LLMProviderUpdate) => {
    try {
      const updated = await updateProvider(id, data);
      setProviders((prev) => prev.map((p) => (p.id === id ? updated : p)));
      toast.success("Provider updated");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to update provider";
      toast.error(msg);
    }
  };

  const handleDeleteProvider = async (id: string) => {
    try {
      await deleteProvider(id);
      setProviders((prev) => prev.map((p) => (p.id === id ? { ...p, enabled: false } : p)));
      toast.success("Provider disabled");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to delete provider";
      toast.error(msg);
    }
  };

  const handleSaveSettings = async (updates: Partial<AppSettings>) => {
    setSettingsSaving(true);
    try {
      const updated = await updateSettings(updates);
      setAppSettings(updated);
      toast.success("Settings saved");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to save settings";
      toast.error(msg);
    } finally {
      setSettingsSaving(false);
    }
  };

  const navigateTo = (cat: Category) => {
    showForm?.(null);
    setCategory(cat);
  };

  const handleBack = () => {
    showForm?.(null);
    if (category === "main") {
      onBack();
    } else {
      setCategory("main");
    }
  };

  const headerTitle =
    category === "main"
      ? "Settings"
      : category === "theme"
      ? "Theme"
      : category === "preferences"
      ? "Preferences"
      : category === "tts"
      ? "Text to Speech"
      : category === "provider"
      ? "LLM Provider"
      : category === "models"
      ? "Model List"
      : category === "mind"
      ? "Mind & Memory"
      : category === "plugins"
      ? "Plugins"
      : category === "debug"
      ? "Debug"
      : "App Settings";

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3.5 shrink-0"
        style={{ borderBottom: "1px solid #0D1117" }}
      >
        <button
          onClick={handleBack}
          className="p-1 rounded-full hover:bg-white/10 text-[var(--app-accent)] transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <span className="flex-1 text-[var(--app-text)]" style={{ fontSize: "19px", fontWeight: 700 }}>
          {headerTitle}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden relative">
        <AnimatePresence mode="wait">
          {category === "main" && (
            <motion.div
              key="main"
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <MainSettings
                onTheme={() => navigateTo("theme")}
                onPreferences={() => navigateTo("preferences")}
                onTTS={() => navigateTo("tts")}
                onProvider={() => navigateTo("provider")}
                onModels={() => navigateTo("models")}
                onMind={() => navigateTo("mind")}
                onAppSettings={() => navigateTo("app")}
                onPlugins={() => navigateTo("plugins")}
                onDebug={() => navigateTo("debug")}
              />
            </motion.div>
          )}
          {category === "theme" && (
            <motion.div
              key="theme"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <ThemeSettings prefs={prefs} setPref={setPref} showForm={showForm} />
            </motion.div>
          )}
          {category === "preferences" && (
            <motion.div
              key="preferences"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <PreferencesSettings prefs={prefs} setPref={setPref} mode="preferences" />
            </motion.div>
          )}
          {category === "tts" && (
            <motion.div
              key="tts"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <PreferencesSettings prefs={prefs} setPref={setPref} mode="tts" />
            </motion.div>
          )}
          {category === "provider" && (
            <motion.div
              key="provider"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <ProviderSettings
                providers={providers}
                providerTypes={providerTypes}
                onCreate={handleCreateProvider}
                onUpdate={handleUpdateProvider}
                onDelete={handleDeleteProvider}
                showForm={showForm}
              />
            </motion.div>
          )}
          {category === "models" && (
            <motion.div
              key="models"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              {loading ? (
                <div className="py-8 text-center">
                  <div className="flex gap-1.5 justify-center">
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        className="w-2 h-2 rounded-full bg-[var(--app-muted)] animate-bounce"
                        style={{ animationDelay: `${i * 0.15}s` }}
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <ModelListSettings
                  models={models}
                  characters={characters}
                  onToggle={toggleModel}
                  onCreate={handleCreateCharacter}
                  onUpdate={handleUpdateCharacter}
                  onDelete={handleDeleteCharacter}
                  providers={providers}
                  showForm={showForm}
                />
              )}
            </motion.div>
          )}
          {category === "app" && (
            <motion.div
              key="app"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <AppSettingsPanel
                settings={appSettings}
                saving={settingsSaving}
                onSave={handleSaveSettings}
              />
            </motion.div>
          )}
          {category === "mind" && (
            <motion.div
              key="mind"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <CompanionMindSettings
                characters={characters.filter((character) => character.enabled)}
                showForm={showForm}
              />
            </motion.div>
          )}
          {category === "plugins" && (
            <motion.div
              key="plugins"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <PluginSettings
                plugins={plugins}
                onPluginsChange={setPlugins}
                showForm={showForm}
              />
            </motion.div>
          )}
          {category === "debug" && (
            <motion.div
              key="debug"
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 20, opacity: 0 }}
              transition={{ duration: 0.12, ease: "easeOut" }}
              className="w-full overflow-x-hidden"
            >
              <DebugPanel />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/* -- Main settings ----------------------------------------------- */

function MainSettings({
  onTheme,
  onPreferences,
  onTTS,
  onProvider,
  onModels,
  onMind,
  onAppSettings,
  onPlugins,
  onDebug,
}: {
  onTheme: () => void;
  onPreferences: () => void;
  onTTS: () => void;
  onProvider: () => void;
  onModels: () => void;
  onMind: () => void;
  onAppSettings: () => void;
  onPlugins: () => void;
  onDebug: () => void;
}) {
  return (
    <div className="py-2">
      {/* App branding */}
      <div className="flex flex-col items-center py-8 px-4 gap-2">
        <div
          className="rounded-full flex items-center justify-center"
          style={{
            width: "72px",
            height: "72px",
            background: "linear-gradient(135deg, var(--app-accent) 0%, var(--app-accent-strong) 100%)",
          }}
        >
          <span className="text-white" style={{ fontSize: "28px", fontWeight: 800 }}>
            C
          </span>
        </div>
        <span className="text-[var(--app-text)]" style={{ fontSize: "18px", fontWeight: 700 }}>
          Chitrika
        </span>
        <span className="text-[var(--app-muted)]" style={{ fontSize: "13px" }}>
          Version 1.0.0
        </span>
      </div>

      <div className="px-2 space-y-0.5">
        <SectionLabel label="Configuration" />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "var(--app-accent-soft)" }}
            >
              <Palette size={16} className="text-[var(--app-accent)]" />
            </div>
          }
          label="Theme"
          sublabel="Pick, create, and share themes"
          onClick={onTheme}
        />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(79,163,227,0.15)" }}
            >
              <Moon size={16} className="text-[var(--app-accent)]" />
            </div>
          }
          label="Preferences"
          sublabel="Font, messaging, notifications"
          onClick={onPreferences}
        />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(34,197,94,0.15)" }}
            >
              <Volume2 size={16} style={{ color: "#22C55E" }} />
            </div>
          }
          label="Text to Speech"
          sublabel="Voice provider, model, and playback"
          onClick={onTTS}
        />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(16,185,129,0.15)" }}
            >
              <Cpu size={16} style={{ color: "#10B981" }} />
            </div>
          }
          label="LLM Provider"
          sublabel="Configure API connections"
          onClick={onProvider}
        />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(124,58,237,0.15)" }}
            >
              <Globe size={16} style={{ color: "#7C3AED" }} />
            </div>
          }
          label="Model List"
          sublabel="Manage available AI models"
          onClick={onModels}
        />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(236,72,153,0.15)" }}
            >
              <Brain size={16} style={{ color: "#EC4899" }} />
            </div>
          }
          label="Mind & Memory"
          sublabel="Inspect emotion and manage memories"
          onClick={onMind}
        />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(245,158,11,0.15)" }}
            >
              <Sliders size={16} style={{ color: "#F59E0B" }} />
            </div>
          }
          label="App Settings"
          sublabel="Heartbeat, emotion, CORS"
          onClick={onAppSettings}
        />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(14,165,233,0.15)" }}
            >
              <Puzzle size={16} style={{ color: "#0EA5E9" }} />
            </div>
          }
          label="Plugins"
          sublabel="Manage local extensions"
          onClick={onPlugins}
        />
      </div>

      <div className="px-2 mt-3 space-y-0.5">
        <SectionLabel label="Development" />
        <NavItem
          icon={
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "rgba(239,68,68,0.15)" }}
            >
              <Bug size={16} style={{ color: "#EF4444" }} />
            </div>
          }
          label="Debug"
          sublabel="Force actions &amp; test behavior"
          onClick={onDebug}
        />
      </div>

      <div className="px-2 mt-3 space-y-0.5">
        <SectionLabel label="About" />
        <div className="px-3 py-2">
          <p className="text-[var(--app-muted)]" style={{ fontSize: "12px", lineHeight: "1.7" }}>
            Chitrika is a unified AI chat interface that brings together the world's leading
            language models in one place.
          </p>
        </div>
      </div>
    </div>
  );
}

function CompanionMindSettings({
  characters,
  showForm,
}: {
  characters: Character[];
  showForm?: (form: React.ReactNode | null) => void;
}) {
  return (
    <div className="px-2 py-2">
      <SectionLabel label="Companions" />
      {characters.length === 0 ? (
        <p className="px-3 py-8 text-center text-sm text-[var(--app-muted)]">
          Create and enable a character first.
        </p>
      ) : characters.map((character) => (
        <NavItem
          key={character.id}
          icon={
            <div
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
              style={{ background: character.color }}
            >
              {character.initials || character.display_name.slice(0, 1)}
            </div>
          }
          label={character.display_name}
          sublabel="Emotion state, durable facts, and recent context"
          onClick={() => showForm?.(
            <CompanionMindView
              character={character}
              onClose={() => showForm?.(null)}
            />
          )}
        />
      ))}
    </div>
  );
}

/* -- Theme ------------------------------------------------------- */

function ThemeSettings({
  prefs,
  setPref,
  showForm,
}: {
  prefs: Preferences;
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
  showForm?: (form: React.ReactNode | null) => void;
}) {
  return (
    <div className="py-2 px-2 space-y-1.5">
      <SectionLabel label={`Themes (${builtinThemes.length + prefs.customThemes.length})`} />
      <div className="px-1">
        <ThemeGrid prefs={prefs} setPref={setPref} showForm={showForm} />
      </div>
      <p className="px-3 pt-2 text-[var(--app-subtle)]" style={{ fontSize: "11px", lineHeight: 1.5 }}>
        Tap a theme to apply it instantly. Create your own from three colors, then copy its code to share — or paste a code to import one.
      </p>
    </div>
  );
}

/* -- Preferences ------------------------------------------------- */

function ThemeGrid({
  prefs,
  setPref,
  showForm,
}: {
  prefs: Preferences;
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
  showForm?: (form: React.ReactNode | null) => void;
}) {
  const custom = prefs.customThemes;
  const all = [...builtinThemes, ...custom];

  const openEditor = (initial: Theme | null, duplicate = false) => {
    const editable = initial && !initial.builtin && !duplicate;
    showForm?.(
      <ThemeEditor
        initial={initial}
        duplicate={duplicate}
        onClose={() => showForm?.(null)}
        onDelete={
          editable
            ? () => {
                setPref("customThemes", custom.filter((t) => t.id !== initial!.id));
                if (prefs.theme === initial!.id) setPref("theme", "midnight");
                showForm?.(null);
              }
            : undefined
        }
        onSubmit={(theme) => {
          const exists = custom.some((t) => t.id === theme.id);
          setPref(
            "customThemes",
            exists ? custom.map((t) => (t.id === theme.id ? theme : t)) : [...custom, theme],
          );
          setPref("theme", theme.id);
          showForm?.(null);
        }}
      />,
    );
  };

  return (
    <div className="grid grid-cols-2 gap-2.5">
      {all.map((theme) => (
        <ThemeCard
          key={theme.id}
          theme={theme}
          selected={prefs.theme === theme.id}
          onSelect={() => setPref("theme", theme.id)}
          onEdit={theme.builtin ? undefined : () => openEditor(theme)}
          onDuplicate={() => openEditor(theme, true)}
        />
      ))}

      <button
        onClick={() => openEditor(null)}
        className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed text-[var(--app-muted)] hover:text-[var(--app-accent)] hover:border-[var(--app-accent)] transition-colors"
        style={{ borderColor: "var(--app-border)", minHeight: 118 }}
      >
        <Palette size={20} />
        <span style={{ fontSize: "12px", fontWeight: 600 }}>New theme</span>
      </button>
    </div>
  );
}

function ThemeCard({
  theme,
  selected,
  onSelect,
  onEdit,
  onDuplicate,
}: {
  theme: Theme;
  selected: boolean;
  onSelect: () => void;
  onEdit?: () => void;
  onDuplicate: () => void;
}) {
  const SchemeIcon = theme.scheme === "light" ? Sun : Moon;

  return (
    <div className="relative">
      <button
        onClick={onSelect}
        className="w-full rounded-2xl overflow-hidden text-left transition-colors"
        style={{
          border: `2px solid ${selected ? "var(--app-accent)" : "var(--app-border)"}`,
          background: selected ? "var(--app-accent-soft)" : "transparent",
          padding: 4,
        }}
        title={theme.label}
      >
        <div className="rounded-xl overflow-hidden">
          <ThemePreview tokens={theme.tokens} height={84} radiusScale={theme.radiusScale} />
        </div>
        <div className="flex items-center gap-1.5 px-1.5 pt-1.5">
          <SchemeIcon size={12} className="text-[var(--app-muted)] shrink-0" />
          <span
            className="flex-1 truncate text-[var(--app-text)]"
            style={{ fontSize: "12px", fontWeight: 600 }}
          >
            {theme.label}
          </span>
          {selected && <Check size={13} className="text-[var(--app-accent)] shrink-0" />}
        </div>
      </button>
      <div className="absolute top-2 right-2 flex gap-1">
        <button
          onClick={onDuplicate}
          className="p-1 rounded-md text-white/80 hover:text-white transition-colors"
          style={{ background: "rgba(0,0,0,0.35)" }}
          title="Duplicate as a new theme"
        >
          <Copy size={11} />
        </button>
        {onEdit && (
          <button
            onClick={onEdit}
            className="p-1 rounded-md text-white/80 hover:text-white transition-colors"
            style={{ background: "rgba(0,0,0,0.35)" }}
            title="Edit theme"
          >
            <Pencil size={11} />
          </button>
        )}
      </div>
    </div>
  );
}

/* -- LLM Provider ------------------------------------------------ */

const PROVIDER_COLORS: Record<string, string> = {
  "deepseek-local": "#4FA3E3",
  deepseek: "#4FA3E3",
  openai: "#10B981",
  claude: "#7C3AED",
  anthropic: "#7C3AED",
};

function ProviderSettings({
  providers,
  providerTypes,
  onCreate,
  onUpdate,
  onDelete,
  showForm,
}: {
  providers: LLMProvider[];
  providerTypes: ProviderType[];
  onCreate: (data: LLMProviderCreate) => Promise<void>;
  onUpdate: (id: string, data: LLMProviderUpdate) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  showForm?: (form: React.ReactNode | null) => void;
}) {
  const enabled = providers.filter((p) => p.enabled);
  const disabled = providers.filter((p) => !p.enabled);

  const showAddForm = () => {
    showForm?.(
      <ProviderForm
        initial={null}
        onSubmit={async (data) => {
          await onCreate(data as LLMProviderCreate);
          showForm?.(null);
        }}
        onCancel={() => showForm?.(null)}
      />
    );
  };

  const showEditForm = (provider: LLMProvider) => {
    showForm?.(
      <ProviderForm
        initial={provider}
        onSubmit={async (data) => {
          await onUpdate(provider.id, data as LLMProviderUpdate);
          showForm?.(null);
        }}
        onCancel={() => showForm?.(null)}
      />
    );
  };

  return (
    <div className="py-2 px-2 space-y-0.5">
      <SectionLabel label={`Providers (${enabled.length})`} />

      {enabled.length === 0 && disabled.length === 0 && (
        <div className="px-3 py-8 text-center">
          <p className="text-[var(--app-muted)]" style={{ fontSize: "13px" }}>
            No providers configured.
          </p>
          <p className="text-[var(--app-muted)] mt-1" style={{ fontSize: "12px" }}>
            Add one to enable AI chat.
          </p>
        </div>
      )}

      {enabled.map((p) => (
        <ProviderItem
          key={p.id}
          provider={p}
          providerTypes={providerTypes}
          onEdit={() => showEditForm(p)}
          onDelete={() => onDelete(p.id)}
        />
      ))}

      {disabled.length > 0 && (
        <>
          <div className="mt-2">
            <SectionLabel label={`Disabled (${disabled.length})`} color="var(--app-muted)" />
          </div>
          {disabled.map((p) => (
            <ProviderItem
              key={p.id}
              provider={p}
              providerTypes={providerTypes}
              onEdit={() => showEditForm(p)}
              onDelete={() => onDelete(p.id)}
            />
          ))}
        </>
      )}

      <div className="mt-3">
        <button
          onClick={showAddForm}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-[var(--app-border)] text-[var(--app-muted)] hover:text-[var(--app-text)] hover:border-[var(--app-accent)] transition-colors"
          style={{ fontSize: "14px" }}
        >
          <Plus size={16} />
          Add Provider
        </button>
      </div>
    </div>
  );
}

function buildProviderSummary(
  provider: LLMProvider,
  providerType: ProviderType | null,
  showKey: boolean
): string {
  const typeLabel = providerType?.label || provider.provider_type || provider.name;
  const summaryParts = [`Type: ${typeLabel}`];

  const customFields = providerType?.custom_provider_api?.fields || [];
  const customConfig = provider.custom_config || {};
  const summaryFields = customFields.filter((field) => field.summary);

  summaryFields.forEach((field) => {
    const rawValue = customConfig[field.key];
    const value = typeof rawValue === "string" ? rawValue.trim() : "";
    if (value) {
      summaryParts.push(`${field.label}: ${value}`);
    }
  });

  if (customFields.length > 0) {
    const keyField = customFields.find((field) => field.key === "api_key");
    if (keyField) {
      const customKey = typeof customConfig[keyField.key] === "string" ? customConfig[keyField.key].trim() : "";
      const hasKey = customKey !== "" || provider.api_key.trim() !== "";
      summaryParts.push(`${keyField.label}: ${showKey ? (customKey || provider.api_key || "Not set") : hasKey ? "hidden" : "Not set"}`);
    }
    return summaryParts.join(" · ");
  }

  summaryParts.push(`Endpoint: ${provider.base_url || "Not set"}`);
  summaryParts.push(`Model: ${provider.default_model || "Not set"}`);
  summaryParts.push(`Key: ${showKey ? (provider.api_key || "Not set") : provider.api_key ? "hidden" : "Not set"}`);

  return summaryParts.join(" · ");
}

function ProviderItem({
  provider: p,
  providerTypes,
  onEdit,
  onDelete,
}: {
  provider: LLMProvider;
  providerTypes: ProviderType[];
  onEdit: () => void;
  onDelete: () => void;
}) {
  const providerIdentity = p.provider_type || p.name;
  const color = PROVIDER_COLORS[providerIdentity] || "var(--app-accent)";
  const [showKey, setShowKey] = useState(false);
  const providerType = useMemo(
    () => providerTypes.find((item) => item.type === p.provider_type) || null,
    [providerTypes, p.provider_type]
  );
  const summary = buildProviderSummary(p, providerType, showKey);
  const [panelOpen, setPanelOpen] = useState(false);
  const pluginApi =
    providerType?.plugin_api && providerType.plugin_api.endpoints.length > 0
      ? providerType.plugin_api
      : null;

  return (
    <div>
    <div
      className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 transition-colors"
      style={{ opacity: p.enabled ? 1 : 0.5 }}
    >
      {/* Color dot */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
        style={{ background: `${color}26` }}
      >
        <Cpu size={14} style={{ color }} />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
            {p.display_name}
          </span>
          {p.is_default && (
            <span
              className="px-1.5 py-0.5 rounded"
              style={{
                fontSize: "10px",
                fontWeight: 600,
                background: "rgba(79,163,227,0.15)",
                color: "var(--app-accent)",
              }}
            >
              DEFAULT
            </span>
          )}
        </div>
        <div
          className="text-[var(--app-muted)] mt-0.5 break-all"
          style={{ fontSize: "12px", lineHeight: 1.45 }}
        >
          {summary}
        </div>
      </div>

      {/* Actions */}
      {pluginApi && (
        <button
          onClick={(e) => { e.stopPropagation(); setPanelOpen((value) => !value); }}
          className="p-1.5 rounded-lg text-[var(--app-muted)] hover:text-[var(--app-accent)] transition-colors"
          title={panelOpen ? "Hide plugin panel" : "Open plugin panel"}
        >
          <LayoutGrid size={14} />
        </button>
      )}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setShowKey((value) => !value);
        }}
        className="p-1.5 rounded-lg text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
        title={showKey ? "Hide API key" : "Show API key"}
      >
        {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onEdit(); }}
        className="p-1.5 rounded-lg text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
      >
        <Pencil size={14} />
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="p-1.5 rounded-lg hover:bg-red-500/10 text-[var(--app-muted)] hover:text-[var(--app-danger)] transition-colors"
      >
        <Trash2 size={14} />
      </button>
    </div>

    {panelOpen && pluginApi && (
      <div style={{ marginLeft: 44, marginTop: 2 }}>
        <PluginPanel pluginId={p.plugin_id || p.provider_type} api={pluginApi} />
      </div>
    )}
    </div>
  );
}

/* -- Model List -------------------------------------------------- */

function ModelListSettings({
  models,
  characters,
  onToggle,
  onCreate,
  onUpdate,
  onDelete,
  providers,
  showForm,
}: {
  models: AIModel[];
  characters: Character[];
  onToggle: (id: string) => void;
  onCreate: (data: {
    name: string;
    display_name: string;
    personality_prompt: string;
    initials: string;
    color: string;
    provider: string;
  }) => void;
  onUpdate: (id: string, data: {
    name: string;
    display_name: string;
    personality_prompt: string;
    initials: string;
    color: string;
    provider: string;
  }) => void;
  onDelete: (id: string) => void;
  providers: LLMProvider[];
  showForm?: (form: React.ReactNode | null) => void;
}) {
  const enabled = models.filter((m) => m.enabled);
  const disabled = models.filter((m) => !m.enabled);

  const handleShowNewCharacter = () => {
    showForm?.(
      <CharacterForm
        initial={null}
        providers={providers}
        onSubmit={async (data) => {
          await onCreate(data);
          showForm?.(null);
        }}
        onCancel={() => showForm?.(null)}
      />
    );
  };

  const handleEditCharacter = (model: AIModel) => {
    const character = characters.find((c) => c.id === model.id);
    if (!character) return;
    showForm?.(
      <CharacterForm
        initial={character}
        providers={providers}
        onSubmit={async (data) => {
          await onUpdate(model.id, data);
          showForm?.(null);
        }}
        onCancel={() => showForm?.(null)}
      />
    );
  };

  return (
    <div className="py-2 px-2">
      <SectionLabel label={`Active (${enabled.length})`} />
      {enabled.map((m) => (
        <motion.div key={m.id} layout transition={{ duration: 0.25 }}>
          <ModelItem
            model={m}
            onToggle={() => onToggle(m.id)}
            onEdit={() => handleEditCharacter(m)}
            onDelete={() => onDelete(m.id)}
          />
        </motion.div>
      ))}

      {disabled.length > 0 && (
        <>
          <div className="mt-2">
            <SectionLabel label={`Disabled (${disabled.length})`} color="var(--app-muted)" />
          </div>
          {disabled.map((m) => (
            <motion.div key={m.id} layout transition={{ duration: 0.25 }}>
              <ModelItem
                model={m}
                onToggle={() => onToggle(m.id)}
                onEdit={() => handleEditCharacter(m)}
                onDelete={() => onDelete(m.id)}
              />
            </motion.div>
          ))}
        </>
      )}

      {/* New Character button */}
      <div className="mt-3">
        <button
          onClick={handleShowNewCharacter}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-[var(--app-border)] text-[var(--app-muted)] hover:text-[var(--app-text)] hover:border-[var(--app-accent)] transition-colors"
          style={{ fontSize: "14px" }}
        >
          + New Character
        </button>
      </div>
    </div>
  );
}

function ModelItem({
  model,
  onToggle,
  onEdit,
  onDelete,
}: {
  model: AIModel;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 transition-colors">
      {/* Avatar: show image if available, otherwise initials */}
      <motion.div
        className="w-10 h-10 rounded-full flex items-center justify-center text-white shrink-0 overflow-hidden"
        animate={{
          background: model.enabled ? model.color : "#2A3A4A",
          opacity: model.enabled ? 1 : 0.5,
        }}
        transition={{ duration: 0.25 }}
        style={{ fontSize: "14px", fontWeight: 700 }}
      >
        {model.avatar_url ? (
          <img
            src={model.avatar_url}
            alt={model.name}
            className="w-full h-full object-cover"
          />
        ) : (
          model.initials
        )}
      </motion.div>

      <div className="flex-1 min-w-0">
        <motion.div
          className="text-[var(--app-text)] truncate"
          animate={{ opacity: model.enabled ? 1 : 0.5 }}
          transition={{ duration: 0.25 }}
          style={{ fontSize: "14px", fontWeight: 500 }}
        >
          {model.name}
        </motion.div>
        {/* Skill / personality preview */}
        {model.skill ? (
          <div
            className="text-[var(--app-muted)] truncate mt-0.5"
            style={{ fontSize: "12px", lineHeight: "1.3" }}
          >
            {model.skill.slice(0, 60)}
            {model.skill.length > 60 ? "..." : ""}
          </div>
        ) : (
          <div className="text-[var(--app-muted)] truncate" style={{ fontSize: "12px" }}>
            {model.provider}
          </div>
        )}
      </div>

      {/* Edit / Delete / Toggle */}
      <button
        onClick={(e) => { e.stopPropagation(); onEdit(); }}
        className="p-1.5 rounded-lg text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
      >
        <Pencil size={14} />
      </button>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="p-1.5 rounded-lg hover:bg-red-500/10 text-[var(--app-muted)] hover:text-[var(--app-danger)] transition-colors"
      >
        <Trash2 size={14} />
      </button>
      <SwitchToggle checked={model.enabled} onCheckedChange={onToggle} />
    </div>
  );
}
