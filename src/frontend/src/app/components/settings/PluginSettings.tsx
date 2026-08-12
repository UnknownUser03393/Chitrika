import { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleOff,
  Loader2,
  Puzzle,
  RefreshCw,
  Search,
  Settings2,
  ShieldAlert,
  Wrench,
} from "lucide-react";
import { toast } from "sonner";

import type { PluginInfo, PluginScanResult } from "../../services/api";
import { rescanPlugins, updatePlugin } from "../../services/api";
import { PluginConfigForm } from "../PluginConfigForm";
import { PluginPanel } from "../PluginPanel";
import { SectionLabel, SwitchToggle } from "./SettingsControls";

type Filter = "all" | "enabled" | "attention";

export function PluginSettings({
  plugins,
  onPluginsChange,
  showForm,
}: {
  plugins: PluginInfo[];
  onPluginsChange: (plugins: PluginInfo[]) => void;
  showForm?: (form: React.ReactNode | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [scanning, setScanning] = useState(false);
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set());
  const [scanIssues, setScanIssues] = useState<string[]>([]);

  const enabledCount = plugins.filter((plugin) => plugin.enabled && plugin.available).length;
  const attentionCount = plugins.filter(
    (plugin) => !plugin.available || Boolean(plugin.load_error),
  ).length + scanIssues.length;

  const visible = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return plugins.filter((plugin) => {
      const matchesQuery = !normalized || [
        plugin.name,
        plugin.id,
        plugin.description,
        plugin.author,
      ].some((value) => value.toLowerCase().includes(normalized));
      const matchesFilter =
        filter === "all" ||
        (filter === "enabled" && plugin.enabled && plugin.available) ||
        (filter === "attention" && (!plugin.available || Boolean(plugin.load_error)));
      return matchesQuery && matchesFilter;
    });
  }, [filter, plugins, query]);

  const toggle = async (plugin: PluginInfo, enabled: boolean) => {
    if (pendingIds.has(plugin.id)) return;
    setPendingIds((current) => new Set(current).add(plugin.id));
    try {
      const updated = await updatePlugin(plugin.id, enabled);
      onPluginsChange(
        plugins.map((item) => (item.id === updated.id ? updated : item)),
      );
      toast.success(`${plugin.name} ${enabled ? "enabled" : "disabled"}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update plugin");
    } finally {
      setPendingIds((current) => {
        const next = new Set(current);
        next.delete(plugin.id);
        return next;
      });
    }
  };

  const rescan = async () => {
    if (scanning) return;
    setScanning(true);
    try {
      const result: PluginScanResult = await rescanPlugins();
      onPluginsChange(result.plugins);
      setScanIssues(result.invalid);
      if (result.invalid.length) {
        toast.warning(
          `Found ${result.discovered} plugins and ${result.invalid.length} invalid manifest${result.invalid.length === 1 ? "" : "s"}`,
        );
      } else {
        toast.success(`Found ${result.discovered} plugin${result.discovered === 1 ? "" : "s"}`);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to rescan plugins");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="space-y-4 px-2 py-2">
      <div className="flex items-center justify-between pr-2">
        <SectionLabel label="Plugin runtime" />
        <button
          type="button"
          onClick={() => void rescan()}
          disabled={scanning}
          className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[var(--app-muted)] transition-colors hover:bg-white/5 hover:text-[var(--app-text)] disabled:opacity-50"
          style={{ fontSize: "12px" }}
        >
          {scanning ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
          {scanning ? "Scanning…" : "Rescan"}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 px-1">
        <RuntimeMetric label="Discovered" value={plugins.length} icon={<Puzzle size={14} />} />
        <RuntimeMetric label="Enabled" value={enabledCount} icon={<CheckCircle2 size={14} />} tone="success" />
        <RuntimeMetric label="Attention" value={attentionCount} icon={<AlertTriangle size={14} />} tone={attentionCount ? "warning" : "muted"} />
      </div>

      {scanIssues.length > 0 && (
        <div className="mx-1 rounded-xl border border-amber-500/20 bg-amber-500/[0.07] p-3">
          <div className="mb-2 flex items-center gap-2 text-amber-300" style={{ fontSize: "12px", fontWeight: 600 }}>
            <ShieldAlert size={14} /> Invalid manifests
          </div>
          <div className="space-y-1">
            {scanIssues.map((issue) => (
              <p key={issue} className="break-words font-mono text-amber-200/75" style={{ fontSize: "10px" }}>
                {issue}
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 px-1">
        <label className="relative min-w-0 flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--app-muted)]" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search plugins"
            className="w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-elevated)] py-2 pl-9 pr-3 text-[var(--app-text)] outline-none placeholder:text-[var(--app-muted)] focus:border-[var(--app-accent)]"
            style={{ fontSize: "12px" }}
          />
        </label>
        <div className="flex rounded-xl border border-[var(--app-border)] bg-[var(--app-elevated)] p-0.5">
          {(["all", "enabled", "attention"] as const).map((value) => (
            <button
              type="button"
              key={value}
              onClick={() => setFilter(value)}
              className="rounded-lg px-2.5 py-1.5 capitalize transition-colors"
              style={{
                fontSize: "11px",
                color: filter === value ? "var(--app-text)" : "var(--app-muted)",
                background: filter === value ? "var(--app-accent-soft)" : "transparent",
              }}
            >
              {value}
            </button>
          ))}
        </div>
      </div>

      {plugins.length === 0 ? (
        <EmptyPlugins onRescan={rescan} scanning={scanning} />
      ) : visible.length === 0 ? (
        <div className="px-4 py-10 text-center text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
          No plugins match this view.
        </div>
      ) : (
        <div className="space-y-2">
          {visible.map((plugin) => (
            <PluginCard
              key={plugin.id}
              plugin={plugin}
              busy={pendingIds.has(plugin.id)}
              onToggle={(enabled) => void toggle(plugin, enabled)}
              showForm={showForm}
            />
          ))}
        </div>
      )}

      <p className="px-3 pt-1 text-[var(--app-muted)]" style={{ fontSize: "11px", lineHeight: 1.5 }}>
        Local plugins execute trusted Python code in the Chitrika process. Enable only plugins you trust.
      </p>
    </div>
  );
}

function PluginCard({
  plugin,
  busy,
  onToggle,
  showForm,
}: {
  plugin: PluginInfo;
  busy: boolean;
  onToggle: (enabled: boolean) => void;
  showForm?: (form: React.ReactNode | null) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasOperations = Boolean(plugin.plugin_api?.endpoints.length);
  const healthy = plugin.available && !plugin.load_error;

  return (
    <article
      className="overflow-hidden rounded-2xl border bg-white/[0.025] transition-colors"
      style={{
        borderColor: plugin.load_error ? "rgba(248,113,113,0.3)" : "var(--app-border)",
        opacity: plugin.available ? 1 : 0.62,
      }}
    >
      <div className="px-4 py-3.5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-500/10">
            {plugin.available ? <Puzzle size={18} className="text-sky-400" /> : <CircleOff size={18} className="text-amber-400" />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-sm font-semibold text-[var(--app-text)]">{plugin.name}</span>
              <span className="rounded-md bg-white/5 px-1.5 py-0.5 text-[var(--app-muted)]" style={{ fontSize: "10px" }}>
                v{plugin.version}
              </span>
              <StatusBadge plugin={plugin} />
            </div>
            <p className="mt-0.5 text-[var(--app-muted)]" style={{ fontSize: "12px", lineHeight: 1.45 }}>
              {plugin.description || "No description provided."}
            </p>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[var(--app-muted)]" style={{ fontSize: "10px" }}>
              <span>{plugin.id}</span>
              {plugin.author && <span>by {plugin.author}</span>}
              <span>{plugin.entrypoint}</span>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            {plugin.has_config && (
              <button
                type="button"
                onClick={() => showForm?.(
                  <PluginConfigForm plugin={plugin} onClose={() => showForm?.(null)} />,
                )}
                className="rounded-lg p-2 text-[var(--app-muted)] transition-colors hover:bg-white/5 hover:text-[var(--app-accent)]"
                title="Configure plugin"
              >
                <Settings2 size={15} />
              </button>
            )}
            {hasOperations && (
              <button
                type="button"
                onClick={() => setExpanded((value) => !value)}
                className="rounded-lg p-2 text-[var(--app-muted)] transition-colors hover:bg-white/5 hover:text-[var(--app-accent)]"
                title="Plugin operations"
                aria-expanded={expanded}
              >
                <ChevronDown size={15} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
              </button>
            )}
            <div className="relative ml-1 flex items-center">
              <SwitchToggle
                checked={plugin.enabled && plugin.available}
                onCheckedChange={onToggle}
                disabled={busy || !plugin.available}
              />
              {busy && <Loader2 size={12} className="absolute -left-4 animate-spin text-[var(--app-accent)]" />}
            </div>
          </div>
        </div>

        {!healthy && (
          <div className="mt-3 rounded-lg bg-red-500/[0.07] px-3 py-2 text-red-300" style={{ fontSize: "11px" }}>
            {plugin.load_error || "Plugin files are missing from disk."}
          </div>
        )}
      </div>

      {expanded && plugin.plugin_api && (
        <div className="border-t border-[var(--app-border)] bg-black/10 px-3 pb-3">
          <PluginPanel pluginId={plugin.id} api={plugin.plugin_api} />
        </div>
      )}
    </article>
  );
}

function StatusBadge({ plugin }: { plugin: PluginInfo }) {
  const state = !plugin.available
    ? { label: "Missing", color: "#F59E0B", background: "rgba(245,158,11,0.12)" }
    : plugin.load_error
      ? { label: "Error", color: "#F87171", background: "rgba(248,113,113,0.12)" }
      : plugin.enabled
        ? { label: "Active", color: "#34D399", background: "rgba(52,211,153,0.12)" }
        : { label: "Disabled", color: "var(--app-muted)", background: "rgba(112,132,153,0.12)" };
  return (
    <span className="rounded-full px-2 py-0.5" style={{ fontSize: "10px", fontWeight: 600, color: state.color, background: state.background }}>
      {state.label}
    </span>
  );
}

function RuntimeMetric({
  label,
  value,
  icon,
  tone = "default",
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  tone?: "default" | "success" | "warning" | "muted";
}) {
  const color = tone === "success" ? "#34D399" : tone === "warning" ? "#FBBF24" : tone === "muted" ? "var(--app-muted)" : "var(--app-accent)";
  return (
    <div className="rounded-xl border border-[var(--app-border)] bg-[var(--app-elevated)] px-3 py-2.5">
      <div className="mb-1 flex items-center gap-1.5" style={{ color }}>
        {icon}
        <span className="text-[var(--app-muted)]" style={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>{label}</span>
      </div>
      <div className="text-lg font-semibold text-[var(--app-text)]">{value}</div>
    </div>
  );
}

function EmptyPlugins({ onRescan, scanning }: { onRescan: () => Promise<void>; scanning: boolean }) {
  return (
    <div className="mx-1 rounded-2xl border border-dashed border-[var(--app-border)] px-6 py-12 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5">
        <Wrench size={22} className="text-[var(--app-muted)]" />
      </div>
      <p className="text-sm font-medium text-[var(--app-text)]">No local plugins discovered</p>
      <p className="mx-auto mt-1 max-w-sm text-[var(--app-muted)]" style={{ fontSize: "12px", lineHeight: 1.5 }}>
        Add a plugin directory containing plugin.json, then scan the runtime again.
      </p>
      <button
        type="button"
        onClick={() => void onRescan()}
        disabled={scanning}
        className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[var(--app-accent)] px-3.5 py-2 text-white disabled:opacity-50"
        style={{ fontSize: "12px", fontWeight: 600 }}
      >
        {scanning ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
        Scan plugins
      </button>
    </div>
  );
}
