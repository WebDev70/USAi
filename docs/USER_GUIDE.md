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
   .venv/bin/python backend/server.py
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
- **Google AI:** Gemini 2.5 Flash, Gemini 2.5 Flash Lite, Gemini 2.5 Pro, Gemini 2.0 Flash
- **Anthropic:** Claude Haiku 4.5, Claude Sonnet 4.5, Claude Sonnet 4.6, Claude Opus 4.5, Claude Opus 4.7, Claude Opus 4.8
- **OpenAI:** GPT-5.2, GPT-5.4, GPT-5.5
- **Meta:** Llama 4 Maverick
- **Cohere:** Cohere English v3

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

**How to verify reasoning actually engaged:** look for two signals in the assistant reply:
1. **💭 Thinking block** — a collapsible block above the answer showing the model's
   chain-of-thought. Only appears when the model returned reasoning content.
2. **Reasoning token count** — the per-message note beneath each reply now shows
   `… · 32 reasoning tokens` (example) when the API reports non-zero
   `reasoning_tokens`. A count of zero, or no count at all, means the model did not
   use reasoning — the setting was either unsupported or the effort level was too low
   to trigger it on that particular message.

If you set **High** and neither signal appears, the model you selected does not
support the `reasoning_effort` parameter and silently ignored it.

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

Click the **📎** button in the composer toolbar to attach files or images.

### The attachment tray

Attached files appear as **chips** in a tray directly above the message box:

- Attaching more files **adds** to the tray — earlier attachments are kept.
- Re-attaching a file with the same name **replaces** its content (no duplicate chip).
- Click the **✕** on a chip to remove just that file.
- After you send a message, the tray clears and the message shows a
  `📄 <filenames>` note recording which files were attached to that turn.

> **Note:** The attachment record shown on a restored chat is **provenance only** —
> the file's text is not re-loaded into context when you reopen an old chat.
> Re-attach the file if you want to keep asking questions about it.

### Images (for vision models)
- Upload images to ask the AI about them.
- Thumbnails appear above the message box; click the ✕ on a thumbnail to remove it.
- Images display inside your message bubble and persist across reloads.

### Text files (for context / RAG)
Supported types include `.txt`, `.md`, `.json`, `.csv`, `.js`, `.ts`, `.py`,
`.html`, `.css`, `.xml`, `.yaml`/`.yml`, `.log`, plus **`.pdf`** and **`.docx`**.

PDF and DOCX files are sent to the server, which extracts their plain text before
chunking (the chip shows the extracted `.txt` name).

#### How retrieval works

Text files are split into **chunks** at structural boundaries (Markdown headings,
paragraph breaks, and whole code blocks). *Chunk size* is an **upper bound** — most
chunks are smaller because splitting stops at the nearest boundary at or below the
limit. This is **structure-aware chunking**, so a code fence or heading never ends
up mid-chunk.

When you send a message, USAi runs a **hybrid search** over your uploaded files:

1. **Lexical pass** — BM25-style keyword overlap between your query and each chunk.
2. **Semantic pass** — embedding-vector cosine similarity, using a per-chunk
   fallback to a section-level embedding if the chunk lacks its own (e.g. very
   short chunks).
3. **Reciprocal Rank Fusion (RRF)** — the two ranked lists are fused into a single
   ranking so neither lexical nor semantic results dominate.

The **top-N chunks** from the fused ranking are selected, then **neighbor expansion**
adds the chunk immediately before and after each winner so context is never cut off
mid-thought.

Every added excerpt is **labelled** with its file name, section heading, and line
range (provenance) — you can always see exactly which part of which file contributed
to an answer.

Two settings control retrieval depth:

| Setting | Meaning |
|---------|---------|
| **Chunk size** | Upper bound on lines per chunk (default 200). Actual chunks are usually smaller — splitting stops at the nearest structural boundary. |
| **Top chunks** | Max number of chunks selected before neighbour-expansion is applied (default 5) |

Uploaded/processed files are cached, and a panel in the sidebar lists your cached
files. **Restore** on a cached file **replaces** the current attachment set (it is not
additive, unlike the 📎 button) — the tray always shows exactly what is attached.

---

## 8. Managing Chats & History

### New chat
Click **+ New Chat** in the sidebar. Your current conversation is **archived to your
chat history**, and a fresh conversation begins.

### Projects
**Projects** are named workspaces that group related chats together, making it easy to
organise work by topic, client, or context.

#### Create a project
1. Click the **＋** button next to the **Projects** heading in the sidebar, or use
   the **+ New Project** control.
