import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Search,
  MoreVertical,
  Send,
  Paperclip,
  Phone,
  Bot,
  RefreshCw,
  Undo2,
  Trash2,
  ArrowDown,
} from "lucide-react";
import type { Message, Chat, StreamErrorInfo } from "../services/api";
import { deleteMessage, fetchMessages, recallMessage, streamMessage, synthesizeTTS } from "../services/api";
import type { Preferences } from "../preferences";
import { ResponseErrorDialog } from "./ResponseErrorDialog";
import { ChatMessageBubble } from "./ChatMessageBubble";

interface Props {
  activeChatId: string;
  /** The active chat metadata (null if none selected). */
  chat: Chat | null;
  prefs: Preferences;
  /** Increment to force message history reload for the active chat. */
  refreshKey?: number;
  /** Called when the chat list should be refreshed (e.g., after first message). */
  onChatListChanged?: () => void;
}

export function ChatArea({ activeChatId, chat, prefs, refreshKey, onChatListChanged }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageMenu, setMessageMenu] = useState<{
    message: Message;
    x: number;
    y: number;
  } | null>(null);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isAwaitingFirstChunk, setIsAwaitingFirstChunk] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [responseError, setResponseError] = useState<StreamErrorInfo | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const shouldFollowRef = useRef(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bufferedReplyRef = useRef("");
  const pendingStreamTextRef = useRef("");
  const streamingAssistantRef = useRef<Message | null>(null);
  const streamFrameRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const ttsRequestRef = useRef(0);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [ttsLoadingMessageId, setTtsLoadingMessageId] = useState<string | null>(null);

  const stopTTS = useCallback(() => {
    ttsRequestRef.current += 1;
    audioRef.current?.pause();
    audioRef.current = null;
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setSpeakingMessageId(null);
    setTtsLoadingMessageId(null);
  }, []);

  const playTTS = useCallback(async (message: Message) => {
    if (!prefs.tts.enabled || message.role !== "assistant" || !message.content.trim()) {
      return;
    }

    const isGPT = prefs.tts.provider === "gptsovits";
    if (!isGPT && !prefs.tts.apiKey.trim()) {
      return;
    }
    if (isGPT && !prefs.tts.refAudioPath.trim()) {
      setError("还没有选择 GPT-SoVITS 音色，请先在设置里选一个参考音频");
      return;
    }

    const requestId = ttsRequestRef.current + 1;
    ttsRequestRef.current = requestId;
    stopTTS();
    ttsRequestRef.current = requestId;
    setTtsLoadingMessageId(message.id);

    try {
      const blob = await synthesizeTTS({
        provider: prefs.tts.provider,
        text: message.content,
        api_key: prefs.tts.apiKey,
        base_url: prefs.tts.baseUrl,
        model: prefs.tts.model,
        voice: prefs.tts.voice,
        speed: prefs.tts.speed,
        ref_audio_path: isGPT ? prefs.tts.refAudioPath : undefined,
        prompt_text: isGPT ? prefs.tts.promptText : undefined,
        text_lang: isGPT ? prefs.tts.textLang : undefined,
        prompt_lang: isGPT ? prefs.tts.promptLang : undefined,
      });
      if (ttsRequestRef.current !== requestId) return;

      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;
      audioUrlRef.current = audioUrl;
      setTtsLoadingMessageId(null);
      setSpeakingMessageId(message.id);
      audio.onended = stopTTS;
      audio.onerror = stopTTS;
      await audio.play();
    } catch (err) {
      if (ttsRequestRef.current === requestId) {
        setError(err instanceof Error ? err.message : "Failed to play speech");
        stopTTS();
      }
    }
  }, [prefs.tts, stopTTS]);

  useEffect(() => stopTTS, [stopTTS]);

  // If the user toggles TTS off, stop any in-flight speech.
  useEffect(() => {
    if (!prefs.tts.enabled) stopTTS();
  }, [prefs.tts.enabled, stopTTS]);

  useEffect(() => {
    if (!messageMenu) return;

    const close = () => setMessageMenu(null);
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };

    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [messageMenu]);

  // Fetch messages when activeChatId changes
  useEffect(() => {
    if (!activeChatId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setResponseError(null);
    setIsAwaitingFirstChunk(false);
    bufferedReplyRef.current = "";
    pendingStreamTextRef.current = "";
    streamingAssistantRef.current = null;
    if (streamFrameRef.current !== null) {
      cancelAnimationFrame(streamFrameRef.current);
      streamFrameRef.current = null;
    }

    fetchMessages(activeChatId)
      .then((data) => {
        if (!cancelled) {
          setMessages(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load messages");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      abortRef.current?.abort();
      if (streamFrameRef.current !== null) {
        cancelAnimationFrame(streamFrameRef.current);
        streamFrameRef.current = null;
      }
    };
  }, [activeChatId, refreshKey]);

  // Scroll to bottom on new messages — only when user is near the bottom
  const handleChatScroll = useCallback(() => {
    const container = chatContainerRef.current;
    if (!container) return;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    const isNearBottom = distanceFromBottom < 80;
    shouldFollowRef.current = isNearBottom;
    setShowScrollButton(!isNearBottom && (isTyping || isAwaitingFirstChunk));
  }, [isTyping, isAwaitingFirstChunk]);

  useEffect(() => {
    if (!shouldFollowRef.current) return;
    const frame = requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({
        behavior: isTyping ? "auto" : "smooth",
        block: "end",
      });
    });
    return () => cancelAnimationFrame(frame);
  }, [messages, isTyping, isAwaitingFirstChunk]);

  const scrollToBottom = useCallback(() => {
    shouldFollowRef.current = true;
    setShowScrollButton(false);
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, []);

  const flushStreamingMessage = useCallback(() => {
    streamFrameRef.current = null;
    const assistantMessage = streamingAssistantRef.current;
    if (!assistantMessage) return;

    const content = pendingStreamTextRef.current;
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.id === assistantMessage.id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = {
          ...updated[idx],
          content,
        };
        return updated;
      }
      return [
        ...prev,
        { ...assistantMessage, content },
      ];
    });
  }, []);

  const scheduleStreamingFlush = useCallback(() => {
    if (streamFrameRef.current !== null) return;
    streamFrameRef.current = requestAnimationFrame(flushStreamingMessage);
  }, [flushStreamingMessage]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }, [input]);

  const handleSend = useCallback(() => {
    if (!input.trim() || isTyping || !activeChatId) return;

    const now = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMsg: Message = {
      id: `local-${Date.now()}`,
      role: "user",
      content: input.trim(),
      time: now,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);
    setIsAwaitingFirstChunk(true);
    bufferedReplyRef.current = "";
    pendingStreamTextRef.current = "";

    // One backend response = one stored message group. The renderer may split
    // short assistant paragraphs into multiple chat bubbles for a human feel.
    const assistantMessage: Message = {
      id: `streaming-${Date.now()}`,
      role: "assistant",
      content: "",
      time: "",
    };
    streamingAssistantRef.current = assistantMessage;

    abortRef.current = streamMessage(
      activeChatId,
      userMsg.content,
      // -- onChunk ----------------------------------------------
      (chunk) => {
        setIsAwaitingFirstChunk(false);
        bufferedReplyRef.current += chunk;
        pendingStreamTextRef.current = bufferedReplyRef.current;

        if (!prefs.streamResponses) {
          return;
        }

        scheduleStreamingFlush();
      },
      // -- onMessageDone ---------------------------------------
      (messageText, messageId) => {
        if (streamFrameRef.current !== null) {
          cancelAnimationFrame(streamFrameRef.current);
          streamFrameRef.current = null;
        }
        const replyTime = new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === assistantMessage.id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = {
              ...updated[idx],
              id: messageId || updated[idx].id,
              content: messageText,
              time: replyTime,
            };
            return updated;
          }
          if (messageText) {
            return [
              ...prev,
              {
                ...assistantMessage,
                id: messageId || assistantMessage.id,
                content: messageText,
                time: replyTime,
              },
            ];
          }
          return prev;
        });
        bufferedReplyRef.current = "";
        pendingStreamTextRef.current = "";
        streamingAssistantRef.current = null;
        if (prefs.tts.enabled && prefs.tts.autoPlay) {
          void playTTS({
            ...assistantMessage,
            id: messageId || assistantMessage.id,
            content: messageText,
            time: replyTime,
          });
        }
      },
      // -- onStreamEnd -----------------------------------------
      () => {
        setIsTyping(false);
        setIsAwaitingFirstChunk(false);
        bufferedReplyRef.current = "";
        pendingStreamTextRef.current = "";
        streamingAssistantRef.current = null;
        onChatListChanged?.();
      },
      // -- onError ---------------------------------------------
      (streamError) => {
        const partial = pendingStreamTextRef.current || bufferedReplyRef.current;
        const failedMessageId = streamError.message_id || assistantMessage.id;
        const replyTime = new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
        setIsTyping(false);
        setIsAwaitingFirstChunk(false);
        bufferedReplyRef.current = "";
        pendingStreamTextRef.current = "";
        streamingAssistantRef.current = null;
        if (streamFrameRef.current !== null) {
          cancelAnimationFrame(streamFrameRef.current);
          streamFrameRef.current = null;
        }
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === assistantMessage.id);
          const failedMessage: Message = {
            ...assistantMessage,
            id: failedMessageId,
            content: partial,
            time: replyTime,
            generation_status: streamError.code === "stream_disconnected" ? "interrupted" : "error",
            error_detail: streamError.details,
          };
          if (idx < 0) return [...prev, failedMessage];
          const updated = [...prev];
          updated[idx] = { ...updated[idx], ...failedMessage };
          return updated;
        });
        setResponseError(streamError);
        onChatListChanged?.();
      },
      // -- onUserMessageSaved ----------------------------------
      (userMessageId) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === userMsg.id ? { ...m, id: userMessageId } : m))
        );
      }
    );
  }, [input, isTyping, activeChatId, onChatListChanged, playTTS, prefs.streamResponses, prefs.tts.autoPlay, prefs.tts.enabled, scheduleStreamingFlush]);

  const handleRecall = useCallback(
    async (messageId: string) => {
      try {
        const recalled = await recallMessage(messageId);
        setMessages((prev) =>
          prev.map((message) => (message.id === messageId ? recalled : message))
        );
        onChatListChanged?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to recall message");
      }
    },
    [onChatListChanged]
  );

  const handleDeleteMessage = useCallback(
    async (messageId: string) => {
      try {
        await deleteMessage(messageId);
        setMessages((prev) => prev.filter((message) => message.id !== messageId));
        onChatListChanged?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete message");
      }
    },
    [onChatListChanged]
  );

  const openMessageMenu = useCallback((message: Message, x: number, y: number) => {
    if (message.id.startsWith("local-") || message.id.startsWith("streaming-")) {
      return;
    }
    setMessageMenu({ message, x, y });
  }, []);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (prefs.sendOnEnter && e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (!chat && !activeChatId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[var(--app-bg)]">
        <div className="text-center">
          <Bot size={48} className="text-[var(--app-muted)] mx-auto mb-4" />
          <p className="text-[var(--app-muted)]" style={{ fontSize: "16px" }}>
            Select a conversation or start a new one
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full min-w-0">
      <div className="flex items-center px-5 shrink-0 bg-[var(--app-panel)] min-h-[64px] border-b border-[var(--app-border)]">
        <div className="flex-1 min-w-0">
          <motion.span
            key={activeChatId}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.12, ease: "easeOut" }}
            className="block text-[var(--app-text)] truncate"
            style={{ fontSize: "var(--app-font-title)", fontWeight: 700 }}
          >
            {chat?.name || "Chat"}
          </motion.span>
        </div>
        <div className="flex items-center gap-0.5">
          <HeaderBtn icon={<Search size={18} />} label="Search messages" />
          <HeaderBtn icon={<Phone size={18} />} label="Voice call" />
          <HeaderBtn icon={<MoreVertical size={18} />} label="More options" />
        </div>
      </div>

      <div
        ref={chatContainerRef}
        onScroll={handleChatScroll}
        className="flex-1 overflow-y-auto px-5 py-7 bg-[var(--app-bg)] relative"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      >
        {loading && (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="flex gap-1.5">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full bg-[var(--app-muted)] animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}

        {!loading && error && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <p className="text-[var(--app-muted)]" style={{ fontSize: "14px" }}>
              {error}
            </p>
            <button
              onClick={() => {
                setError(null);
                setLoading(true);
                fetchMessages(activeChatId)
                  .then(setMessages)
                  .catch((err) =>
                    setError(err instanceof Error ? err.message : "Failed")
                  )
                  .finally(() => setLoading(false));
              }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--app-elevated)] text-[var(--app-text)] transition-colors"
              style={{ fontSize: "14px" }}
            >
              <RefreshCw size={14} />
              Retry
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            {messages.length === 0 && !isTyping ? (
              <div className="h-full">
                <EmptyChat chat={chat} />
              </div>
            ) : (
              <div className="flex flex-col gap-0.5 max-w-3xl mx-auto">
                <AnimatePresence initial={false}>
                  {messages.map((msg, i) => {
                    const prev = messages[i - 1];
                    const showAvatar =
                      msg.role === "assistant" &&
                      (!prev || prev.role === "user");
                    return (
                      <ChatMessageBubble
                        key={msg.id}
                        message={msg}
                        chat={chat || undefined}
                        showAvatar={showAvatar}
                        showTimestamp={prefs.showTimestamps}
                        ttsEnabled={prefs.tts.enabled && (
                          prefs.tts.provider === "gptsovits"
                            ? Boolean(prefs.tts.refAudioPath.trim())
                            : Boolean(prefs.tts.apiKey.trim())
                        )}
                        isSpeaking={speakingMessageId === msg.id}
                        isTtsLoading={ttsLoadingMessageId === msg.id}
                        onSpeak={playTTS}
                        onStopSpeaking={stopTTS}
                        onGenerationError={(message) => setResponseError({
                          code: message.generation_status || "generation_error",
                          message: message.generation_status === "interrupted"
                            ? "The stream disconnected while responding."
                            : "The upstream model failed while responding.",
                          details: message.error_detail || "No technical details were stored.",
                          message_id: message.id,
                        })}
                        onOpenMenu={openMessageMenu}
                      />
                    );
                  })}
                </AnimatePresence>
                <AnimatePresence>
                  {isAwaitingFirstChunk && <TypingIndicator chat={chat} />}
                </AnimatePresence>
                <div ref={bottomRef} />
                {/* Scroll-to-bottom FAB */}
                <AnimatePresence>
                  {showScrollButton && (
                    <motion.button
                      initial={{ opacity: 0, scale: 0.8, y: 8 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.8, y: 8 }}
                      transition={{ duration: 0.18, ease: "easeOut" }}
                      onClick={scrollToBottom}
                      className="sticky bottom-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1.5 px-4 py-2 rounded-full shadow-lg border transition-colors hover:scale-105 active:scale-95"
                      style={{
                        background: "var(--app-elevated)",
                        borderColor: "var(--app-border)",
                        color: "var(--app-text)",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.25)",
                      }}
                      aria-label="Scroll to bottom"
                    >
                      <ArrowDown size={14} />
                      <span style={{ fontSize: "12px", fontWeight: 500 }}>New messages</span>
                    </motion.button>
                  )}
                </AnimatePresence>
              </div>
            )}
          </>
        )}
      </div>

      <div className="shrink-0 px-5 pt-3 pb-4 bg-[var(--app-bg)] border-t border-[var(--app-border)]/70">
        <div className="flex items-center rounded-xl px-3 py-2 max-w-3xl mx-auto bg-[var(--app-panel)]">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message"
            rows={1}
            className="chat-input-textarea flex-1 bg-transparent text-[var(--app-text)] placeholder-[var(--app-subtle)] resize-none block mx-0.5 border-0 outline-none shadow-none appearance-none focus:outline-none focus-visible:outline-none focus:border-0 focus:shadow-none"
            style={{
              fontSize: "var(--app-font-input)",
              lineHeight: "20px",
              paddingTop: "5px",
              paddingBottom: "5px",
            }}
          />
          <button
            className="p-1.5 text-[var(--app-muted)] transition-colors shrink-0 rounded-full"
            aria-label="Attach file"
            title="Attach file — coming soon"
            disabled
          >
            <Paperclip size={18} />
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="p-1.5 rounded-full transition-colors shrink-0"
            style={{
              background:
                input.trim() && !isTyping ? "var(--app-accent)" : "transparent",
              color: input.trim() && !isTyping ? "white" : "var(--app-muted)",
            }}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
      {messageMenu && (
        <MessageContextMenu
          state={messageMenu}
          onRecall={(messageId) => {
            setMessageMenu(null);
            void handleRecall(messageId);
          }}
          onDelete={(messageId) => {
            setMessageMenu(null);
            void handleDeleteMessage(messageId);
          }}
        />
      )}
      <ResponseErrorDialog
        error={responseError}
        onClose={() => setResponseError(null)}
      />
    </div>
  );
}

