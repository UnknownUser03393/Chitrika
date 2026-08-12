# Chitrika

The best replacement for Qwen and Doubao's personified agent.

Chitrika is a desktop-native AI companion — a persistent digital persona with evolving emotional state, memory, and proactive messaging. Not a chatbot. More like someone who's always there.

## I18n

中文版README: README_zh.md

## Announcement

China banned Personified AI Agents on 2026/07/15.

Qwen, Doubao, XingHuo... all took down their `agent` features.

Chitrika is still here :)

## Features

- **Persistent identity** — each character has a personality prompt, visual identity (color/avatar), and evolves over time
- **8-dimension emotion system** — Plutchik-inspired (joy, sadness, anger, fear, trust, anticipation, surprise, disgust) with decay, deltas, and mood classification
- **Long-term memory** — short-term and core memories with importance scoring, full-text search, and automatic pruning
- **Proactive heartbeat** — background engine that ticks every N minutes, checks loneliness, and sends unprompted messages when the character "misses you"
- **SSE streaming** — real-time token-by-token chat response streaming
- **Multi-provider LLM** — pluggable LLM backend with full CRUD management UI; defaults to DeepSeek (OpenAI-compatible API)
- **In-app settings** — heartbeat interval, emotion decay, loneliness threshold managed via Settings UI / DB (no restart for most changes)
- **Multi-character** — run multiple personas, each with independent emotion and memory state
- **Electron desktop app** — native window, desktop toast notifications when the character messages you, backend lifecycle management
- **Landing page** — bilingual (zh/en) showcase with animated sections, mobile-responsive
- **One-click Doubao import** — migrate your Doubao Agent conversation history (agentmsg-shify export) in one API call — characters, conversations, timestamps preserved
- **Plugin system** — trusted local Python plugins with prompt hooks, managed via Settings UI; new plugins disabled by default for safety
- **ONNX emotion classifier** — NLP-based emotion detection from message text using a transformer model, complementing the keyword-heuristic delta system
- **Relationship tracking** — per-character relationship state (closeness, trust, affection) that evolves with conversation
- **Batch chat management** — multi-select conversations for batch delete or clear-messages
- **Companion Mind view** — real-time visualization of a character's emotional state, mood, and relationship metrics
- **Dark-themed UI** — Telegram/Messenger-style chat interface built with React 18, Radix UI, MUI, and Tailwind CSS v4

## Quick start

### Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) (package manager)
- [pnpm](https://pnpm.io/) (frontend)
- An LLM Provider API key (or skip for echo mode)

> [DeepSeek](https://platform.deepseek.com) is suggested because Chitrika optimized the system prompt for it. 

### 1. Clone & install

```bash
git clone <repo-url>
cd chitrika

# Backend
uv sync
uv pip install -e ".[dev]"

# Frontend
cd src/frontend
pnpm install
```

### 2. Configure

Most installs need **nothing**. Defaults work out of the box.

Optional bootstrap file (copy and edit only if you need to):

```bash
cp chitrika.json.example chitrika.json
```

```json
{
  "database_url": "sqlite:///./chitrika.db",
  "cors_origins": [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080"
  ]
}
```

Load order: **environment variables** → **`chitrika.json`** → **built-in defaults**.

Everything else is managed **in-app**:

| What | Where |
|------|--------|
| LLM API key / base URL / model | Settings → Providers |
| Heartbeat interval, emotion decay, loneliness threshold | Settings → App Settings |

> **No API key yet?** Seeded DeepSeek provider starts with an empty key and chat falls back to echo mode — great for testing the UI without burning tokens.

### 3. Run

```bash
# One process launcher: generates an ephemeral API token for both servers
python bootstrap.py
```

For manual two-terminal development, explicitly give both processes the same
token (never store it in localStorage or commit it):

```powershell
# Terminal 1: backend (port 8000)
$env:CHITRIKA_API_TOKEN = "replace-with-a-random-development-token"
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: frontend dev server (from src/frontend/)
$env:VITE_CHITRIKA_API_TOKEN = "replace-with-a-random-development-token"
pnpm dev
```

Open `http://127.0.0.1:8080` and start talking.

### 4. Desktop app (optional)

```bash
# From src/frontend/ — launches the Electron wrapper
# (backend must be running separately in dev mode)
pnpm electron:dev
```

In production builds, Electron manages the backend process automatically and shows desktop toast notifications for proactive messages.

## Architecture

```
Models (SQLModel tables)     src/chitrika/models/
Utils  (pure functions)       src/chitrika/utils/
Services                     src/chitrika/services/
Engines (business logic)     src/chitrika/engines/
Routes (FastAPI endpoints)   src/chitrika/routes/
Schemas (Pydantic DTOs)      src/chitrika/schemas/
Frontend (Vite + Electron)   src/frontend/
App entry point / lifespan   src/main.py
```

**Engine pattern** — engines own the business logic and take a SQLModel `Session` at construction. Routes are thin wrappers that create engines from `Depends(get_session)`.

### Key design

| Concern | Approach |
|---------|----------|
| Database | SQLite + WAL mode (concurrent reads during heartbeat writes) |
| Config | Bootstrap via `chitrika.json` (or env); runtime knobs in `settings` table via `/api/settings` |
| Emotion math | Pure functions in `emotion_algorithms.py` — no DB access, fast, independently testable |
| Soft deletes | Characters (`enabled=false`), messages (`is_deleted`), memories (`is_forgotten`), providers (`enabled=false`) |
| LLM abstraction | `LLMProvider` interface → `OpenAIClient` implementation (any OpenAI-compatible API); keys live in provider rows, not env |
| Prompt assembly | `PromptService` enriches personality with emotional state, relevant memories, tone hints |
| Plugins | Trusted local `.py` files with manifest; prompt hooks inject context before LLM calls; disabled-by-default security |
| Emotion NLP | ONNX transformer model scores joy/sadness/anger/fear from raw message text; runs alongside keyword heuristics |
| Relationship | `RelationshipState` tracks closeness, trust, and affection per character; decays like emotions |
| Desktop notifications | Electron polls `/api/desktop/notifications/pending`, spawns a toast worker for native OS notifications |

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET/POST | `/api/characters[/{id}]` | Character CRUD |
| PATCH/DELETE | `/api/characters/{id}` | Update / disable character |
| GET/POST | `/api/conversations[/{id}]` | Conversation CRUD |
| DELETE | `/api/conversations/{id}` | Delete conversation + messages |
| GET | `/api/chats` | Frontend alias for conversations list |
| POST | `/api/conversations/batch/delete` | Batch delete conversations |
| POST | `/api/conversations/batch/clear-messages` | Batch clear messages from conversations |
| GET | `/api/conversations/{id}/messages` | Message history (cursor pagination) |
| DELETE | `/api/conversations/{id}/messages` | Clear all messages in a conversation |
| POST | `/api/conversations/{id}/messages` | Send message → SSE stream response |
| POST | `/api/conversations/{id}/read` | Mark conversation as read |
| PATCH | `/api/messages/{id}` | Edit message |
| DELETE | `/api/messages/{id}` | Soft-delete message |
| POST | `/api/messages/{id}/recall` | Recall (undo) last bot message |
| GET | `/api/characters/{id}/emotion` | Get emotion analysis |
| POST | `/api/characters/{id}/emotion` | Apply emotion delta |
| GET | `/api/characters/{id}/relationship` | Get relationship state |
| GET/POST | `/api/characters/{id}/memories` | List / create memories |
| GET | `/api/characters/{id}/memories/search?q=` | Full-text memory search |
| PATCH | `/api/memories/{id}` | Update memory |
| DELETE | `/api/memories/{id}` | Hard-delete memory |
| GET | `/api/provider-types` | List supported provider types |
| GET/POST | `/api/providers[/{id}]` | LLM provider CRUD |
| PATCH/DELETE | `/api/providers/{id}` | Update / disable provider |
| GET | `/api/providers/{id}/models` | Fetch available models from upstream |
| GET | `/api/desktop/notifications/pending` | Poll undelivered desktop notifications |
| POST | `/api/desktop/notifications/{id}/ack` | Acknowledge notification shown |
| GET | `/api/settings` | Read app settings (DB + defaults) |
| PUT | `/api/settings` | Update app settings (partial) |
| GET | `/api/plugins` | Discover and list local plugins |
| POST | `/api/plugins/rescan` | Rescan the plugin directory |
| PATCH | `/api/plugins/{id}` | Enable or disable a plugin |
| POST | `/api/debug/actions/{action}` | Run a debug action (e.g. force proactive message) |
| GET | `/api/heartbeat/status` | Heartbeat engine status |
| POST | `/api/heartbeat/tick` | Manual tick trigger |
| POST | `/import/doubao` | Import Doubao Agent conversation history |

## Emotion system

Eight Plutchik-inspired dimensions, each clamped to `[-1.0, 1.0]`:

`joy` `sadness` `anger` `fear` `trust` `anticipation` `surprise` `disgust`

- **Decay** — values drift toward zero exponentially (`emotion_decay_rate`)
- **Deltas** — keyword heuristics adjust emotions after each message
- **NLP classification** — optional ONNX transformer model classifies joy/sadness/anger/fear from raw message text
- **Mood** — weighted dot-product against 10 mood profiles (ecstatic → disgusted)
- **Loneliness** — composite score ≥ `loneliness_threshold` → heartbeat triggers a proactive message

## Heartbeat engine

Background APScheduler thread (default: every 5 minutes). Each tick re-reads interval / decay / loneliness from the DB, then:

1. Emotion decay → 2. Memory importance decay → 3. Loneliness check → 4. Proactive message if lonely

If the heartbeat interval changes in Settings, the scheduler job is rescheduled automatically — no restart. Started in the FastAPI lifespan, stopped on shutdown. Tests monkeypatch it to a no-op.

## Plugin system

Local Python plugins live in the `plugins/` directory (configurable via `plugins_dir`). Each plugin has a `plugin.json` manifest and a `.py` entry point that implements prompt hooks — functions called during prompt assembly to inject extra context before the LLM call.

Plugins are discovered at startup and on-demand via **Settings → Plugins → Rescan**. A newly discovered plugin is always **disabled** — the user must explicitly enable it. This is a security boundary: plugins run inside the Chitrika backend process, so only install code you trust.

```json
{
  "id": "friendly-tone",
  "name": "Friendly Tone",
  "version": "1.0.0",
  "hooks": ["build_system_prompt"]
}
```

See [docs/plugin-development.md](docs/plugin-development.md) for the full API, manifest format, and an example plugin.

## ONNX emotion classifier

Beyond keyword heuristics, Chitrika can classify emotion from raw message text using a transformer model exported to ONNX. The model scores four dimensions — joy, sadness, anger, fear — directly from the user's message content, giving a second signal that complements the keyword-delta system.

- Model: `models/emotion/model.onnx` (~1 GB, git-ignored)
- Export script: `scripts/export_emotion_onnx.py`
- Runtime wrapper: `src/chitrika/utils/emotion_onnx.py`
- NLP preprocessing: `src/chitrika/utils/emotion_nlp.py`

The ONNX classifier is optional — emotion deltas from keyword heuristics work without it. When the model is present, both signals feed into the emotion engine.

## Memory system

Each character keeps three kinds of memories:

| Type | Purpose | Source |
|------|---------|--------|
| `short_term` | Raw recent messages (capped at 50) | Every user message |
| `long_term` | Durable user facts / preferences | Regex extractor, optionally LLM |
| `episodic` | Narrative summaries of past chats | LLM compression (heartbeat) |

### Semantic recall (local embedding)

Memory retrieval is **query-aware**: the current user message is embedded and matched against memory embeddings, so "我家小猫咪生病了" surfaces the memory "用户养了一只叫团子的猫" even with no shared words. Scoring is `0.7 × similarity + 0.3 × importance` over a candidate pool.

- Model: `models/embedding/` (e.g. `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, ~470 MB, git-ignored)
- Export script: `scripts/export_embedding_onnx.py`
- Runtime wrapper: `src/chitrika/utils/memory_embedding.py`

```bash
uv run huggingface-cli download \
  sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 --local-dir MEC/mmini
uv run python scripts/export_embedding_onnx.py MEC/mmini models/embedding
```

When no model is installed the system **degrades gracefully** to importance-only retrieval. Existing memories are backfilled with embeddings by the heartbeat (`MemoryEngine.backfill_embeddings`).

### LLM extraction (optional, costs tokens)

The regex extractor always runs (free): it recognizes "我叫X" / "我住在X" / "my name is X" style patterns. Turning on **Settings → App → LLM Memory Extraction** additionally asks the LLM to extract richer durable facts per message.

### Episodic summaries (optional, costs tokens)

Turning on **Settings → App → Episodic Memory** makes the heartbeat compress every full batch of 30 `short_term` memories into one first-person narrative memory (`episodic`, importance 0.75), then archives the batch. Without it, short-term chatter simply rolls off after 50 messages.

### Runtime settings

| Setting | Default | Effect |
|---------|---------|--------|
| `memory_llm_extraction` | `false` | LLM fact extraction per message |
| `memory_episodic_summary` | `false` | Heartbeat compresses short-term into narrative |

Memory rows store their embedding in a `BLOB` column (auto-added by migration); importance decays over time unless pinned or accessed, and forgotten memories are pruned after a grace period.

## Relationship tracking

Each character maintains a `RelationshipState` with three dimensions:

`closeness` `trust` `affection`

All clamped to `[-1.0, 1.0]`. Like emotions, relationship values decay toward zero over time and are nudged by conversation interactions. The `GET /api/characters/{id}/relationship` endpoint returns the current state (auto-creating a neutral baseline if needed). The **Companion Mind** panel in the frontend visualizes these alongside emotion data.

## Debug panel

The debug API lets you force companion actions for testing and development:

```
POST /api/debug/actions/{action}
```

Supported actions include triggering proactive messages, manipulating emotion state, and other diagnostic operations. The frontend **Debug Panel** (`DebugPanel.tsx`) provides a UI for these actions. Debug endpoints are meant for local development — not authenticated by default.

## Doubao Agent import

Get your Doubao Agent conversation history back under your control. Export from [agentmsg-shify](https://github.com) (the community archive tool) and import in one request:

```bash
curl -X POST http://localhost:8000/import/doubao \
  -H "Content-Type: application/json" \
  -d '{"source_path": "/path/to/doubao_export/"}'
```

Each Doubao bot becomes a Chitrika character. Every conversation (with original timestamps) is preserved. Already-imported conversations are skipped so you can re-run it safely.

## Default character

Chitrika ships with Alvia (徐悦婷 / 0624xyt) as the default character, defined in `skill_0624.txt`. She's the persona behind the Output Style in `CLAUDE.md` — direct, dramatic, fiercely loyal, with a distinct texting rhythm.

Create your own characters via the Settings UI or the `/api/characters` endpoint. Each gets an independent emotion state, memory store, and personality prompt.

## Development

```bash
# Run all tests
uv run pytest

# Single test
uv run pytest tests/test_emotion_algorithms.py
uv run pytest tests/test_api.py::test_send_message_stream

# Verbose
uv run pytest -v

# Install dev dependencies
uv pip install -e ".[dev]"
```

### Test patterns

- In-memory SQLite with `StaticPool`, transaction-per-test rollback
- `client` fixture overrides `get_session` and swaps DB engine
- `seeded_character` fixture creates unique characters per test (UUID in name)
- SSE endpoints tested via `TestClient.stream()`
- Heartbeat and LLM calls are monkeypatched in test config
- Plugin discovery tested with temporary plugin directories
- ONNX emotion classifier tested with the bundled model

## Configuration reference

### Bootstrap — `chitrika.json` (optional)

Must be known before the database is ready. Change requires a process restart.

| Key | Default | Description |
|-----|---------|-------------|
| `database_url` | `sqlite:///./chitrika.db` | SQLAlchemy DB URL |
| `cors_origins` | localhost / 127.0.0.1 dev ports | JSON array or comma-separated string |
| `plugins_dir` | `<project>/plugins` | Trusted local plugin directory |

Optional env overrides: `DATABASE_URL`, `CORS_ORIGINS`, `PLUGINS_DIR`.

See `chitrika.json.example`. No file = defaults. No separate bootstrap GUI.

### Runtime settings (DB + Settings UI)

Stored in the `settings` table, seeded on startup, exposed as `GET/PUT /api/settings` and the **App Settings** panel. Take effect on the next heartbeat tick (interval change also reschedules APScheduler).

| Key | Default | Description |
|-----|---------|-------------|
| `heartbeat_interval_minutes` | `5` | Minutes between heartbeat ticks |
| `emotion_decay_rate` | `0.15` | Emotion decay toward zero per tick |
| `loneliness_threshold` | `0.6` | Loneliness score that triggers proactive messages |

LLM provider credentials (API key, base URL, models) live under Settings → Providers.

Local plugins are managed under Settings → Plugins. New plugins are disabled by
default. See [the plugin development guide](docs/plugin-development.md) for the
manifest format, prompt hook API, security boundary, and an example.

## Project structure

```
chitrika/
├── src/
│   ├── main.py                 # FastAPI app, lifespan, router registration
│   └── chitrika/
│       ├── config.py           # Bootstrap: chitrika.json + env overrides
│       ├── database.py         # SQLModel engine, session factory
│       ├── models/             # SQLModel tables (character, message, memory, emotion, provider, settings, plugin, relationship, etc.)
│       ├── schemas/            # Pydantic request/response models (incl. settings, plugins, debug)
│       ├── engines/            # Business logic (chat, emotion, memory, heartbeat, settings, plugin, relationship, debug)
│       ├── services/           # Prompt assembly, character seeding, provider service, toast worker, emotion debug panel
│       ├── routes/             # FastAPI routes (chat, character, memory, emotion, provider, desktop, heartbeat, settings, plugin, relationship, debug)
│       ├── plugins/            # Plugin hook interface (__init__.py, api.py)
│       ├── utils/              # SSE helpers, emotion algorithms, emotion NLP, emotion ONNX, datetime helpers
│       └── llmproviders/       # LLM provider abstraction + OpenAI-compatible client
├── src/frontend/               # React + Vite + Electron frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx         # Root: sidebar + chat area layout
│   │   │   ├── components/     # ChatArea, ChatListView, SettingsView, CompanionMindView, DebugPanel, landing, UI
│   │   │   └── services/       # Typed API client with SSE streaming
│   │   └── styles/             # Tailwind v4, shadcn/ui theme tokens, globals
│   └── electron/               # Electron main process, backend lifecycle, toast worker
├── models/                     # ML models (emotion ONNX classifier, tokenizer)
│   └── emotion/
├── plugins/                    # User-installed local plugins (disabled by default)
├── examples/plugins/           # Example plugin (friendly-tone)
├── docs/                       # Documentation (plugin development guide)
├── scripts/                    # Utility scripts (ONNX export)
├── tests/                      # pytest tests (incl. plugin, relationship, emotion ONNX)
├── pyproject.toml
├── chitrika.json.example       # Bootstrap config template
└── chitrika.json               # Optional local bootstrap (git-ignored if you add it)
```
