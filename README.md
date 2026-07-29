# Chitrika

The best replacement for Qwen and Doubao's personified agent.

Chitrika is a desktop-native AI companion — a persistent digital persona with evolving emotional state, memory, and proactive messaging. Not a chatbot. More like someone who's always there.

## I18n

中文版README: README_zh.md

## Announcement

China will ban Personified AI Agent at 2026/07/15.

Qwen, Doubao, XingHuo, ..., all of them will ban their `agent` at 0715.

Chitrika will be living :)

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
# Backend (port 8000)
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Frontend dev server (separate terminal, in src/frontend/)
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
| GET | `/api/conversations/{id}/messages` | Message history (cursor pagination) |
| POST | `/api/conversations/{id}/messages` | Send message → SSE stream response |
| PATCH | `/api/messages/{id}` | Edit message |
| DELETE | `/api/messages/{id}` | Soft-delete message |
| GET | `/api/characters/{id}/emotion` | Get emotion analysis |
| POST | `/api/characters/{id}/emotion` | Apply emotion delta |
| GET/POST | `/api/characters/{id}/memories` | List / create memories |
| GET | `/api/characters/{id}/memories/search?q=` | Full-text memory search |
| PATCH | `/api/memories/{id}` | Update memory |
| DELETE | `/api/memories/{id}` | Hard-delete memory |
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
| GET | `/api/heartbeat/status` | Heartbeat engine status |
| POST | `/api/heartbeat/tick` | Manual tick trigger |
| POST | `/import/doubao` | Import Doubao Agent conversation history |

## Emotion system

Eight Plutchik-inspired dimensions, each clamped to `[-1.0, 1.0]`:

`joy` `sadness` `anger` `fear` `trust` `anticipation` `surprise` `disgust`

- **Decay** — values drift toward zero exponentially (`emotion_decay_rate`)
- **Deltas** — keyword heuristics adjust emotions after each message
- **Mood** — weighted dot-product against 10 mood profiles (ecstatic → disgusted)
- **Loneliness** — composite score ≥ `loneliness_threshold` → heartbeat triggers a proactive message

## Heartbeat engine

Background APScheduler thread (default: every 5 minutes). Each tick re-reads interval / decay / loneliness from the DB, then:

1. Emotion decay → 2. Memory importance decay → 3. Loneliness check → 4. Proactive message if lonely

If the heartbeat interval changes in Settings, the scheduler job is rescheduled automatically — no restart. Started in the FastAPI lifespan, stopped on shutdown. Tests monkeypatch it to a no-op.

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
│       ├── models/             # SQLModel tables (character, message, memory, emotion, provider, settings, etc.)
│       ├── schemas/            # Pydantic request/response models (incl. settings)
│       ├── engines/            # Business logic (chat, emotion, memory, heartbeat, settings)
│       ├── services/           # Prompt assembly, character seeding, provider service, toast worker
│       ├── routes/             # FastAPI routes (chat, character, memory, emotion, provider, desktop, heartbeat, settings)
│       ├── utils/              # SSE helpers, emotion algorithms, datetime helpers
│       └── llmproviders/       # LLM provider abstraction + OpenAI-compatible client
├── src/frontend/               # React + Vite + Electron frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx         # Root: sidebar + chat area layout
│   │   │   ├── components/     # ChatArea, ChatListView, SettingsView (App Settings), landing, UI
│   │   │   └── services/       # Typed API client with SSE streaming
│   │   └── styles/             # Tailwind v4, shadcn/ui theme tokens, globals
│   └── electron/               # Electron main process, backend lifecycle, toast worker
├── tests/                      # pytest tests
├── pyproject.toml
├── chitrika.json.example       # Bootstrap config template
└── chitrika.json               # Optional local bootstrap (git-ignored if you add it)
```
