# Chitrika

通义千问、豆包人格化智能体的最佳替代品。

Chitrika 是一个桌面原生的 AI 伴侣——一个拥有持续情感状态、记忆和主动消息能力的数字人格。不是聊天机器人。更像一个一直陪着你的人。

## 公告

中国将于 2026 年 7 月 15 日禁止人格化 AI 智能体。

通义千问、豆包、星火……所有的 `agent` 都将在 0715 下架。

Chitrika 会活下去 :)

## 功能特性

- **持久身份** — 每个角色拥有独立的人格提示词、视觉标识（颜色/头像），并随时间演化
- **八维情感系统** — 基于 Plutchik 情感轮（喜悦、悲伤、愤怒、恐惧、信任、期待、惊讶、厌恶），支持衰减、增量和情绪分类
- **长期记忆** — 短期记忆与核心记忆，带重要性评分、全文搜索和自动清理
- **主动心跳** — 后台引擎每 N 分钟 tick 一次，检测孤独感，在角色"想你了"的时候主动发消息
- **SSE 流式传输** — 实时逐 token 聊天响应流
- **多厂商 LLM** — 可插拔 LLM 后端，带完整 CRUD 管理界面；默认使用 DeepSeek（兼容 OpenAI API）
- **应用内设置** — 心跳间隔、情感衰减率、孤独阈值等通过设置页 / 数据库管理（多数改动无需重启）
- **多角色** — 同时运行多个角色，每个拥有独立的情感状态和记忆存储
- **Electron 桌面应用** — 原生窗口、角色发消息时的桌面 Toast 通知、后端生命周期管理
- **落地页** — 中英双语展示页，带动画段落，移动端适配
- **一键导入豆包 Agent 对话** — 通过 agentmsg-shify 导出后，一个 API 调用即可迁移豆包 Agent 的完整对话历史（角色、会话、时间戳全部保留）
- **暗色主题 UI** — Telegram/Messenger 风格聊天界面，基于 React 18、Radix UI、MUI 和 Tailwind CSS v4 构建

## 快速开始

