import { Bell, Clock, CornerDownLeft, Trash2, Type, Volume2, Zap } from "lucide-react";

import type { Preferences } from "../../preferences";
import {
  SectionLabel,
  SwitchToggle,
  TTSField,
  TTSVoicePicker,
} from "./SettingsControls";

interface PreferencesSettingsProps {
  prefs: Preferences;
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
  mode: "preferences" | "tts";
}

const FONT_SIZE_OPTIONS = [
  {
    value: "Small",
    label: "Small",
    sample: "Compact",
    description: "Tighter spacing and denser reading",
    previewSize: "12px",
  },
  {
    value: "Medium",
    label: "Medium",
    sample: "Balanced",
    description: "Default size for everyday chat",
    previewSize: "14px",
  },
  {
    value: "Large",
    label: "Large",
    sample: "Comfortable",
    description: "Bigger text and easier scanning",
    previewSize: "16px",
  },
] as const;

export function PreferencesSettings({
  prefs,
  setPref,
  mode,
}: PreferencesSettingsProps) {
  return (
    <div className="py-2 px-2 space-y-1.5">
      {mode === "preferences" && (
        <>
          <SectionLabel label="Appearance" />
          <FontSizeSetting prefs={prefs} setPref={setPref} />

          <div className="mt-2">
            <SectionLabel label="Messaging" />
          </div>
          <PreferenceToggle
            icon={<Zap size={18} className="text-[var(--app-muted)] shrink-0" />}
            title="Stream Responses"
            description="Show replies as they arrive"
            checked={prefs.streamResponses}
            onCheckedChange={(value) => setPref("streamResponses", value)}
          />
          <PreferenceToggle
            icon={<CornerDownLeft size={18} className="text-[var(--app-muted)] shrink-0" />}
            title="Send on Enter"
            description="Shift+Enter for new line"
            checked={prefs.sendOnEnter}
            onCheckedChange={(value) => setPref("sendOnEnter", value)}
          />
          <PreferenceToggle
            icon={<Clock size={18} className="text-[var(--app-muted)] shrink-0" />}
            title="Show Timestamps"
            checked={prefs.showTimestamps}
            onCheckedChange={(value) => setPref("showTimestamps", value)}
          />
        </>
      )}

      {mode === "tts" && <TTSSettings prefs={prefs} setPref={setPref} />}

      {mode === "preferences" && (
        <>
          <div className="mt-2">
            <SectionLabel label="Notifications" />
          </div>
          <PreferenceToggle
            icon={<Bell size={18} className="text-[var(--app-muted)] shrink-0" />}
            title="Push Notifications"
            checked={prefs.notifications}
            onCheckedChange={(value) => setPref("notifications", value)}
          />

          <div className="mt-2">
            <SectionLabel label="Danger Zone" color="#EF4444" />
          </div>
          <button className="w-full flex items-center gap-3 px-3.5 py-3 rounded-2xl hover:bg-red-500/10 transition-colors text-left">
            <Trash2 size={18} className="text-[var(--app-danger)] shrink-0" />
            <span className="text-[var(--app-danger)]" style={{ fontSize: "14px", fontWeight: 500 }}>
              Clear All Chat History
            </span>
          </button>
        </>
      )}
    </div>
  );
}