2. Enter a **project name** in the modal.
3. Optionally, enter **Project instructions** — free-text that is automatically
   prepended to every system prompt in this project (see [Project instructions](#project-instructions) below).
4. Choose a **Memory mode** (this can be changed later from project settings):
   - **Default** — project chats share the global Obsidian memory pool (notes
     written here are visible everywhere, and global notes are visible here).
   - **Project-only** — project chats use a private memory scope, isolated from
     other chats.
5. Click **Create**.

#### Open a project
Click any project name in the **Projects** section of the sidebar. A **project
detail view** opens in the main pane showing:
- The project name and a snippet of its instructions.
- A list of all saved chats in this project (click any row to restore that chat).
- A **"＋ New chat"** button to start a fresh conversation in this project.
- A **"⚙ Settings"** button to edit the project name, instructions, memory mode,
  and shared files.

Project chats also appear **grouped under their project row** in the sidebar as
a collapsible sub-list, so you can jump directly to any chat without opening the
detail view first.

#### Rename or pin a project
Hover over the project in the sidebar and click **⋯** to open the context menu:
- **Rename** — change the project name.
- **Pin / Unpin** — pinned projects appear at the top of the sidebar in a **Pinned**
  section.

#### Move a chat into a project
You can reassign any existing chat to a different project (or remove it from
its current project) at any time:

1. Hover over the chat row in the **Chats** section of the sidebar.
2. Click the **⋯** button that appears on the right side.
3. Select **📂 Move to project…**.
4. A picker shows all your projects, plus a **"No project"** option to detach
   the chat from any project.
5. Click the desired target — the sidebar refreshes instantly.

> **Note:** Existing Obsidian memory notes for a chat stay in their original
> vault folder and are **not** moved when you reassign the chat. Only the
> chat's `projectId` metadata is updated.

#### Delete a project
In the ⋯ context menu, click **Delete**. A confirmation prompt appears.
> **What happens to chats and memories?**
> - Chats that belonged to the project are **kept** and moved to the **Chats** section
>   (they are never deleted).
> - Obsidian memory notes created inside the project are **preserved** in the vault;
>   they are never destroyed.

#### Memory Modes

Every project has a **Memory mode** that is chosen at creation and **can be changed later** from the project settings (⋯ → **Settings** on the project row). It governs how Obsidian memory searches and saves are scoped for all chats in that project.

| Mode | Search behaviour | Save behaviour |
|------|-----------------|----------------|
| **Default** | Draws results from **both** the global memory folder and this project's folder, merged by relevance score. | New notes are written to the **project folder** (not the global folder). |
| **Project-only** | Reads **only** from this project's folder — global notes are excluded. Other chats (outside the project) also never see this project's notes. | New notes are written to the **project folder** only. |

**Project folder path** (inside your vault):
```
<vault>/<memory subdir>/projects/<projectId>/memories/
```

**Global notes** are still accessible from any non-project chat, and from chats in projects set to **Default** mode.

> 💡 Use **Default** when you want the project's AI context to benefit from (and contribute to) your general knowledge base.
> Use **Project-only** when the project contains sensitive or domain-specific content you want kept entirely separate.

> **Note:** A memory-mode change takes effect **immediately**. Memory scope is
> resolved fresh on every search and save (the server reads the current mode
> per-request), so the next memory search or save uses the new mode — you do not
> need to reopen the project or start a new chat.

#### Project instructions

Each project can have a set of **custom instructions** that are automatically prepended to every system prompt for chats in that project — you don't need to re-type them per chat.

**Setting instructions:**
- When **creating** a project, enter text in the optional **Instructions** textarea in the modal (up to 8 192 characters / ~2 000 words).
- After creation, open the project settings (⋯ → **Settings** on the project row) and update the Instructions field, then click **Save**.

**How the system prompt is composed:**

```
Layer 1: project.instructions   ← prepended automatically (if non-empty)
Layer 2: per-chat system prompt ← from the "System prompt" input in Prompt & Parameters
─────────────────────────────────────────────────────────────────
Effective system prompt = [layer1, layer2].filter(non-empty).join('\n\n')
```

If only one layer is non-empty, it's used as-is with no extra blank lines.

**Build paths that respect project instructions:**
- First message in a chat
- **↻ Regenerate** (re-uses the composed prompt automatically)
- **✎ Edit & resend** (same)
- Session restore (the app re-fetches the project record when restoring a session)

> **Note:** If you update a project's instructions mid-chat, the new instructions take
> effect the next time you **open** the project or **start a new chat** inside it.
> The current session will keep the old instructions until then.

#### Project files

Projects support **shared knowledge files** that are available to every chat in the project. Once uploaded, these files are chunked and embedded, and their content is automatically included in RAG searches alongside any files uploaded in the current chat session.

**Uploading a file:**
1. Open the project settings (⋯ → **Settings** on the project row in the sidebar).
2. In the **Project files** section (only visible when editing an existing project), click **+ Upload file**.
3. Select one or more files (`.txt`, `.md`, `.pdf`, `.docx`, `.json`, `.csv`).
4. The file is chunked and saved to the project cache on the server. A status message confirms when the upload is done.

**Removing a file:**
- Click the **✕** button next to the filename in the project files list.
- The file and its chunks are removed from the project cache. The deletion takes effect for all chats in the project immediately.

**How project files are searched:**
- At query time, chunks from your project's shared files are merged with any files you uploaded in the current chat session and ranked together by relevance.
- The context note in the message shows the combined count, e.g. `Files: 5 chunk(s)`.
- Project files are loaded when you open a project or restore a session in a project. They persist across chat sessions for the project lifetime.

**Limits & notes:**
- Each file upload is subject to the same 50 MB request size limit as per-chat file uploads.
- Project files are deleted automatically when the project is deleted.
- Files uploaded per-chat remain separate from project files and are never added to the project cache.

#### Sidebar sections

The sidebar is organised into three collapsible sections:

| Section | Contents |
|---------|----------|
| **Pinned** | Pinned projects and pinned chats |
| **Projects** | All your projects (shows up to 5; click "Show more" to see the rest). Each project row lists its own chats in a sub-list beneath it. |
| **Chats** | Ungrouped conversations (no project, or whose project was deleted) |

Chats started outside a project, and chats whose project has been deleted, always
appear in the **Chats** section. Chats that belong to a project appear in that
project's sub-list under **Projects**, not in **Chats**.

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
3. Restart the server (`Ctrl+C` then `.venv/bin/python backend/server.py`).

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
- Check the terminal where `backend/server.py` is running for messages.
- Reload the browser tab.
- Look in the **Debug Logs** panel for errors.

### How do I preserve server logs across restarts?

By default, USAi Chat keeps logs in memory only — they are lost when the server
stops. To write **persistent, timestamped JSONL log files** to a `logs/` directory
in the project, enable log file persistence in your `.env`:

```
PERSIST_LOGS=true
LOG_FILE_MAX=20    # optional — max number of session log files to keep (default 20)
```

Restart the server. From then on, each run creates a file like:

```
logs/2026-06-27-143000-server.jsonl
```

Each line is a JSON object:

```json
{"timestamp": "2026-06-27T14:30:00.123", "level": "info", "component": "memory", "message": "search \"foo\" → 2 hit(s)", "details": {}}
```

Older session files are automatically deleted when the count exceeds `LOG_FILE_MAX`.
Log files are git-ignored — they won't appear in `git status`.

### Analyzing log files with RAIL (developer use)

When `PERSIST_LOGS=true`, the RAIL pipeline automatically analyzes your session log
files during every `/review` and `/govern` pass. You can also run the analyzer
manually from the project root:

```bash
./scripts/analyze-logs.sh          # analyze logs/ (default)
./scripts/analyze-logs.sh logs/    # same, explicit path
```

**What the analyzer reports:**

- Total entries and a breakdown by level (`info`, `warn`, `error`) and component.
- The top-3 most frequent error messages (sensitive patterns like `sk-`, `Bearer `
  are automatically replaced with `[REDACTED]`).
- Any `fetch` entries with `latency_ms > 2000ms` (latency outliers).

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0`  | No error entries found (or no log files exist) |
| `1`  | One or more `"level": "error"` entries found |

In the RAIL `/review` workflow, exit 1 is **advisory only** — it never converts a
PASS review to FAIL. In `/govern` (sprint-close audit), the same error component
appearing in two consecutive reports is escalated to **BLOCKING**.

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

## 11. Raw API Response Capture (developer feature)

This is an **opt-in developer/operator tool** — it is off by default and does
not affect the chat experience.

When enabled, USAi saves the complete JSON envelope returned by the upstream API
for every non-streaming chat request to `.raw_responses/` on the server. Each
file contains the full response body (`id`, `model`, `usage`, `finish_reason`,
`choices`, etc.) plus the HTTP status, endpoint path, model name, and timestamp.

### How to enable

Add to your `.env` file:

```
CAPTURE_RAW_RESPONSES=true
RAW_RESPONSES_MAX=200   # (optional) max files to keep; oldest deleted at cap
```

Restart the server. Files appear under `.raw_responses/` in your project root.

### What is NOT captured

- Your API key / `Authorization` header (never stored — only the response body).
- Streaming responses (SSE capture is a separate future feature).

### Browsing captures

You can inspect files directly:

```bash
ls .raw_responses/
cat .raw_responses/<filename>.json | python3 -m json.tool
```

Or via the server API:

```bash
# List all captures (metadata only)
curl http://localhost:8000/raw-responses

# Read a specific record
curl "http://localhost:8000/raw-responses?id=<filename>"

# Delete all captures
curl -X DELETE http://localhost:8000/raw-responses
```

---

*Happy chatting! For technical/setup details, see `README.md`.*
