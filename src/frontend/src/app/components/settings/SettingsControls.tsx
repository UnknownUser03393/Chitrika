import { useEffect, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import * as Switch from "@radix-ui/react-switch";

import { fetchGPTSoVITSVoices, type GPTSoVITSVoice } from "../../services/api";

export function SectionLabel({
  label,
  color = "var(--app-accent)",
}: {
  label: string;
  color?: string;
}) {
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

export function NavItem({
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

export function SwitchToggle({
  checked,
  onCheckedChange,
  disabled = false,
}: {
  checked: boolean;
  onCheckedChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <Switch.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      className="relative inline-flex cursor-pointer rounded-full outline-none shrink-0 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
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

export function TTSField({
  label,
  value,
  type = "text",
  onChange,
}: {
  label: string;
  value: string;
  type?: "text" | "password";
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <div className="text-[var(--app-muted)] mb-1" style={{ fontSize: "12px" }}>
        {label}
      </div>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-elevated)] px-3 py-2 text-[var(--app-text)] outline-none focus:border-[var(--app-accent)]"
        style={{ fontSize: "13px" }}
      />
    </label>
  );
}

export function TTSVoicePicker({
  value,
  onSelect,
}: {
  value: string;
  onSelect: (voice: GPTSoVITSVoice) => void;
}) {
  const [voices, setVoices] = useState<GPTSoVITSVoice[]>([]);
  const [loading, setLoading] = useState(false);
  const didAutoSelectRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchGPTSoVITSVoices()
      .then((list) => {
        if (!cancelled) setVoices(list);
      })
      .catch(() => {
        if (!cancelled) setVoices([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (didAutoSelectRef.current) return;
    if (value) {
      didAutoSelectRef.current = true;
      return;
    }
    if (!loading && voices.length > 0) {
      didAutoSelectRef.current = true;
      onSelect(voices[0]);
    }
  }, [value, loading, voices, onSelect]);

  const selected = voices.find((voice) => voice.ref_audio_path === value);

  return (
    <label className="block">
      <div className="text-[var(--app-muted)] mb-1" style={{ fontSize: "12px" }}>
        Voice
      </div>
      <select
        value={selected?.ref_audio_path || ""}
        onChange={(event) => {
          const voice = voices.find((item) => item.ref_audio_path === event.target.value);
          if (voice) onSelect(voice);
        }}
        className="w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-elevated)] px-3 py-2 text-[var(--app-text)] outline-none focus:border-[var(--app-accent)]"
        style={{ fontSize: "13px" }}
      >
        <option value="" disabled>
          {loading ? "Loading voices…" : voices.length ? "选择参考音频" : "没有可用音色"}
        </option>
        {voices.map((voice) => (
          <option key={voice.ref_audio_path} value={voice.ref_audio_path}>
            {voice.label}
          </option>
        ))}
      </select>
      {selected && (
        <div
          className="text-[var(--app-muted)] mt-1 truncate"
          style={{ fontSize: "11px" }}
          title={selected.ref_audio_path}
        >
          {selected.ref_audio_path}
        </div>
      )}
    </label>
  );
}

export function AppSlider({
  value,
  min = 0,
  max = 1,
  step = 0.01,
  onValueChange,
}: {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onValueChange: (value: number) => void;
}) {
  return (
    <SliderPrimitive.Root
      value={[value]}
      min={min}
      max={max}
      step={step}
      onValueChange={([next]) => onValueChange(next)}
      className="relative flex h-5 w-full flex-1 touch-none select-none items-center"
    >
      <SliderPrimitive.Track
        className="relative h-1.5 grow overflow-hidden rounded-full"
        style={{ background: "var(--app-border)" }}
      >
        <SliderPrimitive.Range
          className="absolute h-full rounded-full"
          style={{ background: "var(--app-accent)" }}
        />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        className="block size-[18px] shrink-0 rounded-full outline-none transition-transform hover:scale-110"
        style={{
          background: "#fff",
          border: "2.5px solid var(--app-accent)",
          boxShadow: "0 1px 5px rgba(0,0,0,0.22)",
        }}
      />
    </SliderPrimitive.Root>
  );
}