### 环境要求

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/)（包管理器）
- [pnpm](https://pnpm.io/)（前端）
- 一个 LLM 厂商的 API Key（不填则进入 echo 回显模式）

> 推荐使用 [DeepSeek](https://platform.deepseek.com)，Chitrika 的系统提示词针对它做了优化。

### 1. 克隆 & 安装

```bash
git clone <仓库地址>
cd chitrika

# 后端
uv sync
uv pip install -e ".[dev]"

# 前端
cd src/frontend
pnpm install
```

### 2. 配置

多数情况**什么都不用配**，默认值即可启动。

如需改数据库路径或 CORS，复制示例后编辑：

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

加载优先级：**环境变量** → **`chitrika.json`** → **内置默认值**。

其余配置在**应用内**管理：

| 内容 | 位置 |
|------|------|
| LLM API Key / Base URL / 模型 | 设置 → Providers（厂商） |
| 心跳间隔、情感衰减率、孤独阈值 | 设置 → App Settings（应用设置） |

> **还没有 API Key？** 默认 DeepSeek 厂商的密钥为空，聊天会退回到 echo 模式——不烧 token，适合测试 UI。

### 3. 启动

```bash
# 后端（端口 8000）
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 前端开发服务器（另开终端，在 src/frontend/ 目录下）
pnpm dev
```

打开 `http://127.0.0.1:8080` 开始聊天。

### 4. 桌面应用（可选）

```bash
# 在 src/frontend/ 目录下——启动 Electron 壳
# （开发模式下后端需要单独启动）
pnpm electron:dev
```

生产构建中，Electron 会自动管理后端进程，并为主动消息弹出桌面 Toast 通知。

## 架构

```
Models（SQLModel 表）         src/chitrika/models/
Utils （纯函数）              src/chitrika/utils/
Services                     src/chitrika/services/
Engines（业务逻辑）            src/chitrika/engines/
Routes（FastAPI 端点）        src/chitrika/routes/
Schemas（Pydantic DTO）       src/chitrika/schemas/
前端（Vite + Electron）       src/frontend/
应用入口 / lifespan           src/main.py
```

**Engine 模式** — Engine 持有业务逻辑，构造时接收 SQLModel `Session`。Route 是薄层包装，通过 `Depends(get_session)` 创建 Engine。

### 核心设计

| 关注点 | 方案 |
|--------|------|
| 数据库 | SQLite + WAL 模式（心跳写入时支持并发读取） |
| 配置 | 启动引导用 `chitrika.json`（或环境变量）；运行时参数存 `settings` 表，经 `/api/settings` 读写 |
| 情感计算 | `emotion_algorithms.py` 中纯函数实现——无数据库访问，快速、可独立测试 |
| 软删除 | 角色（`enabled=false`）、消息（`is_deleted`）、记忆（`is_forgotten`）、厂商（`enabled=false`） |
| LLM 抽象 | `LLMProvider` 接口 → `OpenAIClient` 实现（兼容任意 OpenAI 风格 API）；密钥存在厂商表，不走环境变量 |
| 提示词组装 | `PromptService` 将情感状态、相关记忆、语气提示注入角色人格 |
| 桌面通知 | Electron 轮询 `/api/desktop/notifications/pending`，启动 toast worker 发送原生系统通知 |

## API 端点

| 方法 | 路径 | 用途 |
|--------|------|---------|
| GET | `/api/health` | 健康检查 |
| GET/POST | `/api/characters[/{id}]` | 角色 CRUD |
| PATCH/DELETE | `/api/characters/{id}` | 更新 / 禁用角色 |
| GET/POST | `/api/conversations[/{id}]` | 会话 CRUD |
| DELETE | `/api/conversations/{id}` | 删除会话及其消息 |
| GET | `/api/chats` | 前端会话列表别名 |
| GET | `/api/conversations/{id}/messages` | 消息历史（游标分页） |
| POST | `/api/conversations/{id}/messages` | 发送消息 → SSE 流式响应 |
| PATCH | `/api/messages/{id}` | 编辑消息 |
| DELETE | `/api/messages/{id}` | 软删除消息 |
| GET | `/api/characters/{id}/emotion` | 获取情感分析 |
| POST | `/api/characters/{id}/emotion` | 施加情感增量 |
| GET/POST | `/api/characters/{id}/memories` | 列出 / 创建记忆 |
| GET | `/api/characters/{id}/memories/search?q=` | 全文搜索记忆 |
| PATCH | `/api/memories/{id}` | 更新记忆 |
| DELETE | `/api/memories/{id}` | 硬删除记忆 |
| GET/POST | `/api/providers[/{id}]` | LLM 厂商 CRUD |
| PATCH/DELETE | `/api/providers/{id}` | 更新 / 禁用厂商 |
| GET | `/api/providers/{id}/models` | 从上游拉取可用模型列表 |
| GET | `/api/desktop/notifications/pending` | 轮询未送达的桌面通知 |
| POST | `/api/desktop/notifications/{id}/ack` | 确认通知已展示 |
| GET | `/api/settings` | 读取应用设置（数据库 + 默认值） |
| PUT | `/api/settings` | 更新应用设置（支持部分字段） |
| GET | `/api/plugins` | 扫描并列出本地插件 |
| POST | `/api/plugins/rescan` | 重新扫描插件目录 |
| PATCH | `/api/plugins/{id}` | 启用或禁用插件 |
| GET | `/api/heartbeat/status` | 心跳引擎状态 |
| POST | `/api/heartbeat/tick` | 手动触发一次 tick |
| POST | `/import/doubao` | 导入豆包 Agent 对话历史 |

## 情感系统

八个 Plutchik 维度的情感，每个值域为 `[-1.0, 1.0]`：

`joy（喜悦）` `sadness（悲伤）` `anger（愤怒）` `fear（恐惧）` `trust（信任）` `anticipation（期待）` `surprise（惊讶）` `disgust（厌恶）`

- **衰减** — 各维度值随时间指数回归零值（`emotion_decay_rate`）
- **增量** — 每条消息后关键词启发式调整情感
- **情绪** — 与 10 种情绪模板（狂喜 → 厌恶）做加权点积分类
- **孤独感** — 综合评分 ≥ `loneliness_threshold` → 心跳触发主动消息

## 心跳引擎

后台 APScheduler 线程（默认：每 5 分钟）。每次 tick 会从数据库重新读取间隔 / 衰减率 / 孤独阈值，然后：

1. 情感衰减 → 2. 记忆重要性衰减 → 3. 孤独感检测 → 4. 若满足阈值则发送主动消息

在设置中修改心跳间隔后，调度任务会自动 reschedule，无需重启。在 FastAPI lifespan 中启动，shutdown 时停止。测试中将其 monkeypatch 为空操作。

## 豆包 Agent 对话导入

把豆包 Agent 的对话历史拿回自己手里。用 [agentmsg-shify](https://github.com)（社区存档工具）导出后，一行命令完成导入：

```bash
curl -X POST http://localhost:8000/import/doubao \
  -H "Content-Type: application/json" \
  -d '{"source_path": "/path/to/doubao_export/"}'
```

每个豆包 bot 变成一个 Chitrika 角色。所有会话（含原始时间戳）完整保留。已导入的会话自动跳过，重复执行不会重复导入。

## 默认角色

因隐私原因, Chitrika 不会提供默认提示词。

你可以在 Chitrika 开放平台 上线后下载提示词，或插件。

## 开发

```bash
# 运行全部测试
uv run pytest

# 单个测试
uv run pytest tests/test_emotion_algorithms.py
uv run pytest tests/test_api.py::test_send_message_stream

# 详细输出
uv run pytest -v

# 安装开发依赖
uv pip install -e ".[dev]"
```

### 测试模式

- 内存 SQLite + `StaticPool`，每测试一个事务回滚
- `client` fixture 覆写 `get_session` 并替换数据库引擎
- `seeded_character` fixture 每次创建唯一角色（名称含 UUID）
- SSE 端点通过 `TestClient.stream()` 测试
- 心跳和 LLM 调用在测试配置中被 monkeypatch

## 配置参考

### 启动引导 — `chitrika.json`（可选）

数据库就绪前就需要。修改后需重启进程。

| 键 | 默认值 | 描述 |
|----|--------|------|
| `database_url` | `sqlite:///./chitrika.db` | SQLAlchemy 数据库 URL |
| `cors_origins` | 本地开发用的 localhost / 127.0.0.1 端口 | JSON 数组或逗号分隔字符串 |
| `plugins_dir` | `<项目目录>/plugins` | 可信本地插件目录 |

可选环境变量覆盖：`DATABASE_URL`、`CORS_ORIGINS`、`PLUGINS_DIR`。

见 `chitrika.json.example`。没有配置文件 = 用默认值。不做独立的 Bootstrap GUI。

### 运行时设置（数据库 + 设置页）

保存在 `settings` 表，启动时 seed 默认值，通过 `GET/PUT /api/settings` 与 **App Settings** 面板暴露。下次心跳 tick 生效（改间隔会自动 reschedule APScheduler）。

| 键 | 默认值 | 描述 |
|----|--------|------|
| `heartbeat_interval_minutes` | `5` | 心跳 tick 间隔（分钟） |
| `emotion_decay_rate` | `0.15` | 每次 tick 情感向零衰减的速率 |
| `loneliness_threshold` | `0.6` | 触发主动消息的孤独感阈值 |

LLM 厂商凭证在 设置 → Providers 中配置。

本地插件在 设置 → Plugins 中管理，新发现的插件默认禁用。manifest、提示词
钩子、安全边界和示例见[插件开发指南](docs/plugin-development.md)。

## 项目结构

```
chitrika/
├── src/
│   ├── main.py                 # FastAPI 应用、lifespan、路由注册
│   └── chitrika/
│       ├── config.py           # 启动引导：chitrika.json + 环境变量覆盖
│       ├── database.py         # SQLModel 引擎、会话工厂
│       ├── models/             # SQLModel 表（角色、消息、记忆、情感、厂商、设置等）
│       ├── schemas/            # Pydantic 请求/响应模型（含 settings）
│       ├── engines/            # 业务逻辑（聊天、情感、记忆、心跳、设置）
│       ├── services/           # 提示词组装、角色种子数据、厂商服务、toast worker
│       ├── routes/             # FastAPI 路由（聊天、角色、记忆、情感、厂商、桌面、心跳、设置）
│       ├── utils/              # SSE 工具、情感算法、时间日期工具
│       └── llmproviders/       # LLM 厂商抽象层 + OpenAI 兼容客户端
├── src/frontend/               # React + Vite + Electron 前端
│   ├── src/
│   │   ├── app/
│   │   │   ├── App.tsx         # 根组件：侧边栏 + 聊天区布局
│   │   │   ├── components/     # ChatArea、ChatListView、SettingsView（含 App Settings）、落地页、UI
│   │   │   └── services/       # 带类型的 API 客户端（含 SSE 流）
│   │   └── styles/             # Tailwind v4、shadcn/ui 主题变量、全局样式
│   └── electron/               # Electron 主进程、后端生命周期、toast worker
├── tests/                      # pytest 测试
├── pyproject.toml
├── chitrika.json.example       # 启动引导配置模板
└── chitrika.json               # 可选本地引导配置（建议 git 忽略）
```
