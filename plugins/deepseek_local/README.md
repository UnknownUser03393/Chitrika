# DeepSeek Web (Local) plugin

Chitrika provider plugin that talks to **chat.deepseek.com** using a reverse-engineered browser session client (cookies + localStorage tokens + PoW). It does **not** use the official `platform.deepseek.com` API key.

## Layout

```
plugins/deepseek_local/
  plugin.json          # manifest
  plugin.py            # entrypoint (ProviderSpec + factory)
  provider.py          # LLMProvider implementation
  login.py             # Playwright login helper
  data/
    auth_state.json    # browser storage state (gitignored)
    session_store.json # chat session continuity (gitignored)
  ds_web/              # vendored web client package
    client.py
    pow.py
    hash_v1.py
    sse.py
    session_store.py
    deepseek_hash_v1.exe   # optional fast PoW solver (Windows)
```

## Setup

1. Enable the plugin (auto-enabled on Chitrika startup if discovered).
2. Login once and save auth state:

```bash
uv pip install playwright
playwright install chromium
uv run python plugins/deepseek_local/login.py
```

3. In Settings → Providers, create/select **DeepSeek Web (Local)**.
   - Leave `auth_state.json path` empty to use `data/auth_state.json`.
   - No API key field.

4. Assign the provider to a character and chat.

## Models

| Public id            | Web model_type |
|----------------------|----------------|
| `deepseek-chat`      | `default`      |
| `default` / `fast`   | `default`      |
| `deepseek-reasoner`  | `expert`       |
| `expert` / `reasoner`| `expert`       |
| `vision`             | `vision`       |

## Auth expired

If chat returns HTTP 401/403, re-run:

```bash
uv run python plugins/deepseek_local/login.py
```

## Source

Logic ported from the local reverse-engineering project (`openai_server` / `deepseek_client` / PoW stack) into a self-contained Chitrika plugin — no separate local OpenAI proxy process required.
