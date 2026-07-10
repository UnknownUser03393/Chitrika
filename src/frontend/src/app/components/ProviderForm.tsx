import { useState } from "react";
import { motion } from "motion/react";
import { Globe, Key, Eye, EyeOff, Server, Cpu, X, Star, Plug, Download, Plus, Check } from "lucide-react";
import { toast } from "sonner";
import type { LLMProvider, LLMProviderCreate, LLMProviderUpdate } from "../services/api";
import { fetchProviderModels } from "../services/api";

/* ── Provider presets ──────────────────────────────────────────── */

const PROVIDER_PRESETS: Record<string, { label: string; color: string; url: string }> = {
  deepseek:     { label: "DeepSeek",     color: "#4FA3E3", url: "https://api.deepseek.com/v1" },
  openai:       { label: "OpenAI",       color: "#10B981", url: "https://api.openai.com/v1" },
  anthropic:    { label: "Anthropic",    color: "#7C3AED", url: "https://api.anthropic.com/v1" },
  groq:         { label: "Groq",         color: "#F97316", url: "https://api.groq.com/openai/v1" },
  together:     { label: "Together",     color: "#6366F1", url: "https://api.together.xyz/v1" },
  openrouter:   { label: "OpenRouter",   color: "#EC4899", url: "https://openrouter.ai/api/v1" },
  local:        { label: "Ollama",       color: "#94A3B8", url: "http://localhost:11434/v1" },
};

/* ── Tiny tag input ─────────────────────────────────────────────── */

function ModelTagInput({
  models,
  onChange,
}: {
  models: string[];
  onChange: (models: string[]) => void;
}) {
  const [input, setInput] = useState("");

  const add = (raw: string) => {
    const trimmed = raw.replace(/,/g, "").trim();
    if (trimmed && !models.includes(trimmed)) {
      onChange([...models, trimmed]);
    }
    setInput("");
  };

  const remove = (name: string) => onChange(models.filter((m) => m !== name));

  return (
    <div className="flex flex-wrap gap-1.5 bg-[#0E1621] rounded-lg px-3 py-2 border border-transparent focus-within:border-[#4FA3E3] transition-colors min-h-[42px] items-center">
      {models.map((m) => (
        <span
          key={m}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-white"
          style={{ background: "rgba(79,163,227,0.18)", fontSize: "12px", lineHeight: "1.8" }}
        >
          {m}
          <button
            type="button"
            onClick={() => remove(m)}
            className="text-[#708499] hover:text-white transition-colors"
          >
            <X size={12} />
          </button>
        </span>
      ))}
      <input
        type="text"
        placeholder={models.length === 0 ? "deepseek-chat" : "Add…"}
        value={input}
        onChange={(e) => {
          const v = e.target.value;
          if (v.includes(",")) { add(v); return; }
          setInput(v);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(input); }
          if (e.key === "Backspace" && !input && models.length > 0) remove(models[models.length - 1]);
        }}
        className="flex-1 min-w-[100px] bg-transparent text-white placeholder-[#708499] outline-none"
        style={{ fontSize: "13px" }}
      />
    </div>
  );
}

/* ── Shared field label ─────────────────────────────────────────── */

function FieldLabel({ icon, label, hint }: { icon: React.ReactNode; label: string; hint?: string }) {
  return (
    <div className="flex items-center gap-1.5 mb-1.5">
      <span className="text-[#708499]">{icon}</span>
      <span className="text-[#708499] uppercase tracking-wider" style={{ fontSize: "11px", fontWeight: 600 }}>
        {label}
      </span>
      {hint && <span className="text-[#5A7A9A] ml-auto" style={{ fontSize: "10px" }}>{hint}</span>}
    </div>
  );
}

/* ── Provider form (full-page) ──────────────────────────────────── */

interface ProviderFormProps {
  initial: LLMProvider | null;
  onSubmit: (data: LLMProviderCreate | LLMProviderUpdate) => Promise<void>;
  onCancel: () => void;
}

