import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { Globe, Key, Eye, EyeOff, Server, Cpu, X, Star, Plug, Download, Plus, Check } from "lucide-react";
import { toast } from "sonner";
import type {
  CustomProviderField,
  LLMProvider,
  LLMProviderCreate,
  LLMProviderUpdate,
  ProviderType,
} from "../services/api";
import { fetchProviderModels, fetchProviderTypes } from "../services/api";

/* ── Provider presets ──────────────────────────────────────────── */

const PROVIDER_PRESETS: Record<string, { label: string; color: string; url: string }> = {
  // Reverse-engineered chat.deepseek.com client — browser auth, no API key.
  "deepseek-local": { label: "DeepSeek Web (Local)", color: "#4FA3E3", url: "" },
  openai: { label: "OpenAI-Compatible", color: "#10B981", url: "https://api.openai.com/v1" },
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
    provider_type: initial?.provider_type || "",
    plugin_id: initial?.plugin_id || null as string | null,
    api_key: initial?.api_key || "",
    base_url: initial?.base_url || "",
    default_model: initial?.default_model || "",
    custom_config: initial?.custom_config || {} as Record<string, string>,
    models: initial?.models || [] as string[],
    is_default: initial?.is_default || false,
  });
  const [saving, setSaving] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [hasExistingKey] = useState(isEdit && !!initial?.api_key);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [providerTypes, setProviderTypes] = useState<ProviderType[]>([]);

  const preset = PROVIDER_PRESETS[form.provider_type] || null;
  const selectedProviderType = useMemo(
    () => providerTypes.find((item) => item.type === form.provider_type) || null,
    [providerTypes, form.provider_type]
  );
  const customFields = selectedProviderType?.custom_provider_api?.fields || [];
  const isCustomProvider = customFields.length > 0;
  const modelFieldKey = selectedProviderType?.custom_provider_api?.model_field_key || null;
  const connectionCustomFields = customFields.filter((field) => field.key !== modelFieldKey);
  const modelCustomField = customFields.find((field) => field.key === modelFieldKey) || null;
  const apiKeyField = customFields.find((field) => field.key === "api_key") || null;
  const customApiKey = apiKeyField ? (form.custom_config[apiKeyField.key] || "") : "";
  const supportsModelFetch =
    (selectedProviderType?.custom_provider_api?.supports_model_fetch ?? selectedProviderType?.supports_model_fetch) !== false;
  const apiKeySatisfied = isCustomProvider
    ? apiKeyField?.required !== true || customApiKey.trim() !== "" || hasExistingKey
    : selectedProviderType?.needs_api_key === false || form.api_key.trim() !== "" || hasExistingKey;
  const requiredCustomFieldsSatisfied = customFields.every((field) => {
    if (!field.required || field.key === "api_key") {
      return true;
    }
    return (form.custom_config[field.key] || "").trim() !== "";
  });
  const canFetchModels = supportsModelFetch && isEdit && !fetchingModels;
  const canSave =
    form.name.trim() !== "" &&
    form.display_name.trim() !== "" &&
    form.provider_type.trim() !== "" &&
    (isCustomProvider || !selectedProviderType?.needs_base_url || form.base_url.trim() !== "") &&
    apiKeySatisfied &&
    requiredCustomFieldsSatisfied;

  useEffect(() => {
    let cancelled = false;
    fetchProviderTypes()
      .then((items) => {
        if (cancelled) return;
        setProviderTypes(items);
        if (!initial && items.length > 0) {
          const first = items.find((item) => item.type === "deepseek-local") || items[0];
          setForm((prev) => {
            if (prev.provider_type) {
              return prev;
            }
            const customConfig = buildInitialCustomConfig(first, {});
            return {
              ...prev,
              provider_type: first.type,
              plugin_id: first.plugin_id,
              display_name: prev.display_name || first.label,
              base_url: first.custom_provider_api ? "" : (prev.base_url || first.default_base_url || ""),
              default_model: resolveInitialDefaultModel(first, customConfig, prev.default_model),
              custom_config: customConfig,
              name: prev.name || first.type.replace(/[^a-z0-9]+/gi, "-").toLowerCase(),
            };
          });
        }
      })
      .catch((err) => {
        const msg = err instanceof Error ? err.message : "Unknown error";
        toast.error(`Failed to load provider types: ${msg}`);
      });
    return () => {
      cancelled = true;
    };
  }, [initial]);

  const handleSubmit = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      const normalizedCustomConfig = normalizeCustomConfig(form.custom_config, customFields);
      const resolvedDefaultModel = resolveSubmittedDefaultModel(
        selectedProviderType,
        normalizedCustomConfig,
        form.default_model,
        form.models
      );
      const payload: LLMProviderCreate | LLMProviderUpdate = {
        display_name: form.display_name.trim(),
        provider_type: form.provider_type.trim(),
        plugin_id: form.plugin_id,
        base_url: isCustomProvider ? "" : form.base_url.trim(),
        default_model: resolvedDefaultModel,
        custom_config: normalizedCustomConfig,
        models: form.models,
        is_default: form.is_default,
      };

      const apiKey = isCustomProvider
        ? (normalizedCustomConfig.api_key || "").trim()
        : form.api_key.trim();
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
    if (selectedProviderType?.supports_model_fetch === false) {
      toast.error("This provider does not expose model fetching.");
      return;
    }
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
      const merged = [...new Set([...form.models, ...names])];
      setForm((prev) => {
        const nextCustomConfig = { ...prev.custom_config };
        if (modelFieldKey && !nextCustomConfig[modelFieldKey] && names.length > 0) {
          nextCustomConfig[modelFieldKey] = names[0];
        }
        return {
          ...prev,
          models: merged,
          default_model: !prev.default_model && names.length > 0 ? names[0] : prev.default_model,
          custom_config: nextCustomConfig,
        };
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error(`Failed to fetch models: ${msg}`);
    } finally {
      setFetchingModels(false);
    }
  };

  const updateCustomField = (fieldKey: string, value: string) => {
    setForm((prev) => ({
      ...prev,
      custom_config: {
        ...prev.custom_config,
        [fieldKey]: value,
      },
    }));
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
                {providerTypes.map((item) => {
                  const swatch = PROVIDER_PRESETS[item.type];
                  const color = swatch?.color || "#4FA3E3";
                  return (
                    <button
                      key={item.type}
                      type="button"
                      onClick={() =>
                        setForm((prev) => {
                          const customConfig = buildInitialCustomConfig(item, prev.custom_config);
                          return {
                            ...prev,
                            provider_type: item.type,
                            plugin_id: item.plugin_id,
                            display_name: prev.display_name || item.label,
                            base_url: item.custom_provider_api ? "" : (prev.base_url || item.default_base_url || swatch?.url || ""),
                            default_model: resolveInitialDefaultModel(item, customConfig, prev.default_model),
                            custom_config: customConfig,
                            name: prev.name || item.type.replace(/[^a-z0-9]+/gi, "-").toLowerCase(),
                          };
                        })
                      }
                      className="flex flex-col items-center gap-1 px-2 py-2.5 rounded-xl border transition-all"
                      style={{
                        borderColor: form.provider_type === item.type ? color : "transparent",
                        background: form.provider_type === item.type ? `${color}15` : "#0E1621",
                      }}
                    >
                      <div className="w-6 h-6 rounded-full" style={{ background: color }} />
                      <span className="text-white truncate w-full text-center" style={{ fontSize: "10px", fontWeight: 500 }}>
                        {item.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-[#0E1621] rounded-lg px-3.5 py-2.5 opacity-50">
                {preset && <div className="w-5 h-5 rounded-full shrink-0" style={{ background: preset.color }} />}
                <span className="text-white" style={{ fontSize: "14px" }}>{selectedProviderType?.label || preset?.label || form.provider_type}</span>
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

          {isCustomProvider ? (
            connectionCustomFields.map((field) => {
              const value = form.custom_config[field.key] || "";
              const inputType = field.secret && !showKey ? "password" : field.input_type === "password" ? "password" : "text";
              const hint = field.required ? "required" : undefined;

              return (
                <div key={field.key}>
                  <FieldLabel
                    icon={field.secret ? <Key size={14} /> : <Plug size={14} />}
                    label={field.label}
                    hint={hint}
                  />
                  {field.input_type === "select" ? (
                    <select
                      value={value}
                      onChange={(e) => updateCustomField(field.key, e.target.value)}
                      className="w-full bg-[#0E1621] text-white rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
                      style={{ fontSize: "14px" }}
                    >
                      <option value="">{field.placeholder || `Select ${field.label}`}</option>
                      {field.options.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  ) : field.secret || field.input_type === "password" ? (
                    <div className="relative">
                      <input
                        type={showKey ? "text" : "password"}
                        placeholder={field.placeholder || (isEdit ? field.label : "")}
                        value={value}
                        onChange={(e) => updateCustomField(field.key, e.target.value)}
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
                  ) : (
                    <input
                      type={inputType}
                      placeholder={field.placeholder || field.default || ""}
                      value={value}
                      onChange={(e) => updateCustomField(field.key, e.target.value)}
                      className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
                      style={{ fontSize: field.key.includes("url") ? "13px" : "14px" }}
                    />
                  )}
                  {field.help_text && (
                    <p className="text-[#5A7A9A] mt-1.5" style={{ fontSize: "11px" }}>
                      {field.help_text}
                    </p>
                  )}
                </div>
              );
            })
          ) : (
            <>
              {/* API Key */}
              <div>
                <FieldLabel
                  icon={<Key size={14} />}
                  label="API Key"
                  hint={selectedProviderType?.needs_api_key === false ? "not required" : hasExistingKey ? "visible" : undefined}
                />
                <div className="relative">
                  <input
                    type={showKey ? "text" : "password"}
                    placeholder={selectedProviderType?.needs_api_key === false ? "Not required for this provider" : isEdit ? "API key" : "e.g. sk-..."}
                    value={form.api_key}
                    onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                    disabled={selectedProviderType?.needs_api_key === false}
                    className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg pl-3.5 pr-10 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors disabled:opacity-50"
                    style={{ fontSize: "14px" }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    disabled={selectedProviderType?.needs_api_key === false}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#708499] hover:text-white transition-colors disabled:opacity-50"
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
                  placeholder={selectedProviderType?.default_base_url || "https://api.deepseek.com/v1"}
                  value={form.base_url}
                  onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                  disabled={selectedProviderType?.needs_base_url === false}
                  className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 pr-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors font-mono disabled:opacity-50"
                  style={{ fontSize: "13px" }}
                />
              </div>
            </>
          )}

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

          {isCustomProvider ? (
            modelCustomField ? (
              <div>
                <FieldLabel icon={<Cpu size={14} />} label={modelCustomField.label} />
                {modelCustomField.input_type === "select" ? (
                  <select
                    value={form.custom_config[modelCustomField.key] || ""}
                    onChange={(e) => updateCustomField(modelCustomField.key, e.target.value)}
                    className="w-full bg-[#0E1621] text-white rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
                    style={{ fontSize: "14px" }}
                  >
                    <option value="">{modelCustomField.placeholder || `Select ${modelCustomField.label}`}</option>
                    {modelCustomField.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                    {form.models
                      .filter((name) => !modelCustomField.options.some((option) => option.value === name))
                      .map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    placeholder={modelCustomField.placeholder || modelCustomField.default || ""}
                    value={form.custom_config[modelCustomField.key] || ""}
                    onChange={(e) => updateCustomField(modelCustomField.key, e.target.value)}
                    className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
                    style={{ fontSize: "14px" }}
                  />
                )}
                {modelCustomField.help_text && (
                  <p className="text-[#5A7A9A] mt-1.5" style={{ fontSize: "11px" }}>
                    {modelCustomField.help_text}
                  </p>
                )}
              </div>
            ) : null
          ) : (
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
          )}

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
                disabled={!canFetchModels}
                className="shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#2A3A4A] text-[#708499] hover:text-[#4FA3E3] hover:border-[#4FA3E3] transition-colors disabled:opacity-50"
                style={{ fontSize: "12px" }}
                title={!supportsModelFetch ? "This provider does not support model discovery" : isEdit ? "Fetch models from provider API" : "Save first to enable"}
              >
                <Download size={13} className={fetchingModels ? "animate-bounce" : ""} />
                {fetchingModels ? "…" : "Fetch"}
              </button>
            </div>
            <p className="text-[#5A7A9A] mt-1.5" style={{ fontSize: "11px" }}>
              {!supportsModelFetch
                ? "Press Enter or comma to add. Backspace to remove. This provider requires manual model entry."
                : "Press Enter or comma to add. Backspace to remove. Click Fetch to pull models from the provider API."}
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

function buildInitialCustomConfig(
  providerType: ProviderType,
  currentConfig: Record<string, string>
): Record<string, string> {
  const fields = providerType.custom_provider_api?.fields || [];
  const nextConfig: Record<string, string> = {};

  fields.forEach((field) => {
    const existingValue = currentConfig[field.key];
    if (typeof existingValue === "string" && existingValue.trim() !== "") {
      nextConfig[field.key] = existingValue;
      return;
    }
    if (field.default) {
      nextConfig[field.key] = field.default;
      return;
    }
    nextConfig[field.key] = "";
  });

  return nextConfig;
}

function normalizeCustomConfig(
  config: Record<string, string>,
  fields: CustomProviderField[]
): Record<string, string> {
  const normalized: Record<string, string> = {};

  fields.forEach((field) => {
    const rawValue = config[field.key] || "";
    normalized[field.key] = rawValue.trim();
  });

  return normalized;
}

function resolveInitialDefaultModel(
  providerType: ProviderType,
  customConfig: Record<string, string>,
  currentValue: string
): string {
  if (currentValue.trim() !== "") {
    return currentValue;
  }

  const modelFieldKey = providerType.custom_provider_api?.model_field_key;
  if (modelFieldKey) {
    const configuredValue = customConfig[modelFieldKey] || "";
    if (configuredValue.trim() !== "") {
      return configuredValue;
    }
  }

  return providerType.default_model || "";
}

function resolveSubmittedDefaultModel(
  providerType: ProviderType | null,
  customConfig: Record<string, string>,
  currentValue: string,
  models: string[]
): string {
  if (!providerType) {
    return currentValue.trim();
  }

  const modelFieldKey = providerType.custom_provider_api?.model_field_key;
  if (modelFieldKey) {
    const configuredValue = customConfig[modelFieldKey] || "";
    if (configuredValue.trim() !== "") {
      return configuredValue.trim();
    }
  }

  if (currentValue.trim() !== "") {
    return currentValue.trim();
  }

  if (models.length > 0) {
    return models[0];
  }

  return providerType.default_model || "";
}

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

