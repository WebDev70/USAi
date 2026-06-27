# USAi Chat — User Guide

Welcome to **USAi Chat**, a lightweight browser-based chat interface for talking to
USAi-compatible AI models. This guide explains everything the app can do and how to
use each feature — no coding knowledge required.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [The Interface at a Glance](#2-the-interface-at-a-glance)
3. [Having a Conversation](#3-having-a-conversation)
4. [Choosing & Configuring a Model](#4-choosing--configuring-a-model)
5. [Prompt & Generation Settings](#5-prompt--generation-settings)
6. [Advanced Features](#6-advanced-features)
7. [File & Image Uploads](#7-file--image-uploads)
8. [Managing Chats & History](#8-managing-chats--history)
9. [Appearance & Convenience](#9-appearance--convenience)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Getting Started

### Start the app
1. Open a terminal in the project folder.
2. Start the server:
   ```bash
   python3 server.py
   ```
3. Open your browser to **http://localhost:8000**

### First-time setup
The app reads its settings from a `.env` file, so in most cases your **API key and
Base URL are already configured** for you — you can start chatting right away.

If you need to enter them manually:
1. Open the **API Configuration** section in the left sidebar.
2. Enter your **API Key** and **Base URL**.

> 🔒 **Your API key is kept private.** When a key is set on the server, it is
> injected behind the scenes by the server's proxy and is **never sent to your
> browser**. You'll see a placeholder indicating a server key is in use.

---

## 2. The Interface at a Glance

| Area | What it does |
|------|--------------|
| **Left Sidebar** | New chat button, chat history, and settings panels |
| **Main Chat Area** | Where your conversation appears |
| **Composer (bottom)** | Where you type; its toolbar has 📎 attach, **Model**, **Reasoning**, and the send button |
| **Debug Logs button (top right)** | Opens a technical log panel for troubleshooting |

The sidebar settings are grouped into collapsible sections:
**Prompt & Parameters · MCP & Plugins · File Uploads**

> The **model** and **reasoning effort** selectors live in the composer toolbar at
> the bottom (next to the 📎 paperclip). Your **API key / Base URL** come from the
> server's `.env`, so those sidebar sections are hidden by default.

---

## 3. Having a Conversation

1. Type your message in the box at the bottom.
2. Send it by:
   - Clicking the **↑** (send) button, or
   - Pressing **Ctrl+Enter** (or **Enter**)
   - Use **Shift+Enter** to add a new line without sending.
3. The AI's reply appears in the chat area.

### Live streaming
By default, responses **stream in token-by-token** as the AI generates them, with a
blinking cursor — so you see the answer appear in real time.

### Stop a response
While the AI is responding, the send button turns into a red **■ Stop** button.
Click it to cancel. If you stop a streaming reply, **the partial text you already
received is kept**.

### Formatted replies (Markdown)
Assistant replies are rendered as **Markdown**, so you'll see proper headings, **bold**,
*italics*, bullet lists, links, and nicely formatted **code blocks**.

### Copy buttons
- Hover over any message to reveal a **Copy** button that copies the full text.
- Each code block has its own **Copy** button.
- A brief "Copied!" confirmation appears when it works.

### Edit & regenerate
- Hover over an **assistant** message to reveal a **↻ Regenerate** button — it
  re-runs the same prompt to get a fresh answer (the old answer and anything
  after it are replaced).
- Hover over one of **your** messages to reveal an **✎ Edit** button — it opens
  an inline editor; change the text and press **Send** (or `Enter`) to re-run the
  conversation from that point. Press **Cancel** (or `Esc`) to discard.
- Both actions discard the turns that came *after* the edited/regenerated point,
  since those replies no longer apply. They're disabled while a response is
  generating.

### Save to memory (💾 Remember)
If an Obsidian vault is configured, hovering a message also shows a **💾 Remember**
button that saves that message to your "second brain" with one click. See
[Obsidian Memory](#obsidian-memory-your-second-brain) under Advanced Features.

### Token usage
Below each reply you'll see a usage note, e.g.:
> `84 in · 51 out · 135 total tokens`

This tells you how many tokens the prompt and response used.

---

## 4. Choosing & Configuring a Model

The **model**, **model router**, and **reasoning effort** selectors are in the **composer toolbar** at
the bottom of the screen (right next to the 📎 paperclip), so you can switch models
without opening the sidebar.

### Built-in model choices
- **Google AI:** Gemini 2.0 Flash, Gemini 2.0 Pro
- **Anthropic:** Claude Haiku 3.5, Claude Sonnet 3.7, Claude Sonnet 4, Claude Opus 4
- **Meta:** Llama 3.2 11B, Llama 4 Maverick

(The full list reflects whatever your provider returns when models are loaded.)

### Model Router (Auto-select)
The **Router: Auto** dropdown automatically picks the right model tier for each
message so you don't have to switch manually:

| Router setting | Behaviour |
|----------------|-----------|
| **Router: Auto** *(default)* | Classifies your message by complexity and selects High, Medium, or Low tier automatically |
| **Router: High** | Always uses the High-tier model (Opus / powerful reasoning) regardless of message content |
| **Router: Medium** | Always uses the Medium-tier model (Sonnet / balanced) |
| **Router: Low** | Always uses the Low-tier model (Haiku / fast & cheap) |
| **Router: Off** | Ignores the router entirely — the model you picked in the Model dropdown is used as-is |

**How Auto classification works:**
- 🔴 **High** — messages longer than 800 characters, messages containing code fences or function/class definitions, or messages using keywords like *architect*, *refactor*, *debug*, *prove*, *theorem*, *optimize*, *security*, *implement*, or *design*.
- 🟡 **Medium** — everything else; also the floor tier when Tool calling is enabled.
- 🟢 **Low** — short greetings and simple look-up questions (*"hi"*, *"what is …"*, *"how many …"*) when Tool calling is off.

The chosen tier and model name appear in the message note below each assistant reply, e.g. `Model: claude-sonnet-4-5 (auto)` or `Model: claude-opus-4 (manual)`.

> **Tip:** Set the Router to **Off** when you want to use a specific model you loaded via
> the Model dropdown (e.g. a custom model id) — the Router won't override it.

### Reasoning effort
Next to the model selector, choose how hard reasoning-capable models "think" before
answering (Off / Low / Medium / High). Higher effort can improve hard problems but
uses more tokens and is slower. Models that don't support reasoning ignore this.

### Smart parameter handling
Some models reject certain parameters (for example, several reasoning models
deprecate `temperature`). USAi **detects this automatically** and omits unsupported
parameters from the request, so you won't get a `400` error. When that happens, the
matching field is greyed out and a note appears in the Debug Logs.

---

## 5. Prompt & Generation Settings

Open the **Prompt & Parameters** section.

| Setting | What it does |
|---------|--------------|
| **System prompt** | Optional instructions that set the AI's behavior/persona for the whole chat |
| **Temperature** (0–2) | Creativity dial. Lower = focused/predictable, higher = creative/varied. **Leave blank to omit** (some models reject it) |
| **Max tokens** | The maximum length of the AI's reply. **Leave blank to omit** |
| **Reasoning effort** | In the composer toolbar — how much a reasoning model "thinks" before answering |

> Leaving **Temperature** or **Max tokens** blank means the app won't send that
> parameter at all, letting the model use its own default.

---

## 6. Advanced Features

Open the **MCP & Plugins** section.

### Stream responses *(on by default)*
Shows the reply as it's generated. Automatically turned off when you use Tool
calling or Structured output (those need the complete response).

### Tool calling
When enabled, the AI can automatically use built-in tools to help answer:
- **Calculator** — safe arithmetic only
- **Search uploaded files** — keyword search across files you've uploaded
- **Context7 docs** — fetches documentation context (only available when Context7 is configured)

A live **"🔧 Using tools"** indicator shows which tools are active, and the message
note lists the tools that were used.

### Context7 integration
A secondary context provider. When enabled and configured, relevant documentation
context is merged into your prompts. Use the **Fetch Context** button to pull
context manually.

> **Note:** During Tool calling, the model can only use Context7 as a tool if the
> **Context7** box is checked. When it's unchecked, the model can still use the
> calculator and uploaded-file search tools.

### Obsidian Memory (your "second brain")
USAi can use an **Obsidian vault** as long-term memory, so it can remember facts,
preferences, and decisions across conversations.

**Setup:** add these to your `.env` and restart the server:
```bash
OBSIDIAN_VAULT_PATH=/path/to/your/Obsidian Vault
OBSIDIAN_MEMORY_SUBDIR=USAi
```
Memories are saved as tagged Markdown notes in `<vault>/USAi/memories/`. The app
**only ever reads/writes inside that folder** — your other notes are never touched.
If no vault is configured, the memory toggles are greyed out.

> **Note for developers:** This project is built using VS Code with the Continue
> extension, and Continue uses the *same* vault as its own memory. To keep the two
> separate, the **app** saves to `USAi/memories/` (this section), while **Continue's
> dev-session notes** go to `Continue Extension/memories/`. As an end user of the
> chat app, you only deal with `USAi/memories/`. (See `AGENTS.md` for the developer
> convention.)

There are **three ways** to use memory:

| Way | How it works | Requirements |
|-----|--------------|--------------|
| **Memory tools** | Tick **Obsidian Memory**. The AI decides on its own when to **save** something worth remembering or **recall** past notes, using the `save_memory` / `search_memory` tools. | Tool calling **on** + vault configured |
| **Auto-recall** | Tick **Auto-recall memories**. Before *every* message, the app searches your vault and injects the most relevant notes as context. | Vault configured (works with or without Tool calling) |
| **💾 Remember button** | Hover any message and click **💾 Remember** to save it to your vault with one click. | Vault configured |

When memories are pulled in, the message note shows a **`Memory: N note(s)`** segment
so you know it happened.

**Semantic re-ranking (optional):** When an embedding model is configured, memory
search results are automatically re-ranked by vector similarity to your query instead
of plain keyword order — so the most semantically relevant notes surface first.

To enable, add to your `.env` and restart:
```bash
EMBED_MODEL=text-embedding-3-small   # or any OpenAI-compatible embed model
EMBED_INPUT_TYPE=search_document     # optional; Cohere-style hint (ignored by OpenAI)
```
The embedding requests go through the same `BASE_URL` / `API_KEY` proxy used for
chat. If no embed model is set, memory search falls back to keyword ranking
automatically — nothing breaks.

> 💡 **Tip:** Use **Auto-recall** for hands-off continuity, **Memory tools** to let
> the AI manage memory itself, and the **💾 Remember** button to deliberately save a
> specific message. You can use any combination.

#### Obsidian-MCP Bridge (advanced — Phase 2)

For richer vault management — rename tags across all notes, move notes, list vaults —
you can optionally configure the `obsidian-mcp` Node.js bridge:

**Prerequisites:**
1. Install `obsidian-mcp` globally: `npm install -g obsidian-mcp`
2. Note the path to the script (usually `$(npm root -g)/obsidian-mcp/index.js`).

**Setup:** add to your `.env` and restart:
```bash
OBSIDIAN_MCP_PATH=/absolute/path/to/obsidian-mcp/index.js
# Only needed if 'node' is not on the server's PATH (e.g. nvm/asdf):
OBSIDIAN_NODE_PATH=/usr/local/bin/node
```

When configured, `GET /config` returns `has_mcp_bridge: true` and three additional
tools become available in the model's tool list (when the **Obsidian Memory** toggle
is on):

| Tool | Description |
|------|-------------|
| `obsidian_rename_tag` | Rename a tag across all notes |
| `obsidian_move_note` | Move or rename a note |
| `obsidian_list_vaults` | List all available Obsidian vaults |

Each bridge call spawns a short-lived Node subprocess (~200–400 ms) — acceptable for
interactive tool use. When `OBSIDIAN_MCP_PATH` is unset the app behaves exactly as
before; no bridge calls are made.



### Structured output (JSON)
Force the AI to return valid JSON.
1. Tick **Structured output (JSON)**.
2. *(Optional)* Paste a **JSON Schema** to define the exact shape of the output.
   The app validates your schema as you type and shows a status line.
3. The reply is pretty-printed, and the note shows **JSON ✓** (valid) or **JSON ✕**.

> The app is resilient: even if your API gateway ignores the JSON request, it adds a
> system instruction and can recover JSON from replies wrapped in code fences or prose.

---

## 7. File & Image Uploads

Open the **File Uploads** section and click **Upload Files / Images**.

### Images (for vision models)
- Upload images to ask the AI about them.
- Thumbnails appear above the message box; click the ✕ on a thumbnail to remove it.
- Images display inside your message bubble and persist across reloads.

### Text files (for context / RAG)
Supported types include `.txt`, `.md`, `.json`, `.csv`, `.js`, `.ts`, `.py`,
`.html`, `.css`, `.xml`, `.yaml`/`.yml`, and `.log`.

Text files are split into **chunks**, and the most relevant chunks are added to your
message automatically. Two settings control this:

| Setting | Meaning |
|---------|---------|
| **Chunk size** | Number of lines per chunk (default 200) |
| **Top chunks** | Max number of chunks added per message (default 5) |

Uploaded/processed files are cached, and a panel lists your cached files.

---

## 8. Managing Chats & History

### New chat
Click **+ New Chat** in the sidebar. Your current conversation is **archived to your
chat history**, and a fresh conversation begins.

### Chat history
- Past conversations appear in the sidebar list (most recent first).
- **Click** a session to reopen it.
- **Hover** over a session to reveal a **delete** button.

### Automatic saving
Your active conversation is saved automatically, so it's restored when you reload the
page (you'll see "Restored N messages from saved history").

### Persisted settings
Your preferences — model, system prompt, temperature, max tokens, reasoning effort,
all the toggles, JSON schema, chunk settings, and base URL — are saved in your
browser and restored automatically next time.

---

## 9. Appearance & Convenience

### Dark / Light mode
Click the **🌙 Dark Mode** button at the bottom of the sidebar to toggle themes.

### Accessibility
USAi Chat is built to be keyboard- and screen-reader-friendly:
- **Keyboard navigation:** every control (buttons, the model/reasoning menus, the
  message box, toggles) is reachable with **Tab** and shows a clear focus ring.
- **Screen readers:** icon-only buttons (send ↑, attach 📎, sidebar ☰) have spoken
  labels, the sidebar toggle announces whether the sidebar is open, and new
  assistant replies are announced as they arrive.
- **Reduced motion:** if your system is set to *Reduce Motion*, the app honors it
  and disables non-essential animation.
- **Readable contrast:** text colors meet WCAG AA contrast in both light and dark
  themes.

### Debug Logs
Click **Debug Logs** (top-right) to open a technical panel showing app activity. You can:
- Filter by **level** (All / Info / Warn / Error)
- **Search** the logs with the filter box
- **Clear** the logs

This is useful when reporting a problem.

---

## 10. Troubleshooting

### `[WARNING]` "API key rejected by upstream" at startup

When the server starts it quietly fires a one-time probe to check that your API key
is accepted by the upstream. If the key is expired, wrong, or missing, you'll see a
line like this in the terminal:

```
[WARNING] startup: API key rejected by upstream (HTTP 401) — chat will fail until a valid key is set in .env
```

**What to do:**
1. Open your `.env` file and verify `API_KEY=` is set to a valid, unexpired key.
2. Make sure `BASE_URL=` points to the correct endpoint for your provider.
3. Restart the server (`Ctrl+C` then `.venv/bin/python server.py`).

If the key is valid but the probe still warns (e.g. your upstream doesn't expose
`/api/v1/models`), the warning is a false alarm — the app will work normally. The
probe only reports `[WARNING]` for HTTP 401/403; other errors (network unreachable,
unexpected status) are reported as informational and don't block startup.

You can also check the **Debug Logs** panel for the `startup` component log entries.

### "API error: 400" when sending a message
A `400` means the API provider rejected the request. Common causes:
- **Wrong model ID** — make sure the selected model is one your provider supports
  (try **Load Models** to see valid options).
- **A parameter the model doesn't support** — e.g. some models reject `reasoning_effort`,
  `response_format` (JSON mode), or images. Try turning those off and resend.
- **Max tokens too high** for that model — lower the **Max tokens** value.
- **Empty or malformed message** — make sure there's actual text/content.

💡 Open the **Debug Logs** panel and look at the error entry for details — it often
includes the exact reason the provider rejected the request.

### `404 GET /favicon.ico`
This is **harmless** — it just means the app has no browser-tab icon. It does not
affect functionality and can be ignored.

### Models won't load
- The API Key and Base URL come from the server's `.env`. Confirm they're set
  correctly there, then restart the server.
- Check that the server is running and you opened **http://localhost:8000**.

### Obsidian Memory toggles are greyed out
- This means no vault is configured. Add `OBSIDIAN_VAULT_PATH` (and optionally
  `OBSIDIAN_MEMORY_SUBDIR`) to your `.env` and **restart the server**.
- Make sure the vault path actually exists on disk.

### The AI used Context7 even though I didn't want it
- Uncheck the **Context7** box in **MCP & Plugins**. With it unchecked, the model
  cannot call Context7 as a tool.

### The page seems stuck
- Check the terminal where `server.py` is running for messages.
- Reload the browser tab.
- Look in the **Debug Logs** panel for errors.

### How do I tell if the server is up without opening the browser?

```bash
curl http://localhost:8000/health
```

A healthy server replies immediately with JSON:

```json
{
  "status": "ok",
  "timestamp": "2026-06-22T19:00:00.123456",
  "uptime_seconds": 45.7,
  "uptime": "0:00:45",
  "version": "1.0.0",
  "features": {
    "has_api_key": true,
    "has_context7": false,
    "has_obsidian": true
  }
}
```

`/health` is also the target of the Docker `HEALTHCHECK` probe — container
orchestrators (Docker Compose health checks, Kubernetes liveness probes) use it to
decide whether the container is ready. No secrets are ever returned by this endpoint.

---

## Quick Reference — Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Enter** / **Ctrl+Enter** | Send message |
| **Shift+Enter** | New line (don't send) |

---

*Happy chatting! For technical/setup details, see `README.md`.*
