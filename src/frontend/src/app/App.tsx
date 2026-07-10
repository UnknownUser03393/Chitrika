import { useState, useEffect, useCallback } from "react";
import { PanelLeftOpen, X, Hash } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import { ChatListView } from "./components/ChatListView";
import { ChatArea } from "./components/ChatArea";
import { SettingsView } from "./components/SettingsView";
import { LandingPage } from "./components/landing/LandingPage";
import { Toaster } from "./components/ui/sonner";
import type { Chat, Character } from "./services/api";
import { fetchConversations, fetchCharacters, createConversation, markConversationRead } from "./services/api";
import { usePreferences } from "./preferences";

type SidebarView = "chats" | "settings";

export default function App() {
  const { preferences, setPreference } = usePreferences();
  const [sidebarView, setSidebarView] = useState<SidebarView>("chats");
  const [activeChatId, setActiveChatId] = useState<string>("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chats, setChats] = useState<Chat[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [messageRefreshKey, setMessageRefreshKey] = useState(0);

  // Landing page visibility
  const [showLanding, setShowLanding] = useState(
    !preferences.landingSeen
  );

  // If user already has conversations, auto-dismiss landing
  useEffect(() => {
    if (!preferences.landingSeen && chats.length > 0) {
      setShowLanding(false);
      setPreference("landingSeen", true);
    }
  }, [chats, preferences.landingSeen, setPreference]);

  const handleGetStarted = () => {
    setShowLanding(false);
    setPreference("landingSeen", true);
  };

  // Right-panel form content (rendered instead of ChatArea)
  const [rightPanelContent, setRightPanelContent] = useState<React.ReactNode>(null);

  // New-chat dialog
  const [showNewChatDialog, setShowNewChatDialog] = useState(false);
  const [dialogChars, setDialogChars] = useState<Character[]>([]);
  const [dialogLoading, setDialogLoading] = useState(false);

  const loadChats = useCallback(async () => {
    try {
      const data = await fetchConversations();
      setChats(data);
      if (!activeChatId && data.length > 0) {
        setActiveChatId(data[0].id);
      }
    } catch {
      // Backend may not be running
    }
  }, [activeChatId]);

  useEffect(() => {
    loadChats();
  }, [refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Desktop (Electron) hooks — only active when window.desktopAPI exists
  useEffect(() => {
    const api = window.desktopAPI;
    if (!api) return;

    // Toast notification click → switch to that conversation
    api.onNotificationClick((conversationId: string) => {
      setActiveChatId(conversationId);
      api.showWindow();
    });

    // Window focused → refresh to pick up unread changes
    api.onWindowFocus(() => {
      setRefreshKey((k) => k + 1);
    });
  }, []);

  // Mark conversation read when active chat changes
  useEffect(() => {
    if (activeChatId) {
      markConversationRead(activeChatId).catch(() => {});
    }
  }, [activeChatId]);

  // Sync notification preference to Electron main process
  useEffect(() => {
    window.desktopAPI?.setNotificationsEnabled(preferences.notifications);
  }, [preferences.notifications]);

  const activeChat = chats.find((c) => c.id === activeChatId) || null;

  const handleSetActiveChatId = (id: string) => {
    setActiveChatId(id);
  };

  const handleChatListChanged = () => {
    setRefreshKey((k) => k + 1);
  };

  const handleChatMessagesCleared = () => {
    setRefreshKey((k) => k + 1);
    setMessageRefreshKey((k) => k + 1);
  };

  // Open new-chat dialog
  const openNewChatDialog = async () => {
    setShowNewChatDialog(true);
    setDialogLoading(true);
    try {
      const chars = await fetchCharacters();
      setDialogChars(chars.filter((c) => c.enabled));
    } catch {
      setDialogChars([]);
    }
    setDialogLoading(false);
  };

  // Character IDs that already have a conversation
  const existingCharIds = new Set(
    chats.map((c) => c.character_id).filter(Boolean) as string[]
  );

  // Create conversation from dialog
  const handleCreateFromDialog = async (characterId: string) => {
    if (existingCharIds.has(characterId)) return; // duplicate guard
    try {
      await createConversation(characterId);
      setShowNewChatDialog(false);
      handleChatListChanged();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create conversation");
    }
  };

  if (showLanding) {
    return (
      <>
        <Toaster />
        <AnimatePresence mode="wait">
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="h-screen w-screen overflow-hidden bg-[var(--app-bg)] text-[var(--app-text)]"
          >
            <LandingPage onGetStarted={handleGetStarted} />
          </motion.div>
        </AnimatePresence>
      </>
    );
  }

  return (
    <>
      <Toaster />
      <AnimatePresence mode="wait">
        <motion.div
          key="app"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="flex h-screen w-screen overflow-hidden bg-[var(--app-bg)] text-[var(--app-text)]"
        >
      {/* Left Sidebar */}
      <motion.div
        className="flex flex-col h-full shrink-0 bg-[var(--app-panel)] relative overflow-hidden border-r border-[var(--app-border)] shadow-[var(--app-shadow)]"
        initial={false}
        animate={{
          width: sidebarCollapsed ? 0 : 320,
          opacity: sidebarCollapsed ? 0 : 1,
        }}
        transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        <div className="overflow-x-hidden" style={{ width: "320px", height: "100%" }}>
          <AnimatePresence mode="wait">
            {sidebarView === "chats" ? (
              <motion.div
                key="chats"
                initial={{ x: -30, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: -30, opacity: 0 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
                className="flex flex-col h-full w-full overflow-x-hidden"
              >
                <ChatListView
                  activeChatId={activeChatId}
                  setActiveChatId={handleSetActiveChatId}
                  onSettingsClick={() => setSidebarView("settings")}
                  onToggleSidebar={() => setSidebarCollapsed(true)}
                  refreshKey={refreshKey}
                  onChatListChanged={handleChatListChanged}
                  onNewChat={openNewChatDialog}
                  onChatDeleted={handleChatListChanged}
                  onChatMessagesCleared={handleChatMessagesCleared}
                  onHomeClick={() => setShowLanding(true)}
                />
              </motion.div>
            ) : (
              <motion.div
                key="settings"
                initial={{ x: 30, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 30, opacity: 0 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
                className="flex flex-col h-full w-full overflow-x-hidden"
              >
                <SettingsView
                  prefs={preferences}
                  setPref={setPreference}
                  onBack={() => {
                    setSidebarView("chats");
                    setRightPanelContent(null);
                  }}
                  showForm={setRightPanelContent}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Collapsed top bar */}
      <AnimatePresence>
        {sidebarCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="flex flex-col shrink-0"
          >
            <div
              className="flex items-center px-4 bg-[var(--app-panel)]"
              style={{ minHeight: "56px", width: "56px" }}
            >
              <motion.button
                initial={{ x: -12 }}
                animate={{ x: 0 }}
                exit={{ x: -12 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
                onClick={() => setSidebarCollapsed(false)}
                className="p-1.5 rounded-full text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
                style={{ background: "transparent" }}
              >
                <PanelLeftOpen size={18} />
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Right Panel: ChatArea or Settings Forms + New-Chat Dialog overlay */}
      <div className="flex-1 relative min-w-0">
        <AnimatePresence mode="wait">
          {rightPanelContent ? (
            <motion.div
              key="form-content"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="h-full flex"
            >
              {rightPanelContent}
            </motion.div>
          ) : (
            <motion.div
              key="chat-area"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              <ChatArea
                activeChatId={activeChatId}
                chat={activeChat}
                prefs={preferences}
                refreshKey={messageRefreshKey}
                onChatListChanged={handleChatListChanged}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* New-Chat Dialog */}
        <AnimatePresence>
          {showNewChatDialog && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="absolute inset-0 z-50 flex items-center justify-center bg-black/50"
              role="dialog"
              aria-modal="true"
              aria-label="New Conversation"
              onClick={() => setShowNewChatDialog(false)}
              onKeyDown={(e) => { if (e.key === "Escape") setShowNewChatDialog(false); }}
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0, y: 10 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.95, opacity: 0, y: 10 }}
                transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
                onClick={(e) => e.stopPropagation()}
                className="bg-[var(--app-panel)] rounded-2xl overflow-hidden"
                style={{ width: "380px", maxHeight: "480px", boxShadow: "var(--app-shadow)" }}
              >
                {/* Dialog header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--app-border)]">
                  <span
                    className="text-[var(--app-text)]"
                    style={{ fontSize: "16px", fontWeight: 600 }}
                  >
                    New Conversation
                  </span>
                  <button
                    onClick={() => setShowNewChatDialog(false)}
                    className="p-1 rounded-full text-[var(--app-muted)] hover:text-[var(--app-text)] transition-colors"
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Character list */}
                <div className="overflow-y-auto px-2 py-2" style={{ maxHeight: "360px" }}>
                  {dialogLoading ? (
                    <div className="flex justify-center py-8">
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
                  ) : dialogChars.length === 0 ? (
                    <div className="text-center py-8 text-[var(--app-muted)]" style={{ fontSize: "14px" }}>
                      No characters available.
                      <br />
                      <span className="text-[var(--app-subtle)]">Go to Settings &gt; Model List to create one.</span>
                    </div>
                  ) : (
                    <>{dialogChars.map((ch) =>
                      <button
                        key={ch.id}
                        onClick={() => !existingCharIds.has(ch.id) && handleCreateFromDialog(ch.id)}
                        disabled={existingCharIds.has(ch.id)}
                        className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 transition-colors text-left disabled:opacity-30 disabled:cursor-not-allowed"
                        title={existingCharIds.has(ch.id) ? "Conversation already exists" : undefined}
                      >
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-white shrink-0"
                          style={{
                            background: ch.color,
                            fontSize: "14px",
                            fontWeight: 700,
                          }}
                        >
                          {ch.initials || ch.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-[var(--app-text)] truncate" style={{ fontSize: "14px", fontWeight: 500 }}>
                            {ch.display_name || ch.name}
                          </div>
                          <div className="text-[var(--app-muted)] truncate" style={{ fontSize: "12px" }}>
                            {existingCharIds.has(ch.id)
                              ? "Already in chat list"
                              : (ch.description || ch.provider || ch.name)}
                          </div>
                        </div>
                        {existingCharIds.has(ch.id) ? (
                          <span className="text-[var(--app-muted)] shrink-0" style={{ fontSize: "11px" }}>Added</span>
                        ) : (
                          <Hash size={16} className="text-[var(--app-muted)] shrink-0" />
                        )}
                      </button>
                    )}</>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      </motion.div>
    </AnimatePresence>
    </>
  );
}
