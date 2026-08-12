/**
 * Chitrika API client — thin wrapper around fetch with SSE support.
 */

import { API_BASE as BASE, apiFetch } from "./api-client";

export { streamMessage } from "./chat-stream";

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
  generation_status?: "complete" | "interrupted" | "error";
  error_detail?: string | null;
}

export interface StreamErrorInfo {
  code: string;
  message: string;
  details: string;
  message_id?: string;
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

export type TTSProvider = "openai" | "gptsovits";

export interface TTSRequest {
  provider?: TTSProvider;
  text: string;
  api_key: string;
  base_url: string;
  model: string;
  voice: string;
  speed: number;
  response_format?: string;
  /** GPT-SoVITS native fields (used when provider === "gptsovits"). */
  ref_audio_path?: string;
  prompt_text?: string;
  text_lang?: string;
  prompt_lang?: string;
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
  const res = await apiFetch(`${BASE}/conversations`);
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.status}`);
  return res.json();
}

export async function createConversation(characterId: string): Promise<Chat> {
  const res = await apiFetch(`${BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ character_id: characterId }),
  });
  if (!res.ok) throw new Error(`Failed to create conversation: ${res.status}`);
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await apiFetch(`${BASE}/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete conversation: ${res.status}`);
}

export async function batchDeleteConversations(ids: string[]): Promise<BatchConversationResult> {
  const res = await apiFetch(`${BASE}/conversations/batch/delete`, {
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
  const res = await apiFetch(`${BASE}/conversations/${id}/messages`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to clear messages: ${res.status}`);
}

export async function batchClearConversationMessages(ids: string[]): Promise<BatchConversationResult> {
  const res = await apiFetch(`${BASE}/conversations/batch/clear-messages`, {
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
  const res = await apiFetch(`${BASE}/conversations/${id}/read`, { method: "POST" });
  if (!res.ok) return 0;
  const data = await res.json();
  return data.marked_read || 0;
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export async function fetchMessages(conversationId: string): Promise<Message[]> {
  const res = await apiFetch(
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
export async function editMessage(
  messageId: string,
  content: string
): Promise<Message> {
  const res = await apiFetch(`${BASE}/messages/${messageId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`Failed to edit message: ${res.status}`);
  return res.json();
}

export async function recallMessage(messageId: string): Promise<Message> {
  const res = await apiFetch(`${BASE}/messages/${messageId}/recall`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to recall message: ${res.status}`);
  return res.json();
}

export async function deleteMessage(messageId: string): Promise<void> {
  const res = await apiFetch(`${BASE}/messages/${messageId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete message: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Characters (AIModels)
// ---------------------------------------------------------------------------

export async function fetchCharacters(): Promise<Character[]> {
  const res = await apiFetch(`${BASE}/characters`);
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
  const res = await apiFetch(`${BASE}/characters`, {
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
  const res = await apiFetch(`${BASE}/characters/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update character: ${res.status}`);
  return res.json();
}

export async function deleteCharacter(id: string): Promise<void> {
  const res = await apiFetch(`${BASE}/characters/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete character: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Emotion
// ---------------------------------------------------------------------------

export async function fetchEmotion(characterId: string): Promise<EmotionState> {
  const res = await apiFetch(`${BASE}/characters/${characterId}/emotion`);
  if (!res.ok) throw new Error(`Failed to fetch emotion: ${res.status}`);
  return res.json();
}

export async function fetchPendingNotifications(): Promise<PendingNotification[]> {
  const res = await apiFetch(`${BASE}/desktop/notifications/pending`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchMemories(
  characterId: string,
  includeForgotten = false
): Promise<Memory[]> {
  const res = await apiFetch(
    `${BASE}/characters/${characterId}/memories?limit=200&include_forgotten=${includeForgotten}`
  );
  if (!res.ok) throw new Error(`Failed to fetch memories: ${res.status}`);
  const data = await res.json();
  return data.memories || [];
}

export async function fetchRelationship(characterId: string): Promise<RelationshipState> {
  const res = await apiFetch(`${BASE}/characters/${characterId}/relationship`);
  if (!res.ok) throw new Error(`Failed to fetch relationship: ${res.status}`);
  return res.json();
}

export interface GPTSoVITSVoice {
  value: string;
  label: string;
  ref_audio_path: string;
  prompt_text: string;
  prompt_lang: string;
}

export async function fetchGPTSoVITSVoices(): Promise<GPTSoVITSVoice[]> {
  try {
    const data = await callPluginApi<{ voices?: GPTSoVITSVoice[] }>(
      "gptsovits",
      "GET",
      "/voices"
    );
    return data.voices || [];
  } catch {
    return [];
  }
}

export async function synthesizeTTS(data: TTSRequest): Promise<Blob> {
  const isGPT = data.provider === "gptsovits";
  const res = await apiFetch(`${BASE}/tts/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider: data.provider || "openai",
      response_format: isGPT ? undefined : "mp3",
      ...data,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to synthesize speech: ${res.status}`);
  }
  return res.blob();
}

export async function createMemory(
  characterId: string,
  data: Pick<Memory, "memory_type" | "content"> & Partial<Pick<Memory, "importance" | "is_pinned">>
): Promise<Memory> {
  const res = await apiFetch(`${BASE}/characters/${characterId}/memories`, {
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
  const res = await apiFetch(`${BASE}/memories/${memoryId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update memory: ${res.status}`);
  return res.json();
}

export async function deleteMemory(memoryId: string): Promise<void> {
  const res = await apiFetch(`${BASE}/memories/${memoryId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete memory: ${res.status}`);
}

// ---------------------------------------------------------------------------
// LLM Providers
// ---------------------------------------------------------------------------

export interface CustomProviderOption {
  value: string;
  label: string;
}

export interface CustomProviderField {
  key: string;
  label: string;
  input_type: "text" | "password" | "select";
  required: boolean;
  secret: boolean;
  default: string;
  placeholder: string;
  help_text: string;
  options: CustomProviderOption[];
  summary: boolean;
}

export interface CustomProviderAPI {
  fields: CustomProviderField[];
  supports_model_fetch: boolean;
  model_field_key: string | null;
}

export interface LLMProvider {
  id: string;
  name: string;
  display_name: string;
  provider_type: string;
  plugin_id: string | null;
  api_key: string;
  base_url: string;
  default_model: string;
  custom_config: Record<string, string>;
  models: string[];
  is_default: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderCreate {
  name: string;
  display_name: string;
  provider_type: string;
  plugin_id?: string | null;
  api_key: string;
  base_url: string;
  default_model?: string;
  custom_config?: Record<string, string>;
  models?: string[];
  is_default?: boolean;
}

export interface LLMProviderUpdate {
  display_name?: string;
  provider_type?: string;
  plugin_id?: string | null;
  api_key?: string;
  base_url?: string;
  default_model?: string;
  custom_config?: Record<string, string>;
  models?: string[];
  is_default?: boolean;
  enabled?: boolean;
}

export async function fetchProviders(): Promise<LLMProvider[]> {
  const res = await apiFetch(`${BASE}/providers`);
  if (!res.ok) throw new Error(`Failed to fetch providers: ${res.status}`);
  return res.json();
}

export async function fetchProvider(id: string): Promise<LLMProvider> {
  const res = await apiFetch(`${BASE}/providers/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch provider: ${res.status}`);
  return res.json();
}

export async function createProvider(
  data: LLMProviderCreate
): Promise<LLMProvider> {
  const res = await apiFetch(`${BASE}/providers`, {
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
  const res = await apiFetch(`${BASE}/providers/${id}`, {
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
  const res = await apiFetch(`${BASE}/providers/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete provider: ${res.status}`);
}

export interface PluginEndpoint {
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: string;
  summary: string;
  description: string;
}

export interface PluginAPI {
  endpoints: PluginEndpoint[];
}

export interface ProviderType {
  type: string;
  label: string;
  plugin_id: string | null;
  needs_api_key: boolean;
  needs_base_url: boolean;
  default_base_url: string;
  default_model: string;
  supports_model_fetch: boolean;
  custom_provider_api: CustomProviderAPI | null;
  plugin_api: PluginAPI | null;
}

/**
 * Call a plugin-declared endpoint (Plugin OpenAPI).
 *
 * ``path`` is relative to ``/api/plugins/{pluginId}/api``, e.g. ``/status``.
 */
export async function callPluginApi<T = Record<string, unknown>>(
  pluginId: string,
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const options: RequestInit = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const res = await apiFetch(`${BASE}/plugins/${pluginId}/api${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Plugin API ${method} ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface ProviderModel {
  name: string;
  display_name: string;
}

export async function fetchProviderTypes(): Promise<ProviderType[]> {
  const res = await apiFetch(`${BASE}/provider-types`);
  if (!res.ok) throw new Error(`Failed to fetch provider types: ${res.status}`);
  return res.json();
}

export async function fetchProviderModels(
  providerId: string
): Promise<ProviderModel[]> {
  const res = await apiFetch(`${BASE}/providers/${providerId}/models`);
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
    const res = await apiFetch(`${BASE}/health`);
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
  memory_llm_extraction: boolean;
  memory_episodic_summary: boolean;
}

export async function fetchSettings(): Promise<AppSettings> {
  const res = await apiFetch(`${BASE}/settings`);
  if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`);
  return res.json();
}

export async function updateSettings(
  updates: Partial<AppSettings>
): Promise<AppSettings> {
  const res = await apiFetch(`${BASE}/settings`, {
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
  plugin_api: PluginAPI | null;
  has_config: boolean;
}

export interface PluginScanResult {
  plugins: PluginInfo[];
  discovered: number;
  invalid: string[];
}

export interface PluginConfigField {
  key: string;
  label: string;
  input_type: "text" | "password" | "select";
  required: boolean;
  secret: boolean;
  default: string;
  placeholder: string;
  help_text: string;
  options: CustomProviderOption[];
  summary: boolean;
}

export interface PluginAction {
  key: string;
  label: string;
  method: string;
  path: string;
  confirm: boolean;
}

export interface PluginConfig {
  fields: PluginConfigField[];
  values: Record<string, string>;
  actions: PluginAction[];
}

export async function fetchPluginConfig(pluginId: string): Promise<PluginConfig> {
  const res = await apiFetch(`${BASE}/plugins/${encodeURIComponent(pluginId)}/config`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch plugin config: ${res.status}`);
  }
  return res.json();
}

export async function savePluginConfig(
  pluginId: string,
  values: Record<string, string>
): Promise<PluginConfig> {
  const res = await apiFetch(`${BASE}/plugins/${encodeURIComponent(pluginId)}/config`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to save plugin config: ${res.status}`);
  }
  return res.json();
}

export async function fetchPlugins(): Promise<PluginInfo[]> {
  const res = await apiFetch(`${BASE}/plugins`);
  if (!res.ok) throw new Error(`Failed to fetch plugins: ${res.status}`);
  return res.json();
}

export async function updatePlugin(id: string, enabled: boolean): Promise<PluginInfo> {
  const res = await apiFetch(`${BASE}/plugins/${encodeURIComponent(id)}`, {
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

export async function rescanPlugins(): Promise<PluginScanResult> {
  const res = await apiFetch(`${BASE}/plugins/rescan`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to rescan plugins: ${res.status}`);
  }
  const scan = (await res.json()) as { discovered: number; invalid: string[] };
  return {
    plugins: await fetchPlugins(),
    discovered: scan.discovered,
    invalid: scan.invalid,
  };
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
  const res = await apiFetch(`${BASE}/import/doubao`, {
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
// Export (full data backup)
// ---------------------------------------------------------------------------

export interface ExportResult {
  filename: string;
  sizeBytes: number;
  counts: {
    characters: number;
    conversations: number;
    messages: number;
    memories: number;
    settings: number;
  };
}

/**
 * Download a full database backup as a JSON file.
 * The backend streams an attachment; we turn it into a blob and save it.
 */
export async function downloadBackup(): Promise<ExportResult> {
  const res = await apiFetch(`${BASE}/export/all`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Export failed: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "chitrika-backup.json";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);

  const contentDisposition = res.headers.get("Content-Disposition") || "";
  const match = contentDisposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : "chitrika-backup.json";
  let counts = { characters: 0, conversations: 0, messages: 0, memories: 0, settings: 0 };
  try {
    const parsed = JSON.parse(await blob.text());
    counts = parsed.counts || counts;
  } catch {
    // Backup download worked; counts are informational only.
  }
  return { filename, sizeBytes: blob.size, counts };
}

export interface RestoreResult {
  status: string;
  characters_created: number;
  characters_skipped: number;
  conversations_created: number;
  conversations_skipped: number;
  messages_created: number;
  messages_skipped: number;
  memories_created: number;
  memories_skipped: number;
}

/** Upload a backup JSON file and merge it into the current database. */
export async function restoreBackup(file: File): Promise<RestoreResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch(`${BASE}/restore`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Restore failed: ${res.status}`);
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
  const res = await apiFetch(`${BASE}/debug/actions/${action}`, {
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
