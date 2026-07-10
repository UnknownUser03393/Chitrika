# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chitrika is an AI chat application frontend — a Telegram/Messenger-style interface for chatting with multiple AI characters backed by different LLM providers. Generated from a Figma design via Figma Make, with a dark theme and custom shadcn/ui component library.

## Commands

```bash
# Install dependencies (uses pnpm)
npm install

# Start development server (Vite on 127.0.0.1:8080)
npm run dev

# Production build
npm run build
```

There are no tests or linter configured yet.

## Architecture

### Entry & Routing

- `src/main.tsx` — React 18 entry point, renders `<App />`
- `src/app/App.tsx` — Root component managing two-panel layout: collapsible left sidebar and right chat area. Sidebar switches between `ChatListView` and `SettingsView` via local state (`sidebarView`). A "New Conversation" dialog overlay lets users pick a character to start chatting with.

### Key Components

- **`ChatListView`** (`src/app/components/ChatListView.tsx`) — Left sidebar showing searchable conversation list split into pinned and recent sections. Fetches from `/api/conversations`. Supports right-click context menu for delete. Has loading, error, and empty states.
- **`ChatArea`** (`src/app/components/ChatArea.tsx`) — Main message view with SSE-streamed AI responses. Sends user messages via POST, then reads the SSE stream (`data:` lines with JSON events: `start`, `content`, `done`, `error`) to render tokens in real-time. Handles loading, error, empty-chat, and typing-indicator states.
- **`SettingsView`** (`src/app/components/SettingsView.tsx`) — Nested settings with four sub-views (`main`, `preferences`, `provider`, `models`). Manages LLM providers (CRUD) and AI characters/models (CRUD + enable/disable toggle). Preferences are local-only state (not persisted).

### API Layer

- **`src/app/services/api.ts`** — Typed fetch wrapper targeting `/api` (proxied to backend at `localhost:8000`). Covers: conversations, messages (with SSE streaming via `streamMessage`), characters, LLM providers, emotions, and health check. Types mirror backend DTOs. Helper `characterToModel()` converts backend Characters to frontend AIModel shape.
- **`src/app/components/mockData.ts`** — Static fallback data for offline/demo mode (not wired up by default; components fetch from live API).

### UI Components

- **`src/app/components/ui/`** — ~50 shadcn/ui components built on Radix UI primitives with `class-variance-authority` variants. These are Figma Make-generated and should not be hand-edited casually — they follow shadcn/ui conventions (`cn()` utility from `utils.ts`).
- **`src/app/components/figma/ImageWithFallback.tsx`** — Image component that shows an error placeholder on load failure.

### Styling

- **Tailwind CSS v4** with the `@tailwindcss/vite` plugin (no separate PostCSS `tailwindcss`/`autoprefixer` config needed).
- **`src/styles/index.css`** — Master import that pulls in `fonts.css`, `tailwind.css`, `theme.css`, and `globals.css`.
- **`src/styles/theme.css`** — shadcn/ui design tokens (CSS custom properties for colors, radii) mapped into Tailwind via `@theme inline`. Both light and dark variants defined, though the app uses a custom dark palette.
- **`src/styles/globals.css`** — Custom `@keyframes chitrikaTyping` animation for the typing indicator.
- The app uses **hardcoded dark colors** throughout components: `#0E1621` (bg), `#17212B` (sidebar), `#1C2B3A` (input bg), `#2B5278` (active/accent), `#4FA3E3` (primary blue), `#708499` (muted text), `#182533` (assistant bubble). These override the shadcn theme tokens.

### Vite Config

- **`vite.config.ts`** — Custom `figma:asset/` plugin resolves `figma:asset/<filename>` imports to `src/assets/<filename>`. `@` alias points to `src/`. Dev server on `127.0.0.1:8080` (IPv4 to avoid WinNAT port reservation) with `/api` proxied to `http://localhost:8000`. SVG and CSV files included as raw assets.

## Package Manager

This project uses **pnpm** (indicated by `pnpm-workspace.yaml`). However, the README instructs `npm i` — either works. The `pnpm.overrides` field in `package.json` pins Vite to 6.3.5.

## Key Dependencies

- **React 18.3** (peer dependency)
- **Motion** (formerly Framer Motion) — `motion/react` for layout animations, `AnimatePresence` for enter/exit transitions
- **Radix UI** — accessible headless primitives (switch, dialog, dropdown-menu, tooltip, etc.)
- **Lucide React** — icon library
- **Recharts** — charting (used by the `chart.tsx` UI component)
- **react-hook-form** — form state management
- **Tailwind CSS v4** with `tw-animate-css` for animation utilities
