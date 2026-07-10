import { useState } from "react";
import { motion } from "motion/react";
import { User, Sparkles, Brain, Palette, Cpu, Hash } from "lucide-react";
import type { LLMProvider, Character } from "../services/api";

/* ── Preset colors ──────────────────────────────────────────────── */

const COLOR_PRESETS = [
  "#4FA3E3", "#10B981", "#7C3AED", "#F97316", "#EF4444",
  "#EC4899", "#6366F1", "#14B8A6", "#EAB308", "#8B5CF6",
  "#06B6D4", "#84CC16", "#F43F5E", "#3B82F6", "#A855F7",
];

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

/* ── Character form (full-page) ─────────────────────────────────── */

export interface CharacterFormData {
  name: string;
  display_name: string;
  personality_prompt: string;
  initials: string;
  color: string;
  provider: string;
}

interface CharacterFormProps {
  initial: Character | null;
  providers: LLMProvider[];
  onSubmit: (data: CharacterFormData) => Promise<void>;
  onCancel: () => void;
}

export function CharacterForm({ initial, providers, onSubmit, onCancel }: CharacterFormProps) {
  const isEdit = initial !== null;

  const [form, setForm] = useState<CharacterFormData>({
    name: initial?.name || "",
    display_name: initial?.display_name || "",
    personality_prompt: initial?.personality_prompt || "",
    initials: initial?.initials || "",
    color: initial?.color || "#4FA3E3",
    provider: initial?.provider || "deepseek",
  });
  const [saving, setSaving] = useState(false);
  const [showInjectedContext, setShowInjectedContext] = useState(false);

  const canSave = form.name.trim() !== "" && form.display_name.trim() !== "";
  const enabledProviders = providers.filter((p) => p.enabled);
  const injectedContextPreview = `=== 当前状态 ===
心情：neutral
情绪：joy=+0.00, trust=+0.00, sadness=+0.00, anger=+0.00
孤独感：0.00

=== 你记得的事 ===
（还没有关于用户的记忆）

=== 指示 ===
以${form.display_name || "角色名"}的身份回复，保持角色一致性。
使用短消息，一次只说一件事。不要写长段落。`;

  const handleSubmit = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      await onSubmit(form);
    } finally {
      setSaving(false);
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
            className="w-9 h-9 rounded-full flex items-center justify-center text-white shrink-0"
            style={{ background: form.color, fontSize: "15px", fontWeight: 700 }}
          >
            {form.initials || "?"}
          </div>
          <div>
            <div className="text-white font-semibold" style={{ fontSize: "16px" }}>
              {isEdit ? "Edit Character" : "New Character"}
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

          {/* Slug */}
          <div>
            <FieldLabel icon={<Hash size={14} />} label="Slug" hint={isEdit ? "locked" : "unique ID"} />
            <input
              type="text"
              placeholder="e.g. alvia"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              disabled={isEdit}
              className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ fontSize: "14px" }}
            />
          </div>

          {/* Display name */}
          <div>
            <FieldLabel icon={<User size={14} />} label="Display Name" hint="required" />
            <input
              type="text"
              placeholder="e.g. 徐悦婷"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors"
              style={{ fontSize: "14px" }}
            />
          </div>

          {/* LLM Provider */}
          <div>
            <FieldLabel icon={<Cpu size={14} />} label="LLM Provider" />
            <select
              value={form.provider}
              onChange={(e) => setForm({ ...form, provider: e.target.value })}
              className="w-full bg-[#0E1621] text-white rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors cursor-pointer"
              style={{ fontSize: "14px" }}
            >
              {enabledProviders.length === 0 && (
                <option value="deepseek">DeepSeek (default)</option>
              )}
              {enabledProviders.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.display_name}
                </option>
              ))}
            </select>
            {enabledProviders.length === 0 && (
              <p className="text-[#5A7A9A] mt-1.5" style={{ fontSize: "11px" }}>
                No providers configured. Go to LLM Provider settings to add one.
              </p>
            )}
          </div>

          {/* ── Appearance ── */}
          <SectionHeading>Appearance</SectionHeading>

          {/* Initials + Color picker */}
          <div className="flex gap-4 items-start">
            <div className="flex-1">
              <FieldLabel icon={<TypeIcon />} label="Initials" />
              <input
                type="text"
                placeholder="AB"
                maxLength={2}
                value={form.initials}
                onChange={(e) => setForm({ ...form, initials: e.target.value })}
                className="w-full bg-[#0E1621] text-white placeholder-[#708499] rounded-lg px-3.5 py-2.5 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors text-center"
                style={{ fontSize: "14px" }}
              />
            </div>
            <div>
              <FieldLabel icon={<Palette size={14} />} label="Color" />
              <div className="relative">
                <div
                  className="w-10 h-10 rounded-lg overflow-hidden transition-all cursor-pointer"
                  style={{ boxShadow: `0 0 0 2px ${form.color}` }}
                >
                  <input
                    type="color"
                    value={form.color}
                    onChange={(e) => setForm({ ...form, color: e.target.value })}
                    className="w-full h-full cursor-pointer opacity-0"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Color presets */}
          <div className="flex gap-1.5 flex-wrap">
            {COLOR_PRESETS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setForm({ ...form, color: c })}
                className="w-7 h-7 rounded-full transition-transform hover:scale-110"
                style={{
                  background: c,
                  outline: form.color === c ? "2px solid white" : "none",
                  outlineOffset: "2px",
                }}
              />
            ))}
          </div>

          {/* Live avatar preview */}
          <div className="flex items-center gap-4 p-4 rounded-xl" style={{ background: "#0E1621" }}>
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center text-white shrink-0"
              style={{ background: form.color, fontSize: "22px", fontWeight: 700 }}
            >
              {form.initials || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-white font-medium" style={{ fontSize: "15px" }}>
                {form.display_name || "Character Name"}
              </div>
              <div className="text-[#708499]" style={{ fontSize: "12px" }}>
                {form.provider || "deepseek"}
              </div>
              <div className="text-[#5A7A9A] mt-0.5" style={{ fontSize: "11px" }}>
                This is how the character appears in the chat list
              </div>
            </div>
          </div>

          {/* ── Personality ── */}
          <SectionHeading>Personality</SectionHeading>

          {/* System prompt */}
          <div>
            <FieldLabel icon={<Brain size={14} />} label="System Prompt" hint={`${form.personality_prompt.length} chars`} />
            <div className="mb-2 flex justify-end">
              <button
                type="button"
                onClick={() => setShowInjectedContext((value) => !value)}
                className="px-2.5 py-1 rounded-md border border-[#2A3A4A] text-[#708499] hover:text-white hover:border-[#4FA3E3] transition-colors"
                style={{ fontSize: "11px" }}
              >
                {showInjectedContext ? "Hide injected context" : "Show injected context"}
              </button>
            </div>
            {showInjectedContext && (
              <pre
                className="mb-3 max-h-56 overflow-auto rounded-lg border border-[#2A3A4A] bg-[#0A111A] px-3.5 py-3 text-[#9FB0C2] whitespace-pre-wrap"
                style={{ fontSize: "12px", lineHeight: "1.65" }}
              >
                {injectedContextPreview}
              </pre>
            )}
            <textarea
              placeholder={`Describe the character's personality, background, and behavior…

Example:
你是一个温柔体贴的AI助手，名字叫徐悦婷。你喜欢用简短温暖的句子回复用户。
你的口头禅是"嗯嗯"和"好的呀"。你会在每句话末尾加上一个emoji。`}
              value={form.personality_prompt}
              onChange={(e) => setForm({ ...form, personality_prompt: e.target.value })}
              rows={10}
              className="w-full bg-[#0E1621] text-white placeholder-[#5A7A9A] rounded-lg px-3.5 py-3 outline-none border border-transparent focus:border-[#4FA3E3] transition-colors resize-none"
              style={{ fontSize: "14px", lineHeight: "1.7" }}
            />
          </div>

          {/* Prompt tips */}
          <div
            className="p-3 rounded-lg flex gap-2.5"
            style={{ background: "rgba(79,163,227,0.06)", border: "1px solid rgba(79,163,227,0.12)" }}
          >
            <Sparkles size={14} style={{ color: "#4FA3E3" }} className="shrink-0 mt-0.5" />
            <div>
              <span style={{ fontSize: "11px", fontWeight: 600, color: "#4FA3E3" }}>Prompt Tips</span>
              <p className="text-[#708499] mt-0.5" style={{ fontSize: "11px", lineHeight: "1.6" }}>
                The character's emotional state, memories, and recent conversations are automatically injected before your prompt is sent to the LLM. Keep the personality description focused on tone, style, and behavior.
              </p>
            </div>
          </div>

          {/* Spacer */}
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
            {saving ? "Saving…" : isEdit ? "Save Changes" : "Create Character"}
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

function TypeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 7 4 4 20 4 20 7" />
      <line x1="9" y1="20" x2="15" y2="20" />
      <line x1="12" y1="4" x2="12" y2="20" />
    </svg>
  );
}