function HeaderBtn({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      className="p-2 rounded-full text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
      aria-label={label}
      title={label}
      disabled
    >
      {icon}
    </button>
  );
}

function EmptyChat({ chat }: { chat: Chat | null }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div
        className="w-20 h-20 rounded-2xl flex items-center justify-center text-white shadow-[var(--app-shadow)]"
        style={{
          background: chat?.color || "var(--app-accent)",
          fontSize: "30px",
          fontWeight: 800,
        }}
      >
        {chat?.initials || "?"}
      </div>
      <div>
        <div
          className="text-[var(--app-text)] text-center"
          style={{ fontSize: "var(--app-font-headline)", fontWeight: 700 }}
        >
          {chat?.name || "Chat"}
        </div>
        <div
          className="text-[var(--app-muted)] text-center mt-1"
          style={{ fontSize: "14px" }}
        >
          Say something
        </div>
      </div>
      <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--app-panel)] border border-[var(--app-border)] shadow-sm">
        <Bot size={14} className="text-[var(--app-accent)]" />
        <span className="text-[var(--app-muted)]" style={{ fontSize: "13px" }}>
          Ready
        </span>
      </div>
    </div>
  );
}

function MessageContextMenu({
  state,
  onRecall,
  onDelete,
}: {
  state: { message: Message; x: number; y: number };
  onRecall: (messageId: string) => void;
  onDelete: (messageId: string) => void;
}) {
  const { message, x, y } = state;
  const isUser = message.role === "user";
  const isRecalled = message.content.startsWith("(recalled) ");
  const style = {
    left: Math.min(x, window.innerWidth - 180),
    top: Math.min(y, window.innerHeight - 88),
  };

  return (
    <div
      className="fixed z-50 min-w-[150px] overflow-hidden rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] py-1 shadow-2xl"
      style={style}
      onContextMenu={(event) => event.preventDefault()}
      onClick={(event) => event.stopPropagation()}
    >
      {isUser && !isRecalled ? (
        <button
          type="button"
          onClick={() => onRecall(message.id)}
          className="flex w-full items-center gap-2 px-3 py-2 text-left text-[var(--app-text)] hover:bg-white/10 transition-colors"
          style={{ fontSize: "13px" }}
        >
          <Undo2 size={14} />
          Recall
        </button>
      ) : (
        <button
          type="button"
          onClick={() => onDelete(message.id)}
          className="flex w-full items-center gap-2 px-3 py-2 text-left text-[var(--app-danger)] hover:bg-red-500/10 transition-colors"
          style={{ fontSize: "13px" }}
        >
          <Trash2 size={14} />
          Delete
        </button>
      )}
    </div>
  );
}

function TypingIndicator({ chat }: { chat: Chat | null }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.95 }}
      transition={{ duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="flex items-end gap-2 justify-start mb-1"
    >
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center text-white shrink-0"
        style={{
          background: chat?.color || "var(--app-accent)",
          fontSize: "11px",
          fontWeight: 700,
        }}
      >
        {chat?.initials || "?"}
      </div>
      <div className="px-4 py-3 bg-[var(--app-assistant-bubble)] rounded-tl-2xl rounded-tr-2xl rounded-br-2xl rounded-bl">
        <div className="flex gap-1 items-center" style={{ height: "14px" }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-[var(--app-muted)]"
              style={{
                animation: `chitrikaTyping 1.2s ${i * 0.2}s infinite ease-in-out`,
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
