# Chitrika

The best replacement for Qwen and Doubao's personified agent.

Chitrika is a dcesktop-native AI companion — a persistent digital persona with evolving emotional state, memory, and proactive messaging. Not a chatbot. More like someone who's always there.

## Announcement

China will ban Personified AI Agent at 2026/07/15.

Qwen, Doubao, XingHuo, ..., all of them will ban their `agent` at 0715.

Chitrika will be livng :)

## Features

- **Persistent identity** — each character has a personality prompt, visual identity (color/avatar), and evolves over time
- **8-dimension emotion system** — Plutchik-inspired (joy, sadness, anger, fear, trust, anticipation, surprise, disgust) with decay, deltas, and mood classification
- **Long-term memory** — short-term and core memories with importance scoring, full-text search, and automatic pruning
- **Proactive heartbeat** — background engine that ticks every N minutes, checks loneliness, and sends unprompted messages when the character "misses you"
- **SSE streaming** — real-time token-by-token chat response streaming
- **Multi-provider LLM** — pluggable LLM backend (OpenAI-compatible API), defaults to DeepSeek
- **Multi-character** — run multiple personas, each with independent emotion and memory state

## Quick start

### Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) (package manager)
- [pnpm](https://pnpm.io/) (frontend)
- An API key from [DeepSeek](https://platform.deepseek.com/) (or skip for echo mode)

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

Create a `.env` file in the project root:

```env
DEEPSEEK_API_KEY=sk-your-key-here
# Everything below is optional — these are the defaults:
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DATABASE_URL=sqlite:///./chitrika.db
HEARTBEAT_INTERVAL_MINUTES=5
EMOTION_DECAY_RATE=0.15
LONELINESS_THRESHOLD=0.6
```

> **No API key?** The chat engine falls back to echo mode — great for testing the UI without burning tokens.

### 3. Run

```bash
# Backend (port 8000)
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal, in src/frontend/)
pnpm dev
```

Open `http://127.0.0.1:8080` and start talking.

## Architecture

```
Models (SQLModel tables)     src/chitrika/models/
Utils  (pure functions)       src/chitrika/utils/
Services                     src/chitrika/services/
Engines (business logic)     src/chitrika/engines/
Routes (FastAPI endpoints)   src/chitrika/routes/
Schemas (Pydantic DTOs)      src/chitrika/schemas/
Frontend (Vite app)          src/frontend/
App entry point / lifespan   src/main.py
```

**Engine pattern** — engines own the business logic and take a SQLModel `Session` at construction. Routes are thin wrappers that create engines from `Depends(get_session)`.

### Key design

| Concern | Approach |
|---------|----------|
| Database | SQLite + WAL mode (concurrent reads during heartbeat writes) |
| Emotion math | Pure functions in `emotion_algorithms.py` — no DB access, fast, independently testable |
| Soft deletes | Characters (`enabled=false`), messages (`is_deleted`), memories (`is_forgotten`) |
| LLM abstraction | `LLMProvider` interface → `OpenAIClient` implementation (any OpenAI-compatible API) |
| Prompt assembly | `PromptService` enriches personality with emotional state, relevant memories, tone hints |

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
| GET | `/api/heartbeat/status` | Heartbeat engine status |
| POST | `/api/heartbeat/tick` | Manual tick trigger |

## Emotion system

Eight Plutchik-inspired dimensions, each clamped to `[-1.0, 1.0]`:

`joy` `sadness` `anger` `fear` `trust` `anticipation` `surprise` `disgust`

- **Decay** — values drift toward zero exponentially (`emotion_decay_rate`)
- **Deltas** — keyword heuristics adjust emotions after each message
- **Mood** — weighted dot-product against 10 mood profiles (ecstatic → disgusted)
- **Loneliness** — composite score ≥ `loneliness_threshold` → heartbeat triggers a proactive message

## Heartbeat engine

Background APScheduler thread (default: every 5 minutes). Each tick:

1. Emotion decay → 2. Memory importance decay → 3. Loneliness check → 4. Proactive message if lonely

Started in the FastAPI lifespan, stopped on shutdown. Tests monkeypatch it to a no-op.

## Default character

What the fuck are you look for?

Write your own.

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

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | `""` | LLM API key (empty = echo mode) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | API base URL |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model name |
| `DATABASE_URL` | `sqlite:///./chitrika.db` | SQLite path |
| `HEARTBEAT_INTERVAL_MINUTES` | `5` | Heartbeat tick interval |
| `EMOTION_DECAY_RATE` | `0.15` | Emotion decay per tick |
| `LONELINESS_THRESHOLD` | `0.6` | Proactive message trigger |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080` | Allowed CORS origins |

## Project structure

```
chitrika/
├── src/
│   ├── main.py              # FastAPI app, lifespan, router registration
│   └── chitrika/
│       ├── config.py         # pydantic-settings configuration
│       ├── database.py       # SQLModel engine, session factory
│       ├── models/           # SQLModel tables
│       ├── schemas/          # Pydantic request/response models
│       ├── engines/          # Business logic (chat, emotion, memory, heartbeat)
│       ├── services/         # Prompt assembly, character seeding
│       ├── routes/           # FastAPI route handlers
│       ├── utils/            # SSE helpers, emotion algorithms, datetime
│       └── llmproviders/     # LLM provider abstraction + OpenAI impl
├── tests/                    # pytest tests
├── pyproject.toml
└── .env                      # Your configuration (git-ignored)
```
