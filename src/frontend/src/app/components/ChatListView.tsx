import { useState, useEffect, useCallback, useRef } from "react";
import { PanelLeftClose, Search, Pin, Settings, Plus, RefreshCw, Trash2, Info } from "lucide-react";
import { toast } from "sonner";
import type { Chat } from "../services/api";
import {
  clearConversationMessages,
  deleteConversation,
  fetchConversations,
} from "../services/api";

interface Props {
  activeChatId: string;
  setActiveChatId: (id: string) => void;
  onSettingsClick: () => void;
  onToggleSidebar: () => void;
  /** Increment to force a refresh of the conversation list. */
  refreshKey?: number;
  /** Callback after creating a conversation. */
  onChatListChanged?: () => void;
  /** Called when the "+" new-chat button is clicked. */
  onNewChat?: () => void;
  /** Called after a conversation is deleted. */
  onChatDeleted?: () => void;
  /** Called after a conversation's messages are cleared. */
  onChatMessagesCleared?: (chatId: string) => void;
  /** Called when the "About Chitrika" button is clicked. */
  onHomeClick?: () => void;
}

export function ChatListView({
  activeChatId,
  setActiveChatId,
  onSettingsClick,
  onToggleSidebar,
  refreshKey,
  onChatListChanged,
  onNewChat,
  onChatDeleted,
  onChatMessagesCleared,
  onHomeClick,
}: Props) {
  const [search, setSearch] = useState("");
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch conversations from the backend
  const loadChats = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchConversations();
      setChats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load conversations");
      // If backend is not running, fall back to empty list
      setChats([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChats();
  }, [loadChats, refreshKey]);

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{
    chatId: string;
    x: number;
    y: number;
  } | null>(null);

  const handleContextMenu = (chatId: string, e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({ chatId, x: e.clientX, y: e.clientY });
  };

  const handleDeleteChat = async (chatId: string) => {
    setContextMenu(null);
    try {
      await deleteConversation(chatId);
      onChatDeleted?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete conversation");
    }
  };

  const handleClearMessages = async (chatId: string) => {
    setContextMenu(null);
    try {
      await clearConversationMessages(chatId);
      onChatMessagesCleared?.(chatId);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to clear messages");
    }
  };

  // Close context menu on any click
  useEffect(() => {
    const close = () => setContextMenu(null);
    if (contextMenu) {
      window.addEventListener("click", close);
      return () => window.removeEventListener("click", close);
    }
  }, [contextMenu]);

  const pinned = chats.filter(
    (c) => (c.pinned || false) && c.name.toLowerCase().includes(search.toLowerCase())
  );
  const recent = chats.filter(
    (c) => !(c.pinned || false) && c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center gap-2 px-4 shrink-0 border-b border-[var(--app-border)]"
        style={{ minHeight: "64px" }}
      >
        <span
          className="flex-1 text-[var(--app-text)]"
          style={{ fontSize: "19px", fontWeight: 700, letterSpacing: "-0.3px" }}
        >
          Chitrika
        </span>
        <button
          onClick={onHomeClick}
          className="p-1.5 rounded-full text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
          aria-label="About Chitrika"
          title="About Chitrika"
        >
          <Info size={18} />
        </button>
        <button
          onClick={onNewChat}
          className="p-1.5 rounded-full text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
          aria-label="New chat"
          title="New chat"
        >
          <Plus size={18} />
        </button>
        <button
          onClick={onToggleSidebar}
          className="p-1.5 rounded-full text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
          aria-label="Collapse sidebar"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-2 shrink-0">
        <div className="flex items-center gap-2 rounded-2xl px-3 py-2 bg-[var(--app-bg)] border border-[var(--app-border)]">
          <Search size={15} className="text-[var(--app-muted)] shrink-0" />
          <input
            type="text"
            placeholder="Search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent flex-1 text-[var(--app-text)] placeholder-[var(--app-subtle)] outline-none"
            style={{ fontSize: "14px" }}
          />
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        {/* Loading state */}
        {loading && (
          <div className="px-4 py-6 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3 animate-pulse">
                <div className="w-12 h-12 rounded-full bg-white/5" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-white/5 rounded w-2/3" />
                  <div className="h-3 bg-white/5 rounded w-full" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div className="text-center py-8 px-4">
            <p className="text-[var(--app-muted)] mb-3" style={{ fontSize: "14px" }}>
              {error}
            </p>
            <button
              onClick={loadChats}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--app-elevated)] text-[var(--app-text)] transition-colors"
              style={{ fontSize: "14px" }}
            >
              <RefreshCw size={14} />
              Retry
            </button>
          </div>
        )}

        {/* Content */}
        {!loading && !error && (
          <>
            {pinned.length > 0 && (
              <>
                {pinned.map((chat) => (
                  <ChatItem
                    key={chat.id}
                    chat={chat}
                    active={activeChatId === chat.id}
                    onClick={() => setActiveChatId(chat.id)}
                    onContextMenu={(e) => handleContextMenu(chat.id, e)}
                    showPin
                  />
                ))}
              </>
            )}
            {recent.map((chat) => (
              <ChatItem
                key={chat.id}
                chat={chat}
                active={activeChatId === chat.id}
                onClick={() => setActiveChatId(chat.id)}
                onContextMenu={(e) => handleContextMenu(chat.id, e)}
              />
            ))}
            {pinned.length === 0 && recent.length === 0 && (
              <div className="text-center py-10 text-[var(--app-muted)]" style={{ fontSize: "14px" }}>
                No chats found
                <br />
                <button
                  onClick={onNewChat}
                  className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--app-elevated)] text-[var(--app-text)] transition-colors"
                >
                  <Plus size={16} />
                  Start a conversation
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Bottom Settings */}
      <div className="shrink-0" style={{ padding: "8px 12px" }}>
        <button
          onClick={onSettingsClick}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-[var(--app-muted)] hover:text-[var(--app-text)]"
        >
          <Settings size={20} />
          <span style={{ fontSize: "14px" }}>Settings</span>
        </button>
      </div>

      {/* Right-click context menu */}
      {contextMenu && (
        <div
          className="fixed z-50 py-1 rounded-lg shadow-lg"
          style={{
            left: Math.min(contextMenu.x, window.innerWidth - 160),
            top: Math.min(contextMenu.y, window.innerHeight - 100),
            background: "var(--app-elevated)",
            border: "1px solid var(--app-border)",
            boxShadow: "var(--app-shadow)",
            minWidth: "150px",
          }}
        >
          <button
            onClick={() => handleClearMessages(contextMenu.chatId)}
            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-red-500/10 transition-colors"
            style={{ fontSize: "13px" }}
          >
            <Trash2 size={14} className="text-[var(--app-danger)]" />
            <span className="text-[var(--app-danger)]">Clear Messages</span>
          </button>
          <button
            onClick={() => handleDeleteChat(contextMenu.chatId)}
            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-red-500/10 transition-colors"
            style={{ fontSize: "13px" }}
          >
            <Trash2 size={14} className="text-[var(--app-danger)]" />
            <span className="text-[var(--app-danger)]">Delete Conversation</span>
          </button>
        </div>
      )}
    </div>
  );
}

