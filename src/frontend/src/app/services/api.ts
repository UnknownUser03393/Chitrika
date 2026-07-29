/**
 * Chitrika API client — thin wrapper around fetch with SSE support.
 */

const BASE: string = window.desktopAPI?.getApiBase?.() || "/api";

// ---------------------------------------------------------------------------
// Types (mirroring mockData.ts + backend DTOs)
// ---------------------------------------------------------------------------

export interface Chat {
  id: string;
  name: string;
  initials: string;
  color: string;
  lastMessage: string;
  time: string;
  unread: number;
  pinned?: boolean;
  character_id?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  time: string;
  created_at?: string;
  edited_at?: string | null;
  is_deleted?: boolean;
}

export interface AIModel {
  id: string;
  name: string;
  provider: string;
  color: string;
  initials: string;
  enabled: boolean;
  /** Personality distillation content (skill / system prompt). */
  skill?: string;
  /** Optional avatar image URL. */
  avatar_url?: string | null;
}

export interface Character {
  id: string;
  name: string;
  display_name: string;
  description: string | null;
  provider?: string;
  personality_prompt?: string;
  initials: string;
  color: string;
  avatar_url: string | null;
  enabled: boolean;
}

export interface EmotionState {
  character_id: string;
  emotions: Record<string, number>;
  mood: string;
  loneliness: number;
  dominant: string;
  updated_at: string;
}

export interface Memory {
  id: string;
  character_id: string;
  memory_type: "short_term" | "long_term" | "episodic";
  content: string;
  importance: number;
  emotional_valence: number | null;
  is_pinned: boolean;
  is_forgotten: boolean;
  created_at: string;
  last_accessed: string;
  access_count: number;
}

export interface RelationshipState {
  character_id: string;
  stage: "stranger" | "acquaintance" | "friend" | "close" | "intimate";
  affinity: number;
  familiarity: number;
  trust: number;
  interaction_count: number;
  positive_interaction_count: number;
  conflict_count: number;
  first_interaction_at: string | null;
  last_interaction_at: string | null;
  updated_at: string;
}

export interface PendingNotification {
  message_id: string;
  conversation_id: string;
  character_id: string | null;
  content_preview: string;
  is_proactive: boolean;
  created_at: string | null;
}

export interface BatchConversationResult {
  requested: number;
  affected: number;
  missing_ids: string[];
}

// ---------------------------------------------------------------------------
// Conversations (Chats)
// ---------------------------------------------------------------------------

export async function fetchConversations(): Promise<Chat[]> {
  const res = await fetch(`${BASE}/conversations`);
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.status}`);
  return res.json();
}

export async function createConversation(characterId: string): Promise<Chat> {
  const res = await fetch(`${BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ character_id: characterId }),
  });
  if (!res.ok) throw new Error(`Failed to create conversation: ${res.status}`);
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete conversation: ${res.status}`);
}

export async function batchDeleteConversations(ids: string[]): Promise<BatchConversationResult> {
  const res = await fetch(`${BASE}/conversations/batch/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ? `Failed to delete conversations: ${JSON.stringify(err.detail)}` : `Failed to delete conversations: ${res.status}`);
  }
  return res.json();
}

export async function clearConversationMessages(id: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${id}/messages`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to clear messages: ${res.status}`);
}

