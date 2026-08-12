import { memo, useMemo } from "react";
import { motion } from "motion/react";
import { AlertTriangle, RefreshCw, Square, Volume2 } from "lucide-react";

import type { Chat, Message } from "../services/api";

interface Props {
  message: Message;
  chat?: Chat;
  showAvatar: boolean;
  showTimestamp: boolean;
  ttsEnabled: boolean;
  isSpeaking: boolean;
  isTtsLoading: boolean;
  onSpeak: (message: Message) => void;
  onStopSpeaking: () => void;
  onGenerationError: (message: Message) => void;
  onOpenMenu: (message: Message, x: number, y: number) => void;
}

export const ChatMessageBubble = memo(function ChatMessageBubble({
  message,
  chat,
  showAvatar,
  showTimestamp,
  ttsEnabled,
  isSpeaking,
  isTtsLoading,
  onSpeak,
  onStopSpeaking,
  onGenerationError,
  onOpenMenu,
}: Props) {
  const isUser = message.role === "user";
  const isRecalled = message.content.startsWith("(recalled) ");
  const segments = useMemo(
    () =>
      isUser
        ? [message.content.replace(/\r\n/g, "\n").trimEnd()]
        : splitAssistantBubbleSegments(message.content),
    [isUser, message.content],
  );

  if (isRecalled) {
    return (
      <motion.div
        onContextMenu={(event) => {
          event.preventDefault();
          onOpenMenu(message, event.clientX, event.clientY);
        }}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, transition: { duration: 0.12 } }}
        transition={{ duration: 0.18, ease: "easeOut" }}
        className="flex justify-center my-2"
      >
        <div
          className="px-2.5 py-1 rounded-md text-[var(--app-muted)]"
          style={{
            background: "rgba(112,132,153,0.12)",
            fontSize: "12px",
            lineHeight: "1.4",
          }}
        >
          You recalled a message
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      onContextMenu={(event) => {
        event.preventDefault();
        onOpenMenu(message, event.clientX, event.clientY);
      }}
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.12 } }}
      transition={{ duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`group/message flex gap-2 mb-3 ${
        isUser ? "justify-end items-end" : "justify-start items-start"
      }`}
    >
      {!isUser && (
        <div className="w-7 shrink-0" style={{ marginTop: "2px" }}>
          {showAvatar && (
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-white"
              style={{
                background: chat?.color || "var(--app-accent)",
                fontSize: "11px",
                fontWeight: 700,
              }}
            >
              {chat?.initials || "?"}
            </div>
          )}
        </div>
      )}

      <div
        className={`relative flex flex-col gap-1.5 max-w-[min(76%,680px)] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        {segments.map((segment, index) => {
          const isFirst = index === 0;
          const isLast = index === segments.length - 1;
          return (
            <div
              key={`${message.id}-${index}`}
              className="max-w-full px-4 py-2.5 relative shadow-sm backdrop-blur"
              style={{
                background: isUser
                  ? "var(--app-user-bubble)"
                  : "var(--app-assistant-bubble)",
                border: isUser
                  ? "1px solid color-mix(in srgb, var(--app-accent-strong) 30%, transparent)"
                  : "1px solid var(--app-border)",
                borderRadius: getBubbleRadius(
                  isUser,
                  isFirst,
                  isLast,
                  segments.length,
                ),
                boxShadow: isUser
                  ? "0 8px 20px rgba(0,0,0,0.12)"
                  : "0 6px 18px rgba(0,0,0,0.08)",
              }}
            >
              <p
                className="whitespace-pre-wrap break-words"
                style={{
                  fontSize: "var(--app-font-bubble)",
                  lineHeight: "1.6",
                  color: isUser ? "white" : "var(--app-text)",
                }}
              >
                {segment}
              </p>
            </div>
          );
        })}
        {!isUser && ttsEnabled && message.content.trim() && (
          <button
            type="button"
            onClick={() => (isSpeaking ? onStopSpeaking() : onSpeak(message))}
            className="absolute -right-8 top-1 rounded-full p-1.5 text-[var(--app-muted)] opacity-0 transition-opacity hover:text-[var(--app-text)] group-hover/message:opacity-100"
            aria-label={isSpeaking ? "Stop speech" : "Play speech"}
            title={isSpeaking ? "Stop speech" : "Play speech"}
            disabled={isTtsLoading}
          >
            {isSpeaking ? <Square size={14} /> : <Volume2 size={15} />}
          </button>
        )}
        {isTtsLoading && (
          <div
            className="absolute -right-8 top-1 p-1.5 text-[var(--app-muted)]"
            aria-label="Loading speech"
          >
            <RefreshCw size={14} className="animate-spin" />
          </div>
        )}
        {!isUser &&
          message.generation_status &&
          message.generation_status !== "complete" && (
            <button
              type="button"
              onClick={() => onGenerationError(message)}
              className="inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] text-amber-500"
              title="Open response error details"
            >
              <AlertTriangle size={11} />
              {message.generation_status === "interrupted"
                ? "Interrupted"
                : "Response error"}
            </button>
          )}
        {showTimestamp && message.time && (
          <div
            className={`pointer-events-none absolute -bottom-4 whitespace-nowrap opacity-0 transition-opacity duration-150 group-hover/message:opacity-60 ${
              isUser ? "right-1" : "left-1"
            }`}
            style={{
              fontSize: "11px",
              lineHeight: 1,
              color: "var(--app-muted)",
            }}
          >
            {message.time}
          </div>
        )}
      </div>
    </motion.div>
  );
});

function getBubbleRadius(
  isUser: boolean,
  isFirst: boolean,
  isLast: boolean,
  count: number,
): string {
  if (count === 1) {
    return isUser ? "14px 14px 5px 14px" : "14px 14px 14px 5px";
  }
  if (isUser) {
    return isFirst ? "14px 14px 5px 14px" : "14px 5px 5px 14px";
  }
  if (isFirst) return "14px 14px 14px 5px";
  return isLast ? "5px 14px 14px 5px" : "5px 14px 14px 5px";
}

function splitAssistantBubbleSegments(content: string): string[] {
  const normalized = content.replace(/\r\n/g, "\n").trimEnd();
  if (!normalized) return [""];
  if (normalized.includes("```")) {
    return [normalized.replace(/\n{3,}/g, "\n\n")];
  }
  const parts = normalized
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length <= 1) return [normalized];
  const shouldSplit =
    normalized.length <= 520 &&
    parts.length <= 6 &&
    parts.every((part) => part.length <= 96 && !looksLikeStructuredBlock(part));
  return shouldSplit ? parts : [normalized.replace(/\n{3,}/g, "\n\n")];
}

function looksLikeStructuredBlock(text: string): boolean {
  return text
    .split("\n")
    .some((line) => /^\s*(?:[-*]|\d+[.)]|#{1,6}\s|>\s)/.test(line));
}
