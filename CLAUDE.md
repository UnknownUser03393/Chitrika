# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Chitrika is a desktop-native AI companion — a persistent digital persona with evolving emotional state, memory, and proactive messaging. It exposes a FastAPI REST API with SSE streaming for chat. The default character (Alvia / 徐悦婷) is defined in `skill_0624.txt`.

**Tech stack:** FastAPI, SQLModel (SQLite + WAL mode), APScheduler (background heartbeat), Pydantic v2, httpx (LLM client). Python >= 3.13.

## Common commands

```bash
# One-click startup (backend + frontend in separate windows)
.\start.ps1        # PowerShell
start.bat          # Command Prompt

# Or start individually:
# Run the API server (reads .env for DEEPSEEK_API_KEY, etc.)
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend dev server (from src/frontend)
pnpm dev

# Run all tests
uv run pytest

# Run a single test file or test function
uv run pytest tests/test_emotion_algorithms.py
uv run pytest tests/test_api.py::test_send_message_stream

# Run tests with verbose output
uv run pytest -v

# Install dev dependencies
uv pip install -e ".[dev]"
```

## Architecture

The codebase follows an **Engine pattern** — engines contain the business logic and accept a SQLModel `Session`, while routes are thin FastAPI wrappers that create engines from the session dependency.

### Layer map (inner to outer)

```
Models (SQLModel tables)     src/chitrika/models/
Utils  (pure functions)       src/chitrika/utils/
Services                     src/chitrika/services/
Engines (business logic)     src/chitrika/engines/
Routes (FastAPI endpoints)   src/chitrika/routes/
Schemas (Pydantic request/response)  src/chitrika/schemas/
App entry point / lifespan   src/main.py
```

### Key design rules

- **Emotion math is pure.** `src/chitrika/utils/emotion_algorithms.py` contains only mathematical functions with no database access. This makes it fast and independently testable. The `EmotionEngine` wraps these with persistence.
- **Engines own their session.** Each engine receives a `Session` at construction time and uses it for all calls within that scope. Engines are created per-request in routes (via `Depends(get_session)`).
- **SQLite uses WAL mode** for concurrent reads during heartbeat writes. SQLite stores naive UTC datetimes — `utcnow()` in `datetime_helpers.py` strips `tzinfo`.
- **Soft deletes everywhere.** Characters (`enabled=false`), messages (`is_deleted`), and memories (`is_forgotten`) use soft-delete. The `MemoryEngine.prune_forgotten()` does hard-delete after a grace period.
- **Deferred router registration** in `main.py` uses a helper function `_register_routers()` to avoid circular imports.

### Emotion system (8 Plutchik-inspired dimensions)

Each character has an `EmotionState` row with eight float dimensions (`joy`, `sadness`, `anger`, `fear`, `trust`, `anticipation`, `surprise`, `disgust`), all clamped to `[-1.0, 1.0]`. The system supports:
- **Decay** — values drift toward zero over time (exponential, `emotion_decay_rate` configurable).
- **Deltas** — keyword heuristics in `ChatEngine._post_process_emotions` adjust emotions after each message.
- **Mood classification** — weighted dot-product against mood profiles (ecstatic, happy, calm, lonely, sad, angry, anxious, surprised, disgusted, neutral).
- **Loneliness** — weighted composite used by the heartbeat engine to trigger proactive messages.

### Heartbeat engine

`HeartbeatEngine` runs on a background APScheduler thread (default: every 5 minutes). Each tick processes all enabled characters:
1. Emotion decay → 2. Memory importance decay → 3. Loneliness check → 4. Proactive message scheduling (when loneliness >= threshold, default 0.6).

The engine is started in `main.py`'s lifespan and stopped on shutdown. Tests monkeypatch `HeartbeatEngine.start` to a no-op.

### LLM provider abstraction

`src/llmproviders/LLMProvider.py` defines the abstract interface (`LLMProvider`) with `send`, `sendAsync`, `stream`, and `streamAsync`. `OpenAIClient` in `OpenAIProvider.py` implements it for any OpenAI-compatible API (used with DeepSeek by default). When no API key is configured, the chat engine returns an echo response for testing.

### Prompt assembly

`PromptService.build_system_prompt()` enriches the character's personality prompt with current emotional state, relevant memories, and tone instructions. `build_messages()` produces the full `[system, ...user/assistant pairs]` list for the LLM call.

### Test patterns

- **conftest.py** sets up in-memory SQLite with `StaticPool`, transaction-per-test rollback, and monkeypatched config (no LLM calls, no heartbeat scheduling, no character seeding).
- **`client` fixture** overrides the `get_session` dependency with the test session and swaps the database engine.
- **`seeded_character` fixture** creates a unique character + emotion state per test (uses `uuid4` in the name to avoid conflicts across tests).
- Tests use FastAPI's `TestClient` with `.stream()` for SSE endpoints.

## API endpoint summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |
| GET/POST | `/api/characters[/{id}]` | Character CRUD |
| PATCH/DELETE | `/api/characters/{id}` | Update/disable character |
| GET/POST | `/api/conversations[/{id}]` | Conversation CRUD |
| DELETE | `/api/conversations/{id}` | Delete conversation + messages |
| GET | `/api/chats` | Frontend alias for conversations list |
| GET | `/api/conversations/{id}/messages` | Message history (cursor pagination) |
| POST | `/api/conversations/{id}/messages` | Send message (SSE stream response) |
| PATCH | `/api/messages/{id}` | Edit message |
| DELETE | `/api/messages/{id}` | Soft-delete message |
| GET | `/api/characters/{id}/emotion` | Get emotion analysis |
| POST | `/api/characters/{id}/emotion` | Apply emotion delta |
| GET/POST | `/api/characters/{id}/memories` | List/create memories |
| GET | `/api/characters/{id}/memories/search?q=` | Full-text memory search |
| PATCH | `/api/memories/{id}` | Update memory |
| DELETE | `/api/memories/{id}` | Hard-delete memory |
| GET | `/api/heartbeat/status` | Heartbeat engine status |
| POST | `/api/heartbeat/tick` | Manual tick trigger |

## Configuration (.env)

All settings are loaded via `pydantic-settings` from environment / `.env`:
- `DEEPSEEK_API_KEY` — LLM API key (omit for echo mode)
- `DEEPSEEK_BASE_URL` — default `https://api.deepseek.com/v1`
- `DEEPSEEK_MODEL` — default `deepseek-chat`
- `DATABASE_URL` — default `sqlite:///./chitrika.db`
- `HEARTBEAT_INTERVAL_MINUTES` — default `5`
- `EMOTION_DECAY_RATE` — default `0.15`
- `LONELINESS_THRESHOLD` — default `0.6`
- `CORS_ORIGINS` — comma-separated, default `http://localhost:5173,http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080`
