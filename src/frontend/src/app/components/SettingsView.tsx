import { useState, useEffect } from "react";
import {
  ArrowLeft,
  Moon,
  Sun,
  Globe,
  Type,
  CornerDownLeft,
  Bell,
  Clock,
  Trash2,
  ChevronRight,
  Cpu,
  Plus,
  Pencil,
  Zap,
  Eye,
  EyeOff,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import * as Switch from "@radix-ui/react-switch";
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
} from "../services/api";
import type { Character, LLMProvider, LLMProviderCreate, LLMProviderUpdate } from "../services/api";
import { CharacterForm } from "./CharacterForm";
import { ProviderForm } from "./ProviderForm";
import { themes } from "../preferences";
import type { Preferences, ThemeId } from "../preferences";

interface Props {
  onBack: () => void;
  showForm?: (form: React.ReactNode | null) => void;
  prefs: Preferences;
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
}

type Category = "main" | "preferences" | "provider" | "models";

export function SettingsView({ onBack, showForm, prefs, setPref }: Props) {
  const [category, setCategory] = useState<Category>("main");
  const [models, setModels] = useState<AIModel[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch characters and providers from backend
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchCharacters(),
      fetchProviders(),
    ])
      .then(([chars, provs]) => {
        setCharacters(chars);
        setModels(chars.map(characterToModel));
        setProviders(provs);
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
      : category === "preferences"
      ? "Preferences"
      : category === "provider"
      ? "LLM Provider"
      : "Model List";

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
                onPreferences={() => navigateTo("preferences")}
                onProvider={() => navigateTo("provider")}
                onModels={() => navigateTo("models")}
              />
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
              <PreferencesSettings prefs={prefs} setPref={setPref} />
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
        </AnimatePresence>
      </div>
    </div>
  );
}

/* -- Shared primitives ------------------------------------------- */

function SectionLabel({ label, color = "var(--app-accent)" }: { label: string; color?: string }) {
  return (
    <div className="px-3 py-1.5">
      <span
        style={{
          fontSize: "11px",
          fontWeight: 700,
          letterSpacing: "0.8px",
          textTransform: "uppercase",
          color,
        }}
      >
        {label}
      </span>
    </div>
  );
}

function NavItem({
  icon,
  label,
  sublabel,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  sublabel?: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 transition-colors text-left"
    >
      {icon}
      <div className="flex-1 min-w-0">
        <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
          {label}
        </div>
        {sublabel && (
          <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
            {sublabel}
          </div>
        )}
      </div>
      <ChevronRight size={16} className="text-[var(--app-muted)]" />
    </button>
  );
}

