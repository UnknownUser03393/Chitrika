import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { AlertCircle, Eye, EyeOff, Loader2, Play, Plug, Save } from "lucide-react";
import type {
  PluginAction,
  PluginConfig,
  PluginConfigField,
  PluginInfo,
} from "../services/api";
import { callPluginApi, fetchPluginConfig, savePluginConfig } from "../services/api";

/**
 * Config form for a plugin's declared Config API — editable fields plus
 * action buttons that invoke the plugin's Plugin OpenAPI endpoints.
 */

export function PluginConfigForm({
  plugin,
  onClose,
}: {
  plugin: PluginInfo;
  onClose: () => void;
}) {
  const [config, setConfig] = useState<PluginConfig | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [savedValues, setSavedValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [actionResults, setActionResults] = useState<Record<string, string>>({});
  const [progress, setProgress] = useState<{
    stage: string;
    message: string;
    percent: number | null;
  } | null>(null);
  const timerRef = useRef<number | null>(null);

  const dirty = useMemo(
    () => JSON.stringify(values) !== JSON.stringify(savedValues),
    [savedValues, values],
  );
  const missingRequired = useMemo(
    () => config?.fields.filter((field) => field.required && !(values[field.key] || "").trim()) || [],
    [config, values],
  );

  const stopPolling = () => {
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const startPolling = (endpoint: string) => {
    stopPolling();
    setProgress(null);
    timerRef.current = window.setInterval(async () => {
      try {
        const data = (await callPluginApi(plugin.id, "GET", endpoint)) as {
          stage?: string;
          message?: string;
          percent?: number | null;
        };
        setProgress({
          stage: data.stage || "",
          message: data.message || "",
          percent: typeof data.percent === "number" ? data.percent : null,
        });
        if (data.stage === "done" || data.stage === "failed" || data.percent === 100) {
          stopPolling();
        }
      } catch {
        setProgress({
          stage: "failed",
          message: "Progress endpoint is no longer available.",
          percent: null,
        });
        stopPolling();
      }
    }, 1000);
  };

  useEffect(() => () => stopPolling(), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setConfig(null);
    fetchPluginConfig(plugin.id)
      .then((cfg) => {
        if (cancelled) return;
        setConfig(cfg);
        setValues(cfg.values || {});
        setSavedValues(cfg.values || {});
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Failed to load config";
        setLoadError(message);
        toast.error(message);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [plugin.id]);

  const updateValue = (key: string, value: string) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const runAction = async (action: PluginAction) => {
    if (action.confirm && !window.confirm(`确定执行「${action.label}」？`)) return;
    setBusyAction(action.key);
    try {
      const data = (await callPluginApi(plugin.id, action.method, action.path)) as Record<
        string,
        unknown
      >;
      setActionResults((prev) => ({
        ...prev,
        [action.key]: JSON.stringify(data, null, 2),
      }));
      if (data.started === true && typeof data.progress_endpoint === "string") {
        // Long-running operation (e.g. relogin) — poll and show a progress bar.
        toast.success(data.message ? String(data.message) : "Done");
        startPolling(data.progress_endpoint);
      } else {
        toast.success("Done");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyAction(null);
    }
  };

  const handleSave = async () => {
    if (!config || saving || !dirty) return;
    if (missingRequired.length) {
      toast.error(`Required: ${missingRequired.map((field) => field.label).join(", ")}`);
      return;
    }
    setSaving(true);
    try {
      const updated = await savePluginConfig(plugin.id, values);
      setConfig(updated);
      setValues(updated.values || {});
      setSavedValues(updated.values || {});
      toast.success("Config saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    if (dirty && !window.confirm("Discard unsaved plugin configuration changes?")) return;
    onClose();
  };

  const toggleSecret = (key: string) => {
    setVisibleSecrets((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="h-full w-full flex flex-col bg-[#0E1621]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-8 py-4 border-b border-[#1C2B3A] shrink-0 bg-[#17212B]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-sky-500/10">
            <Plug size={18} className="text-sky-400" />
          </div>
          <div>
            <div className="text-white font-semibold" style={{ fontSize: "16px" }}>
              {plugin.name} — Config
            </div>
            <div className="text-[#708499]" style={{ fontSize: "12px" }}>
              {plugin.description || plugin.id}
            </div>
          </div>
        </div>
        <button
          onClick={handleClose}
          className="text-[#708499] hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5"
          style={{ fontSize: "13px" }}
        >
          Close
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-8 py-8 space-y-6">
          {loading ? (
            <div className="flex items-center gap-2 text-[#708499]">
              <Loader2 size={14} className="animate-spin" /> Loading config…
            </div>
          ) : loadError ? (
            <div className="flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/[0.07] p-4 text-red-300" style={{ fontSize: "12px" }}>
              <AlertCircle size={15} className="mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold">Configuration unavailable</div>
                <div className="mt-1 break-words text-red-200/70">{loadError}</div>
              </div>
            </div>
          ) : config ? (
            <>
              {config.fields.length > 0 && (
                <>
                  <SectionHeading>Config</SectionHeading>
                  {config.fields.map((field) => (
                    <FieldRow
                      key={field.key}
                      field={field}
                      value={values[field.key] ?? ""}
                      onChange={(value) => updateValue(field.key, value)}
                      secretVisible={visibleSecrets.has(field.key)}
                      onToggleSecret={() => toggleSecret(field.key)}
                    />
                  ))}
                </>
              )}

              {config.actions.length > 0 && (
                <>
                  <SectionHeading>Operations</SectionHeading>
                  <div className="space-y-2">
                    {config.actions.map((action) => (
                      <div key={action.key}>
                        <button
                          onClick={() => runAction(action)}
                          disabled={busyAction !== null}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#2A3A4A] text-[#708499] hover:text-[#4FA3E3] hover:border-[#4FA3E3] transition-colors disabled:opacity-50"
                          style={{ fontSize: "13px" }}
                        >
                          {busyAction === action.key ? (
                            <Loader2 size={13} className="animate-spin" />
                          ) : (
                            <Play size={13} />
                          )}
                          {action.label}
                        </button>
                        {actionResults[action.key] && (
                          <pre
                            className="mt-2 p-3 rounded-lg bg-[#0A1018] text-[#9FB6C8] overflow-x-auto"
                            style={{ fontSize: "11px" }}
                          >
                            {actionResults[action.key]}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}

              {progress && (
                <div className="p-3 rounded-lg bg-[#0A1018] border border-[var(--app-border)]">
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className="text-[var(--app-muted)]"
                      style={{ fontSize: "11px", fontWeight: 600 }}
                    >
                      {progress.stage === "done"
                        ? "完成"
                        : progress.stage === "failed"
                          ? "失败"
                          : "进行中"}
                    </span>
                    {progress.percent != null && (
                      <span className="text-[#4FA3E3]" style={{ fontSize: "11px", fontWeight: 600 }}>
                        {Math.round(progress.percent)}%
                      </span>
                    )}
                  </div>
                  <div className="h-1.5 rounded-full bg-[#0E1621] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[#4FA3E3] transition-all duration-500"
                      style={{
                        width:
                          progress.percent != null
                            ? `${Math.max(2, Math.min(100, progress.percent))}%`
                            : "35%",
                      }}
                    />
                  </div>
                  <div className="text-[var(--app-muted)] mt-1.5 break-words" style={{ fontSize: "11px" }}>
                    {progress.message}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-[#708499]" style={{ fontSize: "13px" }}>
              No config available for this plugin.
            </p>
          )}
        </div>
      </div>

      {/* Sticky footer */}
      <div className="shrink-0 px-8 py-4 border-t border-[#1C2B3A] bg-[#17212B]">
        <div className="flex gap-3">
          <button
            onClick={handleClose}
            className="flex-1 py-2.5 rounded-lg font-medium text-[#708499] hover:text-white hover:bg-white/5 transition-colors"
            style={{ fontSize: "14px" }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!config || saving || !dirty || missingRequired.length > 0}
            className="flex-[2] py-2.5 rounded-lg font-medium transition-all inline-flex items-center justify-center gap-2"
            style={{
              fontSize: "14px",
              background: config && !saving && dirty && !missingRequired.length ? "#4FA3E3" : "#2A3A4A",
              color: config && !saving && dirty && !missingRequired.length ? "white" : "#708499",
              cursor: config && !saving && dirty && !missingRequired.length ? "pointer" : "not-allowed",
            }}
          >
            <Save size={14} />
            {saving ? "Saving…" : dirty ? "Save Config" : "Saved"}
          </button>
        </div>
      </div>
    </div>
  );
}

function FieldRow({
  field,
  value,
  onChange,
  secretVisible,
  onToggleSecret,
}: {
  field: PluginConfigField;
  value: string;
  onChange: (value: string) => void;
  secretVisible: boolean;
  onToggleSecret: () => void;
}) {
  const isSecret = field.secret || field.input_type === "password";
  const inputType = isSecret && !secretVisible ? "password" : "text";

  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <span
          className="text-[#708499] uppercase tracking-wider"
          style={{ fontSize: "11px", fontWeight: 600 }}
        >
          {field.label}
          {field.required && <span className="ml-1 text-red-400">*</span>}
        </span>
      </div>
      {field.input_type === "select" ? (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
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
      ) : (
        <div className="relative">
          <input
            type={inputType}
            value={value}
            placeholder={field.placeholder || field.default || ""}
            onChange={(e) => onChange(e.target.value)}
            className={`w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg py-2.5 outline-none border transition-colors ${isSecret ? "pl-3.5 pr-10" : "px-3.5"} ${field.required && !value.trim() ? "border-red-500/40" : "border-transparent focus:border-[#4FA3E3]"}`}
            style={{ fontSize: "14px" }}
          />
          {isSecret && (
            <button
              type="button"
              onClick={onToggleSecret}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#708499] transition-colors hover:text-white"
              aria-label={secretVisible ? `Hide ${field.label}` : `Show ${field.label}`}
            >
              {secretVisible ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          )}
        </div>
      )}
      {field.help_text && (
        <p className="text-[#5A7A9A] mt-1.5" style={{ fontSize: "11px" }}>
          {field.help_text}
        </p>
      )}
    </div>
  );
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
