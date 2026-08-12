import { useEffect, useRef, useState } from "react";
import { Activity, Brain, Download, Gauge, Heart, Sparkles } from "lucide-react";
import { toast } from "sonner";

import {
  downloadBackup,
  restoreBackup,
  type AppSettings,
} from "../../services/api";
import { AppSlider, SectionLabel, SwitchToggle } from "./SettingsControls";

interface AppSettingsPanelProps {
  settings: AppSettings | null;
  saving: boolean;
  onSave: (updates: Partial<AppSettings>) => Promise<void>;
}

const DEFAULT_SETTINGS: AppSettings = {
  heartbeat_interval_minutes: 5,
  emotion_decay_rate: 0.15,
  loneliness_threshold: 0.6,
  memory_llm_extraction: false,
  memory_episodic_summary: false,
};

export function AppSettingsPanel({
  settings,
  saving,
  onSave,
}: AppSettingsPanelProps) {
  const [form, setForm] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [dirty, setDirty] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (settings) {
      setForm(settings);
      setDirty(false);
    }
  }, [settings]);

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }));
    setDirty(true);
  };

  const handleSave = () => {
    onSave(form).then(() => setDirty(false));
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const result = await downloadBackup();
      toast.success(
        `备份已保存 · ${result.counts.messages} 条消息 / ${result.counts.memories} 条记忆 · ${(result.sizeBytes / 1024 / 1024).toFixed(1)} MB`,
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "备份导出失败");
    } finally {
      setExporting(false);
    }
  };

  const handleRestore = async (file: File) => {
    setRestoring(true);
    try {
      const result = await restoreBackup(file);
      toast.success(
        `恢复完成 · 新增 ${result.characters_created} 个角色 / ${result.conversations_created} 个会话 / ${result.messages_created} 条消息 / ${result.memories_created} 条记忆 · 已存在的自动跳过`,
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "备份恢复失败");
    } finally {
      setRestoring(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  if (!settings) {
    return (
      <div className="py-8 text-center">
        <div className="flex gap-1.5 justify-center">
          {[0, 1, 2].map((index) => (
            <div
              key={index}
              className="w-2 h-2 rounded-full bg-[var(--app-muted)] animate-bounce"
              style={{ animationDelay: `${index * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="py-2 px-2 space-y-1.5">
      <SectionLabel label="Server Configuration" />

      <div className="rounded-2xl bg-white/[0.03] px-3.5 py-3.5 space-y-3">
        <div className="flex items-center gap-3">
          <Activity size={18} className="text-[var(--app-muted)] shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
              Heartbeat Interval
            </div>
            <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
              Minutes between background ticks
            </div>
          </div>
        </div>
        <input
          type="number"
          min={1}
          max={1440}
          value={form.heartbeat_interval_minutes}
          onChange={(event) => update("heartbeat_interval_minutes", parseInt(event.target.value) || 5)}
          className="w-full rounded-xl px-3 py-2 text-[var(--app-text)] text-sm"
          style={{
            background: "var(--app-elevated)",
            border: "1px solid var(--app-border)",
            outline: "none",
          }}
        />
      </div>

      <div className="rounded-2xl bg-white/[0.03] px-3.5 py-3.5 space-y-3">
        <div className="flex items-center gap-3">
          <Gauge size={18} className="text-[var(--app-muted)] shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
              Emotion Decay Rate
            </div>
            <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
              How fast emotions drift toward neutral (0–1)
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <AppSlider
            value={form.emotion_decay_rate}
            min={0}
            max={1}
            step={0.01}
            onValueChange={(value) => update("emotion_decay_rate", value)}
          />
          <MetricValue value={form.emotion_decay_rate} />
        </div>
      </div>

      <div className="rounded-2xl bg-white/[0.03] px-3.5 py-3.5 space-y-3">
        <div className="flex items-center gap-3">
          <Heart size={18} className="text-[var(--app-muted)] shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
              Loneliness Threshold
            </div>
            <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
              Score that triggers proactive messaging (0–1)
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <AppSlider
            value={form.loneliness_threshold}
            min={0}
            max={1}
            step={0.01}
            onValueChange={(value) => update("loneliness_threshold", value)}
          />
          <MetricValue value={form.loneliness_threshold} />
        </div>
      </div>

      <ToggleSetting
        icon={<Sparkles size={18} className="text-[var(--app-muted)] shrink-0" />}
        title="LLM Memory Extraction"
        description="Extract durable facts with the AI (extra tokens per message; regex fallback still runs)"
        checked={form.memory_llm_extraction}
        onCheckedChange={(value) => update("memory_llm_extraction", value)}
      />

      <ToggleSetting
        icon={<Brain size={18} className="text-[var(--app-muted)] shrink-0" />}
        title="Episodic Memory"
        description="Compress old chats into lasting narrative memories (extra tokens; off by default)"
        checked={form.memory_episodic_summary}
        onCheckedChange={(value) => update("memory_episodic_summary", value)}
      />

      <SectionLabel label="Data Backup" />
      <div className="rounded-2xl bg-white/[0.03] px-3.5 py-3.5 space-y-3">
        <div className="flex items-center gap-3">
          <Download size={18} className="text-[var(--app-muted)] shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
              Backup &amp; Export
            </div>
            <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
              Save the entire database (characters, conversations, memories, settings) as a JSON file
            </div>
          </div>
        </div>
        <ActionButton onClick={handleExport} disabled={exporting}>
          {exporting ? "Exporting…" : "Download Backup"}
        </ActionButton>

        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) handleRestore(file);
          }}
        />
        <ActionButton onClick={() => fileInputRef.current?.click()} disabled={restoring}>
          {restoring ? "Restoring…" : "Restore from Backup"}
        </ActionButton>
      </div>

      <div className="mt-3 px-1">
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          className="w-full rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors"
          style={{
            background: dirty ? "var(--app-accent)" : "var(--app-elevated)",
            color: dirty ? "#fff" : "var(--app-muted)",
            opacity: dirty && !saving ? 1 : 0.7,
            cursor: dirty && !saving ? "pointer" : "default",
          }}
        >
          {saving ? "Saving…" : "Save Settings"}
        </button>
        {dirty && (
          <p className="text-[var(--app-muted)] text-center mt-1.5" style={{ fontSize: "11px" }}>
            Changes will take effect on the next heartbeat tick
          </p>
        )}
      </div>
    </div>
  );
}

function MetricValue({ value }: { value: number }) {
  return (
    <span
      className="w-12 text-right shrink-0 text-[var(--app-text)] rounded-lg px-1.5 py-1"
      style={{
        fontSize: "13px",
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
        background: "var(--app-elevated)",
        color: "var(--app-accent)",
      }}
    >
      {value.toFixed(2)}
    </span>
  );
}

function ToggleSetting({
  icon,
  title,
  description,
  checked,
  onCheckedChange,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  checked: boolean;
  onCheckedChange: (value: boolean) => void;
}) {
  return (
    <div className="rounded-2xl bg-white/[0.03] px-3.5 py-3.5 space-y-3">
      <div className="flex items-center gap-3">
        {icon}
        <div className="flex-1 min-w-0">
          <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
            {title}
          </div>
          <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
            {description}
          </div>
        </div>
        <SwitchToggle checked={checked} onCheckedChange={onCheckedChange} />
      </div>
    </div>
  );
}

function ActionButton({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors"
      style={{
        background: "var(--app-elevated)",
        border: "1px solid var(--app-border)",
        color: disabled ? "var(--app-muted)" : "var(--app-text)",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.7 : 1,
      }}
    >
      {children}
    </button>
  );
}