function SwitchToggle({
  checked,
  onCheckedChange,
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  return (
    <Switch.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      className="relative inline-flex cursor-pointer rounded-full outline-none shrink-0 transition-colors"
      style={{ width: "36px", height: "20px", background: checked ? "var(--app-accent)" : "var(--app-border)" }}
    >
      <Switch.Thumb
        className="block rounded-full bg-white shadow-sm transition-transform"
        style={{
          width: "16px",
          height: "16px",
          marginTop: "2px",
          transform: checked ? "translateX(18px)" : "translateX(2px)",
        }}
      />
    </Switch.Root>
  );
}

/* -- Main settings ----------------------------------------------- */

function MainSettings({
  onPreferences,
  onProvider,
  onModels,
}: {
  onPreferences: () => void;
  onProvider: () => void;
  onModels: () => void;
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
              style={{ background: "rgba(79,163,227,0.15)" }}
            >
              <Moon size={16} className="text-[var(--app-accent)]" />
            </div>
          }
          label="Preferences"
          sublabel="Theme, font, messaging"
          onClick={onPreferences}
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

/* -- Preferences ------------------------------------------------- */

function PreferencesSettings({
  prefs,
  setPref,
}: {
  prefs: Preferences;
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
}) {
  return (
    <div className="py-2 px-2 space-y-0.5">
      <SectionLabel label="Appearance" />

      {/* Theme */}
      <div className="flex items-start gap-3 px-3 py-3 rounded-xl hover:bg-white/5">
        {prefs.theme === "dawn" ? (
          <Sun size={18} className="text-[var(--app-muted)] shrink-0 mt-1" />
        ) : (
          <Moon size={18} className="text-[var(--app-muted)] shrink-0 mt-1" />
        )}
        <div className="flex-1 min-w-0">
          <div className="text-[var(--app-text)]" style={{ fontSize: "14px" }}>
            Theme
          </div>
          <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
            {themes.find((theme) => theme.id === prefs.theme)?.label}
          </div>
        </div>
        <div className="flex gap-1.5">
          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => setPref("theme", theme.id as ThemeId)}
              className="h-9 w-12 rounded-lg border transition-all"
              style={{
                background: theme.colors[0],
                borderColor:
                  prefs.theme === theme.id
                    ? "var(--app-accent)"
                    : "var(--app-border)",
                boxShadow:
                  prefs.theme === theme.id
                    ? "0 0 0 2px var(--app-accent-soft)"
                    : "none",
              }}
              title={theme.label}
            >
              <span className="flex h-full w-full overflow-hidden rounded-[6px]">
                {theme.colors.map((color) => (
                  <span key={color} className="flex-1" style={{ background: color }} />
                ))}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Font Size */}
      <div className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5">
        <Type size={18} className="text-[var(--app-muted)] shrink-0" />
        <span className="flex-1 text-[var(--app-text)]" style={{ fontSize: "14px" }}>
          Font Size
        </span>
        <div className="flex rounded-lg overflow-hidden" style={{ background: "var(--app-elevated)" }}>
          {["Small", "Medium", "Large"].map((s) => (
            <button
              key={s}
              onClick={() => setPref("fontSize", s)}
              className="px-2.5 py-1 transition-colors"
              style={{
                background: prefs.fontSize === s ? "var(--app-accent)" : "transparent",
                color: prefs.fontSize === s ? "white" : "var(--app-muted)",
                fontSize: "11px",
                fontWeight: 500,
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Language */}
      <div className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5">
        <Globe size={18} className="text-[var(--app-muted)] shrink-0" />
        <span className="flex-1 text-[var(--app-text)]" style={{ fontSize: "14px" }}>
          Language
        </span>
        <span className="text-[var(--app-muted)]" style={{ fontSize: "13px" }}>
          English
        </span>
        <ChevronRight size={14} className="text-[var(--app-muted)]" />
      </div>

      <div className="mt-2">
        <SectionLabel label="Messaging" />
      </div>

      {/* Stream Responses */}
      <div className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5">
        <Zap size={18} className="text-[var(--app-muted)] shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-[var(--app-text)]" style={{ fontSize: "14px" }}>
            Stream Responses
          </div>
          <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
            Show replies as they arrive
          </div>
        </div>
        <SwitchToggle
          checked={prefs.streamResponses}
          onCheckedChange={(v) => setPref("streamResponses", v)}
        />
      </div>

      {/* Send on Enter */}
      <div className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5">
        <CornerDownLeft size={18} className="text-[var(--app-muted)] shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-[var(--app-text)]" style={{ fontSize: "14px" }}>
            Send on Enter
          </div>
          <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
            Shift+Enter for new line
          </div>
        </div>
        <SwitchToggle
          checked={prefs.sendOnEnter}
          onCheckedChange={(v) => setPref("sendOnEnter", v)}
        />
      </div>

      {/* Show Timestamps */}
      <div className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5">
        <Clock size={18} className="text-[var(--app-muted)] shrink-0" />
        <span className="flex-1 text-[var(--app-text)]" style={{ fontSize: "14px" }}>
          Show Timestamps
        </span>
        <SwitchToggle
          checked={prefs.showTimestamps}
          onCheckedChange={(v) => setPref("showTimestamps", v)}
        />
      </div>

      <div className="mt-2">
        <SectionLabel label="Notifications" />
      </div>

      {/* Notifications */}
      <div className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5">
        <Bell size={18} className="text-[var(--app-muted)] shrink-0" />
        <span className="flex-1 text-[var(--app-text)]" style={{ fontSize: "14px" }}>
          Push Notifications
        </span>
        <SwitchToggle
          checked={prefs.notifications}
          onCheckedChange={(v) => setPref("notifications", v)}
        />
      </div>

      <div className="mt-2">
        <SectionLabel label="Danger Zone" color="#EF4444" />
      </div>

      <button className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-red-500/10 transition-colors">
        <Trash2 size={18} className="text-[var(--app-danger)] shrink-0" />
        <span className="text-[var(--app-danger)]" style={{ fontSize: "14px" }}>
          Clear All Chat History
        </span>
      </button>
    </div>
  );
}

/* -- LLM Provider ------------------------------------------------ */

const PROVIDER_COLORS: Record<string, string> = {
  deepseek: "#4FA3E3",
  openai: "#10B981",
  claude: "#7C3AED",
  anthropic: "#7C3AED",
};

function ProviderSettings({
  providers,
  onCreate,
  onUpdate,
  onDelete,
  showForm,
}: {
  providers: LLMProvider[];
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

function ProviderItem({
  provider: p,
  onEdit,
  onDelete,
}: {
  provider: LLMProvider;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const color = PROVIDER_COLORS[p.name] || "var(--app-accent)";
  const [showKey, setShowKey] = useState(false);
  const apiKeyText = p.api_key || "Not set";

  return (
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
          Endpoint: {p.base_url || "Not set"} · Model: {p.default_model || "Not set"} · Key:{" "}
          {showKey ? apiKeyText : "hidden"}
        </div>
      </div>

      {/* Actions */}
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
