import { useEffect, useState } from "react";
import { Bug, Play, Send, CheckCircle, XCircle, Loader2, ChevronDown, Sparkles } from "lucide-react";
import { toast } from "sonner";
import type { Character, DebugActionResponse } from "../services/api";
import { fetchCharacters, runDebugAction } from "../services/api";

const DEBUG_ACTIONS = [
  {
    id: "loneliness_proactive_message",
    label: "Loneliness Proactive Message",
    description: "Force the character to send a loneliness-triggered message immediately",
  },
] as const;

export function DebugPanel() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const [characterId, setCharacterId] = useState("");
  const [actionId, setActionId] = useState(DEBUG_ACTIONS[0].id);
  const [content, setContent] = useState("");
  const [deliverNow, setDeliverNow] = useState(true);
  const [useLlm, setUseLlm] = useState(false);
  const [result, setResult] = useState<DebugActionResponse | null>(null);

  useEffect(() => {
    fetchCharacters()
      .then((chars) => {
        const enabled = chars.filter((c) => c.enabled);
        setCharacters(enabled);
        if (enabled.length > 0 && !characterId) {
          setCharacterId(enabled[0].id);
        }
      })
      .catch(() => toast.error("Failed to load characters"))
      .finally(() => setLoading(false));
  }, [characterId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRun = async () => {
    if (!characterId) return;
    setRunning(true);
    setResult(null);
    try {
      const data = await runDebugAction(actionId, {
        character_id: characterId,
        content: content.trim() || undefined,
        deliver_now: deliverNow,
        use_llm: useLlm,
      });
      setResult(data);
      if (data.delivered) {
        toast.success("Action executed — message delivered");
      } else {
        toast.success("Action executed — message queued");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Debug action failed");
    } finally {
      setRunning(false);
    }
  };

  const selectedChar = characters.find((c) => c.id === characterId);
  const currentAction = DEBUG_ACTIONS.find((a) => a.id === actionId);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {/* Intro */}
        <div className="flex items-center gap-2 text-[var(--app-muted)]" style={{ fontSize: "13px" }}>
          <Bug size={15} />
          <span>Force companion actions for development &amp; testing</span>
        </div>

        {/* Character picker */}
        <div>
          <label
            className="block text-[var(--app-text)] mb-1.5"
            style={{ fontSize: "13px", fontWeight: 500 }}
          >
            Character
          </label>
          {loading ? (
            <div className="flex items-center gap-2 py-2 text-[var(--app-muted)]" style={{ fontSize: "13px" }}>
              <Loader2 size={14} className="animate-spin" />
              Loading…
            </div>
          ) : characters.length === 0 ? (
            <p className="text-[var(--app-muted)]" style={{ fontSize: "13px" }}>
              No enabled characters found
            </p>
          ) : (
            <div className="relative">
              <select
                value={characterId}
                onChange={(e) => setCharacterId(e.target.value)}
                className="w-full appearance-none rounded-lg px-3 py-2.5 text-[var(--app-text)] border border-[var(--app-border)]"
                style={{
                  fontSize: "14px",
                  background: "var(--app-input-bg, #1C2B3A)",
                  paddingRight: "2rem",
                }}
              >
                {characters.map((ch) => (
                  <option key={ch.id} value={ch.id}>
                    {ch.display_name || ch.name}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={15}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--app-muted)]"
              />
            </div>
          )}
          {selectedChar && (
            <div className="flex items-center gap-2 mt-1.5">
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center text-white shrink-0"
                style={{ background: selectedChar.color, fontSize: "10px", fontWeight: 700 }}
              >
                {selectedChar.initials || selectedChar.name.charAt(0).toUpperCase()}
              </div>
              <span className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
                {selectedChar.name}
              </span>
            </div>
          )}
        </div>

        {/* Action picker */}
        <div>
          <label
            className="block text-[var(--app-text)] mb-1.5"
            style={{ fontSize: "13px", fontWeight: 500 }}
          >
            Action
          </label>
          <div className="space-y-1.5">
            {DEBUG_ACTIONS.map((action) => (
              <button
                key={action.id}
                onClick={() => {
                  setActionId(action.id);
                  setResult(null);
                }}
                className="w-full text-left px-3 py-2.5 rounded-lg border transition-colors"
                style={{
                  fontSize: "14px",
                  background: actionId === action.id
                    ? "rgba(79,163,227,0.12)"
                    : "var(--app-input-bg, #1C2B3A)",
                  borderColor: actionId === action.id
                    ? "var(--app-accent, #4FA3E3)"
                    : "var(--app-border)",
                }}
              >
                <div className="text-[var(--app-text)]" style={{ fontWeight: 500 }}>
                  {action.label}
                </div>
                <div className="text-[var(--app-muted)] mt-0.5" style={{ fontSize: "12px" }}>
                  {action.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* LLM generation toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={15} style={{ color: useLlm ? "#F59E0B" : "var(--app-muted)" }} />
            <div>
              <div className="text-[var(--app-text)]" style={{ fontSize: "13px", fontWeight: 500 }}>
                Generate with LLM
              </div>
              <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
                Context-aware message from the character&rsquo;s provider
              </div>
            </div>
          </div>
          <button
            onClick={() => setUseLlm(!useLlm)}
            className="relative w-11 h-6 rounded-full transition-colors shrink-0"
            style={{
              background: useLlm ? "#F59E0B" : "var(--app-border)",
            }}
            role="switch"
            aria-checked={useLlm}
          >
            <span
              className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"
              style={{
                transform: useLlm ? "translateX(20px)" : "translateX(0)",
              }}
            />
          </button>
        </div>

        {/* Content override — disabled when LLM generates */}
        <div>
          <label
            className="block text-[var(--app-text)] mb-1.5"
            style={{ fontSize: "13px", fontWeight: 500 }}
          >
            Message content{" "}
            <span className="text-[var(--app-muted)]" style={{ fontWeight: 400 }}>
              {useLlm
                ? "(LLM generates; this is a fallback if LLM fails)"
                : "(optional — uses fallback when empty)"}
            </span>
          </label>
          <textarea
            value={useLlm ? "" : content}
            onChange={(e) => setContent(e.target.value)}
            rows={3}
            placeholder={
              useLlm
                ? "LLM will generate the message…"
                : "Enter custom message content…"
            }
            disabled={useLlm}
            className="w-full rounded-lg px-3 py-2.5 text-[var(--app-text)] border border-[var(--app-border)] resize-none disabled:opacity-40"
            style={{
              fontSize: "14px",
              background: "var(--app-input-bg, #1C2B3A)",
            }}
          />
        </div>

        {/* Deliver now toggle */}
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[var(--app-text)]" style={{ fontSize: "13px", fontWeight: 500 }}>
              Deliver immediately
            </div>
            <div className="text-[var(--app-muted)]" style={{ fontSize: "12px" }}>
              Message appears in chat right away
            </div>
          </div>
          <button
            onClick={() => setDeliverNow(!deliverNow)}
            className="relative w-11 h-6 rounded-full transition-colors"
            style={{
              background: deliverNow ? "var(--app-accent, #4FA3E3)" : "var(--app-border)",
            }}
            role="switch"
            aria-checked={deliverNow}
          >
            <span
              className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"
              style={{
                transform: deliverNow ? "translateX(20px)" : "translateX(0)",
              }}
            />
          </button>
        </div>

        {/* Run button */}
        <button
          onClick={handleRun}
          disabled={running || !characterId}
          className="w-full flex items-center justify-center gap-2 rounded-lg py-2.5 text-white font-medium transition-opacity disabled:opacity-50"
          style={{
            fontSize: "14px",
            background: "var(--app-accent, #4FA3E3)",
          }}
        >
          {running ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Running…
            </>
          ) : (
            <>
              <Play size={16} />
              Run {currentAction?.label ?? actionId}
            </>
          )}
        </button>

        {/* Result */}
        {result && (
          <div
            className="rounded-lg p-4 space-y-2"
            style={{
              background: result.status === "ok"
                ? "rgba(16,185,129,0.08)"
                : "rgba(239,68,68,0.08)",
              border: `1px solid ${result.status === "ok" ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
            }}
          >
            <div className="flex items-center gap-2">
              {result.status === "ok" ? (
                <CheckCircle size={16} style={{ color: "#10B981" }} />
              ) : (
                <XCircle size={16} style={{ color: "#EF4444" }} />
              )}
              <span
                className="text-[var(--app-text)]"
                style={{ fontSize: "14px", fontWeight: 600 }}
              >
                {result.action}
              </span>
            </div>

            <div className="space-y-1" style={{ fontSize: "13px" }}>
              <Row label="Status" value={result.status} />
              <Row label="Delivered" value={result.delivered ? "Yes ✓" : "No"} />
              {typeof result.details?.llm_used === "boolean" && (
                <Row
                  label="LLM used"
                  value={result.details.llm_used ? "Yes ✨" : "No"}
                />
              )}
              {typeof result.details?.content === "string" && (
                <Row label="Content" value={result.details.content} />
              )}
              {result.conversation_id && (
                <Row label="Conversation" value={result.conversation_id} mono />
              )}
              {result.scheduled_message_id && (
                <Row label="Scheduled msg" value={result.scheduled_message_id} mono />
              )}
              {result.delivered_message_id && (
                <Row label="Delivered msg" value={result.delivered_message_id} mono />
              )}
            </div>

            {Object.keys(result.details).length > 0 && (
              <details className="mt-2">
                <summary
                  className="text-[var(--app-muted)] cursor-pointer"
                  style={{ fontSize: "12px" }}
                >
                  Raw details
                </summary>
                <pre
                  className="mt-1 p-2 rounded text-[var(--app-muted)] overflow-x-auto"
                  style={{
                    fontSize: "11px",
                    background: "var(--app-input-bg, #1C2B3A)",
                  }}
                >
                  {JSON.stringify(result.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}

        {/* Send insight hint */}
        {result?.delivered && (
          <div
            className="flex items-start gap-2 text-[var(--app-muted)]"
            style={{ fontSize: "12px" }}
          >
            <Send size={13} className="shrink-0 mt-0.5" />
            <span>
              Return to the chat list — you'll see the new message in the conversation.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex gap-2">
      <span className="text-[var(--app-muted)] shrink-0">{label}:</span>
      <span
        className="text-[var(--app-text)] truncate"
        style={mono ? { fontFamily: "ui-monospace, monospace", fontSize: "11px" } : undefined}
      >
        {value}
      </span>
    </div>
  );
}
