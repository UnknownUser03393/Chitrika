# Chitrika local plugins

Chitrika loads trusted Python plugins from the `plugins` directory. Plugins
are discovered at startup and when the user selects **Settings → Plugins →
Rescan**. A newly discovered plugin is always disabled; the user must enable it
explicitly.

> Plugins execute Python code inside the Chitrika backend process. Install and
> enable only code you trust. This local plugin API is not a security sandbox.

## Directory layout

Each plugin lives in its own directory:

```text
plugins/
└── my-tone/
    ├── plugin.json
    └── plugin.py
```

`plugin.json`:

```json
{
  "manifest_version": 1,
  "id": "example.my-tone",
  "name": "My tone",
  "version": "1.0.0",
  "description": "Adds a response style instruction",
  "author": "Your name",
  "entrypoint": "plugin.py:plugin"
}
```

IDs must start with a lowercase letter and contain only lowercase letters,
digits, `.`, `_`, or `-`. The entrypoint is a Python file relative to the
plugin directory followed by the exported object name.

## Prompt hook

The first supported hook is `on_system_prompt(context)`. It receives an
immutable `PromptContext` and returns the replacement system prompt. Returning
`None` leaves the prompt unchanged.

```python
from src.chitrika.plugins import PromptContext


class MyTonePlugin:
    def on_system_prompt(self, context: PromptContext) -> str:
        return context.system_prompt + "\nUse warm, concise language."


plugin = MyTonePlugin()
```

Enabled hooks run in plugin-ID order. A failing hook is isolated: Chitrika
continues the chat, records the error in the Plugins settings screen, and runs
the remaining plugins.

## Configuration and API

The default plugin directory is `<project>/plugins`. Override it with
`plugins_dir` in `chitrika.json` or the `PLUGINS_DIR` environment variable.

- `GET /api/plugins` — rescan and list plugins
- `POST /api/plugins/rescan` — rescan and return discovery errors
- `PATCH /api/plugins/{id}` with `{"enabled": true}` — enable or disable