interface ChatItemProps {
  chat: Chat;
  active: boolean;
  onClick: () => void;
  onContextMenu?: (e: React.MouseEvent) => void;
  showPin?: boolean;
}

function ChatItem({ chat, active, onClick, onContextMenu, showPin }: ChatItemProps) {
  return (
    <button
      onClick={onClick}
      onContextMenu={onContextMenu}
      className={`w-full flex items-center gap-3 px-3.5 py-2.5 mx-2 my-1 rounded-2xl transition-colors text-left ${
        active ? "bg-[var(--app-accent-soft)] shadow-sm" : "hover:bg-[var(--app-hover)]"
      }`}
    >
      {/* Avatar */}
      <div
        className="w-11 h-11 rounded-2xl flex items-center justify-center text-white shrink-0 shadow-sm"
        style={{ background: chat.color, fontSize: "17px", fontWeight: 700 }}
      >
        {chat.initials}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1 min-w-0">
            {showPin && (
              <Pin
                size={11}
                className="text-[var(--app-muted)] shrink-0"
                style={{ transform: "rotate(45deg)" }}
              />
            )}
            <span
              className="text-[var(--app-text)] truncate"
              style={{ fontSize: "15px", fontWeight: 500 }}
            >
              {chat.name}
            </span>
          </div>
          <span className="text-[var(--app-muted)] shrink-0" style={{ fontSize: "12px" }}>
            {chat.time}
          </span>
        </div>

        <div className="flex items-center justify-between gap-2 mt-0.5">
          <span className="text-[var(--app-muted)] truncate" style={{ fontSize: "13px" }}>
            {chat.lastMessage}
          </span>
          {chat.unread > 0 && (
            <span
              className="shrink-0 rounded-full flex items-center justify-center"
              style={{
                background: active ? "var(--app-panel)" : "var(--app-accent)",
                color: active ? "var(--app-accent-strong)" : "#FFFFFF",
                fontSize: "11px",
                fontWeight: 700,
                minWidth: "20px",
                height: "20px",
                padding: "0 5px",
              }}
            >
              {chat.unread}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