export function ProviderForm({ initial, onSubmit, onCancel }: ProviderFormProps) {
  const isEdit = initial !== null;

  const [form, setForm] = useState({
    name: initial?.name || "",
    display_name: initial?.display_name || "",
    api_key: initial?.api_key || "",
    base_url: initial?.base_url || "",
    default_model: initial?.default_model || "",
    models: initial?.models || [] as string[],
    is_default: initial?.is_default || false,
  });
  const [saving, setSaving] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [hasExistingKey] = useState(isEdit && !!initial?.api_key);
  const [fetchingModels, setFetchingModels] = useState(false);

  const canSave = form.name.trim() !== "" && form.display_name.trim() !== "" && form.base_url.trim() !== "";
  const preset = PROVIDER_PRESETS[form.name] || null;

  const handleSubmit = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      const payload: LLMProviderCreate | LLMProviderUpdate = {
        display_name: form.display_name.trim(),
        base_url: form.base_url.trim(),
        default_model: form.default_model.trim() || form.models[0] || "",
        models: form.models,
        is_default: form.is_default,
      };

      const apiKey = form.api_key.trim();
      if (isEdit) {
        if (apiKey) {
          payload.api_key = apiKey;
        }
      } else {
        (payload as LLMProviderCreate).name = form.name.trim();
        (payload as LLMProviderCreate).api_key = apiKey;
      }

      await onSubmit(payload);
    } finally {
      setSaving(false);
    }
  };

  const handleFetchModels = async () => {
    // For new providers, we need them saved first to have an ID.
    // For editing, we can fetch immediately.
    if (!isEdit) {
      toast.error("Save the provider first, then you can fetch models from the edit screen.");
      return;
    }
    setFetchingModels(true);
    try {
      const models = await fetchProviderModels(initial!.id);
      const names = models.map((m) => m.name);
      // Merge with existing (keep user-added ones, add new ones from API)
      const merged = [...new Set([...form.models, ...names])];
      setForm({ ...form, models: merged });
      if (!form.default_model && names.length > 0) {
        setForm((prev) => ({ ...prev, default_model: names[0] }));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error(`Failed to fetch models: ${msg}`);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onCancel();
  };

  return (
    <div className="h-full w-full flex flex-col bg-[#0E1621]" onKeyDown={handleKeyDown}>
      {/* ── Top bar ── */}
      <div className="flex items-center justify-between px-8 py-4 border-b border-[#1C2B3A] shrink-0 bg-[#17212B]">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: preset ? `${preset.color}22` : "rgba(79,163,227,0.15)" }}
          >
            <Server size={18} style={{ color: preset?.color || "#4FA3E3" }} />
          </div>
          <div>
            <div className="text-white font-semibold" style={{ fontSize: "16px" }}>
              {isEdit ? "Edit Provider" : "New Provider"}
            </div>
            {isEdit && (
              <div className="text-[#708499]" style={{ fontSize: "12px" }}>
                {initial?.display_name}
              </div>
            )}
          </div>
        </div>
        <button
          onClick={onCancel}
          className="text-[#708499] hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5"
          style={{ fontSize: "13px" }}
        >
          Cancel
        </button>
      </div>

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-8 py-8 space-y-6">
          {/* ── Identity ── */}
          <SectionHeading>Identity</SectionHeading>

          {/* Provider type (new) or locked display (edit) */}
          <div>
            <FieldLabel icon={<Cpu size={14} />} label="Provider Type" hint={isEdit ? "locked" : "required"} />
            {!isEdit ? (
              <div className="grid grid-cols-4 gap-2">
                {Object.entries(PROVIDER_PRESETS).map(([key, p]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() =>
                      setForm({
                        ...form,
                        name: key,
                        display_name: form.display_name || p.label,
                        base_url: form.base_url || p.url,
                      })
                    }
                    className="flex flex-col items-center gap-1 px-2 py-2.5 rounded-xl border transition-all"
                    style={{
                      borderColor: form.name === key ? p.color : "transparent",
                      background: form.name === key ? `${p.color}15` : "#0E1621",
                    }}
                  >
                    <div className="w-6 h-6 rounded-full" style={{ background: p.color }} />
                    <span className="text-white truncate w-full text-center" style={{ fontSize: "10px", fontWeight: 500 }}>
                      {p.label}
                    </span>
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setForm({ ...form, name: "" })}
                  className="flex flex-col items-center gap-1 px-2 py-2.5 rounded-xl border transition-all"
                  style={{
                    borderColor: !PROVIDER_PRESETS[form.name] && form.name ? "#4FA3E3" : "transparent",
                    background: !PROVIDER_PRESETS[form.name] && form.name ? "rgba(79,163,227,0.08)" : "#0E1621",
                  }}
                >
                  <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ background: "#2A3A4A" }}>
                    <Plus size={12} className="text-[#708499]" />
                  </div>
                  <span className="text-[#708499] truncate w-full text-center" style={{ fontSize: "10px" }}>Custom</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-[#0E1621] rounded-lg px-3.5 py-2.5 opacity-50">
                {preset && <div className="w-5 h-5 rounded-full shrink-0" style={{ background: preset.color }} />}
                <span className="text-white" style={{ fontSize: "14px" }}>{preset?.label || form.name}</span>
              </div>
            )}
          </div>

          {/* Display name */}
          <div>
            <FieldLabel icon={<Star size={14} />} label="Display Name" />
            <input
              type="text"
              placeholder="e.g. DeepSeek V4"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
              style={{ fontSize: "14px" }}
            />
          </div>

          {/* ── Connection ── */}
          <SectionHeading>Connection</SectionHeading>

          {/* API Key */}
          <div>
            <FieldLabel icon={<Key size={14} />} label="API Key" hint={hasExistingKey ? "visible" : undefined} />
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                placeholder={isEdit ? "API key" : "e.g. sk-..."}
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg pl-3.5 pr-10 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
                style={{ fontSize: "14px" }}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#708499] hover:text-white transition-colors"
              >
                {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Base URL */}
          <div>
            <FieldLabel icon={<Globe size={14} />} label="Base URL" />
            <input
              type="text"
              placeholder="https://api.deepseek.com/v1"
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors font-mono"
              style={{ fontSize: "13px" }}
            />
          </div>

          {/* Test connection */}
          <button
            type="button"
            onClick={() => toast.error("Connection test coming soon")}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-dashed border-[#2A3A4A] text-[#708499] hover:text-[#4FA3E3] hover:border-[#4FA3E3] transition-colors"
            style={{ fontSize: "13px" }}
            title="Coming soon"
          >
            <Plug size={14} />
            Test Connection
          </button>

          {/* ── Models ── */}
          <SectionHeading>Models</SectionHeading>

          {/* Default model */}
          <div>
            <FieldLabel icon={<Cpu size={14} />} label="Default Model" />
            <input
              type="text"
              placeholder="e.g. deepseek-chat"
              value={form.default_model}
              onChange={(e) => setForm({ ...form, default_model: e.target.value })}
              className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
              style={{ fontSize: "14px" }}
            />
          </div>

          {/* Models tag input + fetch button */}
          <div>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <FieldLabel icon={<Server size={14} />} label="Available Models" />
                <ModelTagInput models={form.models} onChange={(models) => setForm({ ...form, models })} />
              </div>
              <button
                type="button"
                onClick={handleFetchModels}
                disabled={fetchingModels}
                className="shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#2A3A4A] text-[#708499] hover:text-[#4FA3E3] hover:border-[#4FA3E3] transition-colors disabled:opacity-50"
                style={{ fontSize: "12px" }}
                title={isEdit ? "Fetch models from provider API" : "Save first to enable"}
              >
                <Download size={13} className={fetchingModels ? "animate-bounce" : ""} />
                {fetchingModels ? "…" : "Fetch"}
              </button>
            </div>
            <p className="text-[#5A7A9A] mt-1.5" style={{ fontSize: "11px" }}>
              Press Enter or comma to add. Backspace to remove. Click Fetch to pull models from the provider API.
            </p>
          </div>

          {/* Default toggle */}
          <label
            className="flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-colors hover:bg-white/[0.03]"
            style={{ background: form.is_default ? "rgba(79,163,227,0.06)" : "transparent" }}
          >
            <div
              className="w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 transition-colors cursor-pointer"
              style={{
                background: form.is_default ? "#4FA3E3" : "#2A3A4A",
                border: form.is_default ? "none" : "2px solid #3A4A5C",
              }}
              onClick={() => setForm({ ...form, is_default: !form.is_default })}
            >
              {form.is_default && <Check size={12} strokeWidth={3} className="text-white" />}
            </div>
            <div>
              <div className="text-white select-none" style={{ fontSize: "13px", fontWeight: 500 }}>
                Set as default provider
              </div>
              <div className="text-[#708499] select-none" style={{ fontSize: "11px" }}>
                New characters will use this provider automatically
              </div>
            </div>
          </label>

          {/* Spacer for footer clearance */}
          <div className="h-4" />
        </div>
      </div>

      {/* ── Sticky footer ── */}
      <div className="shrink-0 px-8 py-4 border-t border-[#1C2B3A] bg-[#17212B]">
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-lg font-medium text-[#708499] hover:text-white hover:bg-white/5 transition-colors"
            style={{ fontSize: "14px" }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSave || saving}
            className="flex-[2] py-2.5 rounded-lg font-medium transition-all"
            style={{
              fontSize: "14px",
              background: canSave && !saving ? "#4FA3E3" : "#2A3A4A",
              color: canSave && !saving ? "white" : "#708499",
              cursor: canSave && !saving ? "pointer" : "not-allowed",
            }}
          >
            {saving ? "Saving…" : isEdit ? "Save Changes" : "Create Provider"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Helpers ────────────────────────────────────────────────────── */

function SectionHeading({ children }: { children: string }) {
  return (
    <p
      className="text-[#708499] pb-1.5 border-b border-[#1C2B3A]"
      style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px" }}
    >
      {children}
    </p>
  );
}