export async function batchClearConversationMessages(ids: string[]): Promise<BatchConversationResult> {
  const res = await fetch(`${BASE}/conversations/batch/clear-messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ? `Failed to clear conversations: ${JSON.stringify(err.detail)}` : `Failed to clear conversations: ${res.status}`);
  }
  return res.json();
}

export async function markConversationRead(id: string): Promise<number> {
  const res = await fetch(`${BASE}/conversations/${id}/read`, { method: "POST" });
  if (!res.ok) return 0;
  const data = await res.json();
  return data.marked_read || 0;
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export async function fetchMessages(conversationId: string): Promise<Message[]> {
  const res = await fetch(
    `${BASE}/conversations/${conversationId}/messages?limit=100`
  );
  if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
  const data = await res.json();
  return (data.messages || []).map((m: Message) => ({
    ...m,
    time: m.time || formatTime(m.created_at || ""),
  }));
}

/**
 * Send a message and stream the AI response via SSE.
 *
 * The LLM may reply with multiple messages (split on newlines). Each message
 * gets its own ``start`` / content chunks / ``done``. Callbacks reflect this:
 *
 * - ``onChunk`` – raw text arriving right now (can span messages)
 * - ``onMessageDone`` – one assistant message is complete
 * - ``onStreamEnd`` – the SSE stream ended (no more messages)
 * - ``onUserMessageSaved`` – the persisted user message id (replaces the
 *   temporary ``local-*`` id so recall/delete work without a reload)
 *
 * Returns an AbortController so the caller can cancel mid-stream.
 */
export function streamMessage(
  conversationId: string,
  content: string,
  onChunk: (text: string) => void,
  onMessageDone: (messageText: string, messageId: string) => void,
  onStreamEnd: () => void,
  onError: (error: string) => void,
  onUserMessageSaved?: (messageId: string) => void
): AbortController {
  const controller = new AbortController();

  fetch(`${BASE}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        onError(`Server error: ${res.status}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response stream");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      /** Accumulated text for the *current* message (reset on "start"). */
      let currentMessageText = "";
      let currentMessageId = "";
      let streamHadError = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            switch (event.type) {
              case "start":
                currentMessageId = event.message_id;
                currentMessageText = "";
                if (event.user_message_id) {
                  onUserMessageSaved?.(event.user_message_id);
                }
                break;
              case "content":
                currentMessageText += event.content;
                onChunk(event.content);
                break;
              case "done":
                if (currentMessageText) {
                  onMessageDone(currentMessageText, currentMessageId);
                }
                break;
              case "error":
                streamHadError = true;
                onError(event.message);
                break;
            }
          } catch {
            // Skip malformed SSE lines
          }
        }
      }

      // Stream ended naturally — notify the caller.
      if (!streamHadError) {
        onStreamEnd();
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    });

  return controller;
}

export async function editMessage(
  messageId: string,
  content: string
): Promise<Message> {
  const res = await fetch(`${BASE}/messages/${messageId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`Failed to edit message: ${res.status}`);
  return res.json();
}

export async function recallMessage(messageId: string): Promise<Message> {
  const res = await fetch(`${BASE}/messages/${messageId}/recall`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to recall message: ${res.status}`);
  return res.json();
}

export async function deleteMessage(messageId: string): Promise<void> {
  const res = await fetch(`${BASE}/messages/${messageId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete message: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Characters (AIModels)
// ---------------------------------------------------------------------------

export async function fetchCharacters(): Promise<Character[]> {
  const res = await fetch(`${BASE}/characters`);
  if (!res.ok) throw new Error(`Failed to fetch characters: ${res.status}`);
  const data = await res.json();
  return data.characters || [];
}

export async function createCharacter(data: {
  name: string;
  display_name: string;
  personality_prompt?: string;
  description?: string;
  provider?: string;
  initials?: string;
  color?: string;
  avatar_url?: string;
}): Promise<Character> {
  const res = await fetch(`${BASE}/characters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create character: ${res.status}`);
  }
  return res.json();
}

export async function updateCharacter(
  id: string,
  updates: Partial<Character>
): Promise<Character> {
  const res = await fetch(`${BASE}/characters/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update character: ${res.status}`);
  return res.json();
}

export async function deleteCharacter(id: string): Promise<void> {
  const res = await fetch(`${BASE}/characters/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete character: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Emotion
// ---------------------------------------------------------------------------

export async function fetchEmotion(characterId: string): Promise<EmotionState> {
  const res = await fetch(`${BASE}/characters/${characterId}/emotion`);
  if (!res.ok) throw new Error(`Failed to fetch emotion: ${res.status}`);
  return res.json();
}

export async function fetchPendingNotifications(): Promise<PendingNotification[]> {
  const res = await fetch(`${BASE}/desktop/notifications/pending`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchMemories(
  characterId: string,
  includeForgotten = false
): Promise<Memory[]> {
  const res = await fetch(
    `${BASE}/characters/${characterId}/memories?limit=200&include_forgotten=${includeForgotten}`
  );
  if (!res.ok) throw new Error(`Failed to fetch memories: ${res.status}`);
  const data = await res.json();
  return data.memories || [];
}

export async function fetchRelationship(characterId: string): Promise<RelationshipState> {
  const res = await fetch(`${BASE}/characters/${characterId}/relationship`);
  if (!res.ok) throw new Error(`Failed to fetch relationship: ${res.status}`);
  return res.json();
}

export async function createMemory(
  characterId: string,
  data: Pick<Memory, "memory_type" | "content"> & Partial<Pick<Memory, "importance" | "is_pinned">>
): Promise<Memory> {
  const res = await fetch(`${BASE}/characters/${characterId}/memories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create memory: ${res.status}`);
  return res.json();
}

export async function updateMemory(
  memoryId: string,
  updates: Partial<Pick<Memory, "content" | "importance" | "is_pinned" | "is_forgotten">>
): Promise<Memory> {
  const res = await fetch(`${BASE}/memories/${memoryId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update memory: ${res.status}`);
  return res.json();
}

export async function deleteMemory(memoryId: string): Promise<void> {
  const res = await fetch(`${BASE}/memories/${memoryId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete memory: ${res.status}`);
}

// ---------------------------------------------------------------------------
// LLM Providers
// ---------------------------------------------------------------------------

export interface LLMProvider {
  id: string;
  name: string;
  display_name: string;
  api_key: string;
  base_url: string;
  default_model: string;
  models: string[];
  is_default: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderCreate {
  name: string;
  display_name: string;
  api_key: string;
  base_url: string;
  default_model?: string;
  models?: string[];
  is_default?: boolean;
}

export interface LLMProviderUpdate {
  display_name?: string;
  api_key?: string;
  base_url?: string;
  default_model?: string;
  models?: string[];
  is_default?: boolean;
  enabled?: boolean;
}

export async function fetchProviders(): Promise<LLMProvider[]> {
  const res = await fetch(`${BASE}/providers`);
  if (!res.ok) throw new Error(`Failed to fetch providers: ${res.status}`);
  return res.json();
}

export async function fetchProvider(id: string): Promise<LLMProvider> {
  const res = await fetch(`${BASE}/providers/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch provider: ${res.status}`);
  return res.json();
}

export async function createProvider(
  data: LLMProviderCreate
): Promise<LLMProvider> {
  const res = await fetch(`${BASE}/providers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create provider: ${res.status}`);
  }
  return res.json();
}

export async function updateProvider(
  id: string,
  updates: LLMProviderUpdate
): Promise<LLMProvider> {
  const res = await fetch(`${BASE}/providers/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update provider: ${res.status}`);
  }
  return res.json();
}

export async function deleteProvider(id: string): Promise<void> {
  const res = await fetch(`${BASE}/providers/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete provider: ${res.status}`);
}

export interface ProviderModel {
  name: string;
  display_name: string;
}

export async function fetchProviderModels(
  providerId: string
): Promise<ProviderModel[]> {
  const res = await fetch(`${BASE}/providers/${providerId}/models`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch models: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Health / Status
// ---------------------------------------------------------------------------

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// App Settings (server-side, persisted in DB)
// ---------------------------------------------------------------------------

export interface AppSettings {
  heartbeat_interval_minutes: number;
  emotion_decay_rate: number;
  loneliness_threshold: number;
}

export async function fetchSettings(): Promise<AppSettings> {
  const res = await fetch(`${BASE}/settings`);
  if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`);
  return res.json();
}

export async function updateSettings(
  updates: Partial<AppSettings>
): Promise<AppSettings> {
  const res = await fetch(`${BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update settings: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Local plugins
// ---------------------------------------------------------------------------

export interface PluginInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  entrypoint: string;
  path: string;
  available: boolean;
  enabled: boolean;
  load_error: string | null;
  installed_at: string;
  updated_at: string;
}

export async function fetchPlugins(): Promise<PluginInfo[]> {
  const res = await fetch(`${BASE}/plugins`);
  if (!res.ok) throw new Error(`Failed to fetch plugins: ${res.status}`);
  return res.json();
}

export async function updatePlugin(id: string, enabled: boolean): Promise<PluginInfo> {
  const res = await fetch(`${BASE}/plugins/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update plugin: ${res.status}`);
  }
  return res.json();
}

export async function rescanPlugins(): Promise<PluginInfo[]> {
  const res = await fetch(`${BASE}/plugins/rescan`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to rescan plugins: ${res.status}`);
  return fetchPlugins();
}

// ---------------------------------------------------------------------------
// Import (data migration)
// ---------------------------------------------------------------------------

export interface ImportResult {
  imported_characters: number;
  imported_conversations: number;
  skipped_conversations: number;
  total_in_source: number;
}

export async function importDoubao(sourcePath: string): Promise<ImportResult> {
  const res = await fetch(`${BASE}/import/doubao`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_path: sourcePath }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Import failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Debug actions
// ---------------------------------------------------------------------------

export interface DebugActionRequest {
  character_id: string;
  conversation_id?: string;
  deliver_now?: boolean;
  content?: string;
  use_llm?: boolean;
  metadata?: Record<string, unknown>;
}

export interface DebugActionResponse {
  action: string;
  status: string;
  character_id: string;
  conversation_id: string | null;
  scheduled_message_id: string | null;
  delivered_message_id: string | null;
  delivered: boolean;
  details: Record<string, unknown>;
}

export async function runDebugAction(
  action: string,
  body: DebugActionRequest
): Promise<DebugActionResponse> {
  const res = await fetch(`${BASE}/debug/actions/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Debug action failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(dateStr: string): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  return `${Math.floor(days / 30)}个月前`;
}

/**
 * Convert a backend Character to the frontend AIModel shape.
 */
export function characterToModel(c: Character): AIModel {
  return {
    id: c.id,
    name: c.display_name || c.name,
    provider: c.provider || "deepseek",
    color: c.color,
    initials: c.initials || c.name.charAt(0).toUpperCase(),
    enabled: c.enabled,
    skill: c.personality_prompt || c.description || "",
    avatar_url: c.avatar_url,
  };
}
