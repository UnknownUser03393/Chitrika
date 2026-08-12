import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, Play, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import type { PluginAPI, PluginEndpoint } from "../services/api";
import { callPluginApi } from "../services/api";

function endpointKey(endpoint: PluginEndpoint): string {
  return `${endpoint.method} ${endpoint.path}`;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function scalarLabel(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function ResultNode({ label, value, depth = 0 }: { label: string; value: unknown; depth?: number }) {
  if (isPlainObject(value)) {
    const entries = Object.entries(value);
    return (
      <div style={{ marginLeft: depth * 10 }}>
        {label && <div className="mb-1 font-medium text-[var(--app-muted)]" style={{ fontSize: "11px" }}>{label}</div>}
        {entries.length ? entries.map(([key, child]) => (
          <ResultNode key={key} label={key} value={child} depth={depth + 1} />
        )) : <span className="text-[var(--app-muted)]" style={{ fontSize: "11px" }}>Empty response</span>}
      </div>
    );
  }
  if (Array.isArray(value)) {
    return (
      <div className="mb-1.5 grid grid-cols-[minmax(70px,auto)_1fr] gap-2" style={{ marginLeft: depth * 10, fontSize: "11px" }}>
        <span className="text-[var(--app-muted)]">{label}</span>
        <span className="break-all text-[var(--app-text)]">
          {value.every((item) => !isPlainObject(item))
            ? value.map(scalarLabel).join(", ") || "—"
            : JSON.stringify(value, null, 2)}
        </span>
      </div>
    );
  }
  return (
    <div className="mb-1.5 grid grid-cols-[minmax(70px,auto)_1fr] gap-2" style={{ marginLeft: depth * 10, fontSize: "11px" }}>
      <span className="text-[var(--app-muted)]">{label}</span>
      <span className="break-all text-[var(--app-text)]">{scalarLabel(value)}</span>
    </div>
  );
}

export function PluginPanel({ pluginId, api }: { pluginId: string; api: PluginAPI }) {
  const getEndpoints = useMemo(
    () => api.endpoints.filter((endpoint) => endpoint.method === "GET"),
    [api.endpoints],
  );
  const actionEndpoints = useMemo(
    () => api.endpoints.filter((endpoint) => endpoint.method !== "GET"),
    [api.endpoints],
  );
  const [results, setResults] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loadingKeys, setLoadingKeys] = useState<Set<string>>(new Set());
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const keys = getEndpoints.map(endpointKey);
    setLoadingKeys(new Set(keys));
    setErrors((current) => {
      const next = { ...current };
      keys.forEach((key) => delete next[key]);
      return next;
    });

    const settled = await Promise.allSettled(
      getEndpoints.map(async (endpoint) => ({
        key: endpointKey(endpoint),
        value: await callPluginApi(pluginId, endpoint.method, endpoint.path),
      })),
    );
    const nextResults: Record<string, unknown> = {};
    const nextErrors: Record<string, string> = {};
    settled.forEach((result, index) => {
      const key = endpointKey(getEndpoints[index]);
      if (result.status === "fulfilled") nextResults[key] = result.value.value;
      else nextErrors[key] = errorMessage(result.reason, "Failed to load status");
    });
    setResults((current) => ({ ...current, ...nextResults }));
    setErrors((current) => ({ ...current, ...nextErrors }));
    setLoadingKeys(new Set());
  }, [getEndpoints, pluginId]);

  useEffect(() => {
    if (getEndpoints.length) void refresh();
  }, [getEndpoints.length, refresh]);

  const runAction = async (endpoint: PluginEndpoint) => {
    const key = endpointKey(endpoint);
    if (busyAction) return;
    setBusyAction(key);
    setErrors((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
    try {
      const result = await callPluginApi(pluginId, endpoint.method, endpoint.path);
      setResults((current) => ({ ...current, [key]: result }));
      toast.success(endpoint.summary ? `${endpoint.summary} completed` : "Plugin action completed");
      if (getEndpoints.length) await refresh();
    } catch (error) {
      const message = errorMessage(error, "Plugin action failed");
      setErrors((current) => ({ ...current, [key]: message }));
      toast.error(message);
    } finally {
      setBusyAction(null);
    }
  };

  const refreshing = loadingKeys.size > 0;

  return (
    <section className="mt-3 rounded-xl border border-[var(--app-border)] bg-[#0E1621] p-3">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <div className="text-[var(--app-accent)]" style={{ fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px" }}>
            Runtime operations
          </div>
          <div className="mt-0.5 text-[var(--app-muted)]" style={{ fontSize: "10px" }}>
            {api.endpoints.length} declared endpoint{api.endpoints.length === 1 ? "" : "s"}
          </div>
        </div>
        {getEndpoints.length > 0 && (
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[var(--app-muted)] transition-colors hover:bg-white/5 hover:text-[var(--app-text)] disabled:opacity-50"
            style={{ fontSize: "11px" }}
          >
            {refreshing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            Refresh
          </button>
        )}
      </div>

      {api.endpoints.length === 0 && (
        <div className="py-3 text-center text-[var(--app-muted)]" style={{ fontSize: "11px" }}>
          This plugin declares no runtime endpoints.
        </div>
      )}

      <div className="space-y-2">
        {getEndpoints.map((endpoint) => {
          const key = endpointKey(endpoint);
          return (
            <div key={key} className="rounded-lg border border-white/5 bg-black/10 p-2.5">
              <EndpointHeading endpoint={endpoint} />
              {loadingKeys.has(key) ? (
                <div className="mt-2 flex items-center gap-1.5 text-[var(--app-muted)]" style={{ fontSize: "11px" }}>
                  <Loader2 size={11} className="animate-spin" /> Loading…
                </div>
              ) : errors[key] ? (
                <InlineError message={errors[key]} />
              ) : (
                <div className="mt-2"><ResultNode label="" value={results[key]} /></div>
              )}
            </div>
          );
        })}
      </div>

      {actionEndpoints.length > 0 && (
        <div className="mt-3 space-y-2">
          {actionEndpoints.map((endpoint) => {
            const key = endpointKey(endpoint);
            const busy = busyAction === key;
            return (
              <div key={key}>
                <button
                  type="button"
                  onClick={() => void runAction(endpoint)}
                  disabled={busyAction !== null}
                  className="flex w-full items-center gap-2 rounded-lg border border-[var(--app-border)] px-3 py-2 text-left text-[var(--app-muted)] transition-colors hover:border-[var(--app-accent)] hover:text-[var(--app-accent)] disabled:opacity-50"
                  style={{ fontSize: "11px" }}
                  title={endpoint.description}
                >
                  {busy ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                  <span className="flex-1">{endpoint.summary || `${endpoint.method} ${endpoint.path}`}</span>
                  <span className="font-mono opacity-60">{endpoint.method}</span>
                </button>
                {errors[key] && <InlineError message={errors[key]} />}
                {!errors[key] && results[key] !== undefined && (
                  <div className="mt-1.5 flex items-center gap-1.5 text-emerald-400" style={{ fontSize: "10px" }}>
                    <CheckCircle2 size={11} /> Last action completed
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function EndpointHeading({ endpoint }: { endpoint: PluginEndpoint }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div>
        <div className="font-medium text-[var(--app-text)]" style={{ fontSize: "11px" }}>
          {endpoint.summary || endpoint.path}
        </div>
        {endpoint.description && (
          <div className="mt-0.5 text-[var(--app-muted)]" style={{ fontSize: "10px" }}>{endpoint.description}</div>
        )}
      </div>
      <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[var(--app-muted)]" style={{ fontSize: "9px" }}>
        {endpoint.method} {endpoint.path}
      </span>
    </div>
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="mt-2 flex items-start gap-1.5 break-words text-red-300" style={{ fontSize: "10px" }}>
      <AlertCircle size={11} className="mt-0.5 shrink-0" /> {message}
    </div>
  );
}