function FontSizeSetting({
  prefs,
  setPref,
}: Pick<PreferencesSettingsProps, "prefs" | "setPref">) {
  return (
    <div className="rounded-2xl bg-white/[0.03] px-3.5 py-3.5 space-y-3">
      <div className="flex items-center gap-3">
        <Type size={18} className="text-[var(--app-muted)] shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
            Font Size
          </div>
          <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
            {prefs.fontSize}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {FONT_SIZE_OPTIONS.map((option) => {
          const selected = prefs.fontSize === option.value;
          return (
            <button
              key={option.value}
              onClick={() => setPref("fontSize", option.value)}
              className="w-full flex items-center gap-3 rounded-2xl border px-3 py-3 text-left transition-colors"
              style={{
                background: selected
                  ? "color-mix(in srgb, var(--app-accent) 10%, var(--app-elevated))"
                  : "var(--app-elevated)",
                borderColor: selected ? "var(--app-accent)" : "transparent",
              }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{
                  background: selected
                    ? "color-mix(in srgb, var(--app-accent) 16%, transparent)"
                    : "rgba(255,255,255,0.04)",
                  color: selected ? "var(--app-accent)" : "var(--app-text)",
                  fontSize: option.previewSize,
                  fontWeight: 700,
                }}
              >
                Aa
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 600 }}>
                    {option.label}
                  </span>
                  <span className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
                    {option.sample}
                  </span>
                </div>
                <div className="text-[var(--app-muted)] mt-0.5" style={{ fontSize: "12px", lineHeight: 1.45 }}>
                  {option.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function TTSSettings({
  prefs,
  setPref,
}: Pick<PreferencesSettingsProps, "prefs" | "setPref">) {
  const updateTTS = (updates: Partial<Preferences["tts"]>) => {
    setPref("tts", { ...prefs.tts, ...updates });
  };

  return (
    <>
      <div className="mt-2">
        <SectionLabel label="Text to Speech" />
      </div>
      <div className="rounded-xl bg-white/[0.03] px-3.5 py-3 space-y-3">
        <div className="flex items-center gap-3">
          <Volume2 size={18} className="text-[var(--app-muted)] shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
              AI Voice
            </div>
            <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
              {prefs.tts.provider === "gptsovits"
                ? "用本地 GPT-SoVITS 克隆音色朗读助手回复"
                : "Read assistant messages using an OpenAI-compatible TTS API"}
            </div>
          </div>
          <SwitchToggle
            checked={prefs.tts.enabled}
            onCheckedChange={(enabled) => updateTTS({ enabled })}
          />
        </div>

        {prefs.tts.enabled && (
          <>
            <div className="flex items-center gap-3">
              <span className="flex-1 text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
                Auto-play Replies
              </span>
              <SwitchToggle
                checked={prefs.tts.autoPlay}
                onCheckedChange={(autoPlay) => updateTTS({ autoPlay })}
              />
            </div>

            <TTSProviderPicker prefs={prefs} updateTTS={updateTTS} />
            {prefs.tts.provider === "gptsovits" ? (
              <GPTSoVITSFields prefs={prefs} updateTTS={updateTTS} />
            ) : (
              <OpenAITTSFields prefs={prefs} updateTTS={updateTTS} />
            )}
          </>
        )}
      </div>
    </>
  );
}

type UpdateTTS = (updates: Partial<Preferences["tts"]>) => void;

function TTSProviderPicker({ prefs, updateTTS }: { prefs: Preferences; updateTTS: UpdateTTS }) {
  const selectProvider = (provider: Preferences["tts"]["provider"]) => {
    updateTTS({
      provider,
      baseUrl:
        provider === "openai" && prefs.tts.baseUrl.startsWith("http://")
          ? "https://api.openai.com/v1"
          : provider === "gptsovits" && prefs.tts.baseUrl.includes("api.openai.com")
            ? "http://127.0.0.1:9880"
            : prefs.tts.baseUrl,
    });
  };

  return (
    <div className="grid grid-cols-2 gap-2">
      {([
        ["openai", "OpenAI", "Cloud API"],
        ["gptsovits", "GPT-SoVITS", "Local clone"],
      ] as const).map(([provider, title, subtitle]) => (
        <button
          key={provider}
          type="button"
          onClick={() => selectProvider(provider)}
          className="rounded-xl border px-3 py-2.5 text-left transition-colors"
          style={{
            background:
              prefs.tts.provider === provider
                ? "color-mix(in srgb, var(--app-accent) 10%, var(--app-elevated))"
                : "var(--app-elevated)",
            borderColor: prefs.tts.provider === provider ? "var(--app-accent)" : "transparent",
          }}
        >
          <div className="text-[var(--app-text)]" style={{ fontSize: "13px", fontWeight: 600 }}>
            {title}
          </div>
          <div className="text-[var(--app-muted)]" style={{ fontSize: "11px" }}>
            {subtitle}
          </div>
        </button>
      ))}
    </div>
  );
}

function GPTSoVITSFields({ prefs, updateTTS }: { prefs: Preferences; updateTTS: UpdateTTS }) {
  return (
    <>
      <TTSVoicePicker
        value={prefs.tts.refAudioPath}
        onSelect={(voice) =>
          updateTTS({
            refAudioPath: voice.ref_audio_path,
            promptText: voice.prompt_text,
            promptLang: voice.prompt_lang || "zh",
          })
        }
      />
      <TTSField label="Server URL" value={prefs.tts.baseUrl} onChange={(baseUrl) => updateTTS({ baseUrl })} />
      <div className="grid grid-cols-2 gap-2">
        <TTSField label="Text Lang" value={prefs.tts.textLang} onChange={(textLang) => updateTTS({ textLang })} />
        <TTSField label="Prompt Lang" value={prefs.tts.promptLang} onChange={(promptLang) => updateTTS({ promptLang })} />
      </div>
      <SpeedField prefs={prefs} updateTTS={updateTTS} />
      <p className="text-[var(--app-muted)]" style={{ fontSize: "11px", lineHeight: 1.5 }}>
        首次使用请在 设置 → Plugins 里启用 gptsovits 插件并点击「启动 GPT-SoVITS」。音色列表从参考音频列表读取。
      </p>
    </>
  );
}

function OpenAITTSFields({ prefs, updateTTS }: { prefs: Preferences; updateTTS: UpdateTTS }) {
  return (
    <>
      <TTSField label="API Key" value={prefs.tts.apiKey} type="password" onChange={(apiKey) => updateTTS({ apiKey })} />
      <TTSField label="Base URL" value={prefs.tts.baseUrl} onChange={(baseUrl) => updateTTS({ baseUrl })} />
      <div className="grid grid-cols-2 gap-2">
        <TTSField label="Model" value={prefs.tts.model} onChange={(model) => updateTTS({ model })} />
        <TTSField label="Voice" value={prefs.tts.voice} onChange={(voice) => updateTTS({ voice })} />
      </div>
      <SpeedField prefs={prefs} updateTTS={updateTTS} />
    </>
  );
}

function SpeedField({ prefs, updateTTS }: { prefs: Preferences; updateTTS: UpdateTTS }) {
  return (
    <label className="block">
      <div className="flex items-center justify-between text-[var(--app-muted)] mb-1" style={{ fontSize: "12px" }}>
        <span>Speed</span>
        <span>{prefs.tts.speed.toFixed(2)}x</span>
      </div>
      <input
        type="range"
        min="0.25"
        max="4"
        step="0.05"
        value={prefs.tts.speed}
        onChange={(event) => updateTTS({ speed: Number(event.target.value) })}
        className="w-full accent-[var(--app-accent)]"
      />
    </label>
  );
}

function PreferenceToggle({
  icon,
  title,
  description,
  checked,
  onCheckedChange,
}: {
  icon: React.ReactNode;
  title: string;
  description?: string;
  checked: boolean;
  onCheckedChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center gap-3 px-3.5 py-3 rounded-2xl hover:bg-white/[0.04]">
      {icon}
      <div className="flex-1 min-w-0">
        <div className="text-[var(--app-text)]" style={{ fontSize: "14px", fontWeight: 500 }}>
          {title}
        </div>
        {description && (
          <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
            {description}
          </div>
        )}
      </div>
      <SwitchToggle checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
}
