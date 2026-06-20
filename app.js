const themeToggle = document.getElementById('themeToggle');
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

function safeTrim(s) {
  return (s || '').toString().trim();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Minimal, dependency-free Markdown renderer ───────────────────────────────
// Security: ALL text is HTML-escaped first, then a limited set of Markdown
// constructs are converted to safe HTML. No raw HTML from the model is allowed
// through, so this is XSS-safe. Supports: fenced/inline code, headings, bold,
// italic, links, unordered/ordered lists, blockquotes, hr, and paragraphs.
function renderMarkdown(src) {
  if (src == null) return '';
  const text = String(src).replace(/\r\n/g, '\n');

  // 1. Extract fenced code blocks first so their contents aren't formatted.
  const codeBlocks = [];
  let work = text.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_m, lang, code) => {
    const idx = codeBlocks.length;
    const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : '';
    codeBlocks.push(`<pre class="md-pre"><code${langClass}>${escapeHtml(code.replace(/\n$/, ''))}</code></pre>`);
    return `\u0000CODE${idx}\u0000`;
  });

  // 2. Escape everything else.
  work = escapeHtml(work);

  // 3. Inline code (after escaping, backticks survive).
  const inlineCodes = [];
  work = work.replace(/`([^`\n]+)`/g, (_m, code) => {
    const idx = inlineCodes.length;
    inlineCodes.push(`<code class="md-code">${code}</code>`);
    return `\u0000INLINE${idx}\u0000`;
  });

  // 4. Process block-level constructs line by line.
  const lines = work.split('\n');
  const html = [];
  let listType = null; // 'ul' | 'ol' | null

  const closeList = () => {
    if (listType) { html.push(`</${listType}>`); listType = null; }
  };

  for (let raw of lines) {
    const line = raw;

    // Horizontal rule
    if (/^\s*([-*_])\1\1+\s*$/.test(line)) {
      closeList();
      html.push('<hr class="md-hr">');
      continue;
    }
    // Headings (# .. ######)
    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level} class="md-h">${inline(heading[2])}</h${level}>`);
      continue;
    }
    // Blockquote (note: '>' has already been escaped to '&gt;' at this point)
    const quote = line.match(/^\s*&gt;\s?(.*)$/);
    if (quote) {
      closeList();
      html.push(`<blockquote class="md-quote">${inline(quote[1])}</blockquote>`);
      continue;
    }
    // Unordered list item
    const uli = line.match(/^\s*[-*+]\s+(.*)$/);
    if (uli) {
      if (listType !== 'ul') { closeList(); html.push('<ul class="md-list">'); listType = 'ul'; }
      html.push(`<li>${inline(uli[1])}</li>`);
      continue;
    }
    // Ordered list item
    const oli = line.match(/^\s*\d+\.\s+(.*)$/);
    if (oli) {
      if (listType !== 'ol') { closeList(); html.push('<ol class="md-list">'); listType = 'ol'; }
      html.push(`<li>${inline(oli[1])}</li>`);
      continue;
    }
    // Blank line → paragraph break
    if (/^\s*$/.test(line)) {
      closeList();
      html.push('');
      continue;
    }
    // Code-block placeholder line (leave as-is)
    if (/^\u0000CODE\d+\u0000$/.test(line.trim())) {
      closeList();
      html.push(line.trim());
      continue;
    }
    // Default: paragraph line
    closeList();
    html.push(`<p class="md-p">${inline(line)}</p>`);
  }
  closeList();

  let out = html.join('\n');

  // 5. Inline formatting helper (bold, italic, links). Applied above via inline().
  function inline(s) {
    return s
      // Links [text](url) — only http(s)/mailto to avoid javascript: URLs
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+)\)/g,
        (_m, label, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`)
      // Bold **text** or __text__
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/__([^_]+)__/g, '<strong>$1</strong>')
      // Italic *text* or _text_
      .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
      .replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>');
  }

  // 6. Restore inline code and code blocks.
  out = out.replace(/\u0000INLINE(\d+)\u0000/g, (_m, i) => inlineCodes[+i]);
  out = out.replace(/\u0000CODE(\d+)\u0000/g, (_m, i) => codeBlocks[+i]);

  return out;
}

function setTheme(isDark) {
  document.body.classList.toggle('dark-mode', isDark);
  themeToggle.textContent = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  logger.info('theme', 'Theme changed', { mode: isDark ? 'dark' : 'light' });
}

const appConfig = {
  base_url: '',
  default_model: '',
  default_system_prompt: '',
  context7_base_url: '',
  context7_path: '',
  context7_method: '',
  // Booleans returned by /config; secrets themselves are never sent to the client.
  has_api_key: false,
  has_context7: false,
  has_obsidian: false,
  };

function getSelectedModel() {
  const modelSelect = document.getElementById('modelSelect');
  const modelCustomInput = document.getElementById('modelCustom');
  return modelSelect.value === 'custom' ? safeTrim(modelCustomInput.value) : modelSelect.value;
  }

// ─── Per-model parameter capabilities ────────────────────────────────────────
// Some models reject certain OpenAI-style parameters (e.g. reasoning models
// often deprecate `temperature`). Rather than maintaining an exact allow-list of
// every model name, we match against case-insensitive substring patterns. Each
// entry lists the parameters that model should NOT receive; matching params are
// silently omitted from the request payload so the user doesn't get a 400.
const MODEL_PARAM_EXCLUSIONS = [
  // Anthropic Claude Opus 4.x reasoning models deprecate `temperature`.
  { pattern: 'opus', exclude: ['temperature'] },
  { pattern: 'claude_opus', exclude: ['temperature'] },
  { pattern: 'claude-opus', exclude: ['temperature'] },
  // OpenAI o-series / GPT-5 reasoning models reject `temperature` and use
  // `max_completion_tokens` instead of `max_tokens`.
  { pattern: 'o1', exclude: ['temperature'] },
  { pattern: 'o3', exclude: ['temperature'] },
  { pattern: 'o4-mini', exclude: ['temperature'] },
  { pattern: 'gpt-5', exclude: ['temperature'] },
];

// Return the set of parameter names that should be omitted for a given model id.
function getExcludedParams(modelId) {
  const id = (modelId || '').toLowerCase();
  const excluded = new Set();
  for (const rule of MODEL_PARAM_EXCLUSIONS) {
    if (id.includes(rule.pattern)) {
      rule.exclude.forEach((p) => excluded.add(p));
    }
  }
  return excluded;
}

// Reflect the current model's parameter support in the sidebar UI: disabled,
// dimmed fields with an explanatory tooltip when a param is unsupported.
function updateParamFieldStates() {
  const excluded = getExcludedParams(getSelectedModel());
  const apply = (inputId, paramName, label) => {
    const el = document.getElementById(inputId);
    if (!el) return;
    const isExcluded = excluded.has(paramName);
    el.disabled = isExcluded;
    el.style.opacity = isExcluded ? '0.5' : '';
    el.title = isExcluded
      ? `${label} is not supported by the selected model and will be omitted.`
      : '';
  };
  apply('temperature', 'temperature', 'Temperature');
  apply('maxTokens', 'max_tokens', 'Max tokens');
  apply('reasoningEffort', 'reasoning_effort', 'Reasoning effort');

  const composerReasoning = document.getElementById('composerReasoning');
  if (composerReasoning) {
    const isExcluded = excluded.has('reasoning_effort');
    composerReasoning.disabled = isExcluded;
    composerReasoning.style.opacity = isExcluded ? '0.5' : '';
  }
}

// ─── Composer mirror selects ─────────────────────────────────────────────────
// The composer toolbar has compact Model and Reasoning selects that mirror the
// canonical selects in the sidebar. These helpers keep the two in sync without
// duplicating any of the underlying logic/state.

// Rebuild the composer model dropdown from the sidebar's <select> options.
function syncComposerModelOptions() {
  const source = document.getElementById('modelSelect');
  const mirror = document.getElementById('composerModel');
  if (!source || !mirror) return;
  mirror.innerHTML = source.innerHTML;
  mirror.value = source.value;
}

// Reflect the current sidebar select values onto the composer selects.
function syncComposerFromSidebar() {
  const modelSel = document.getElementById('modelSelect');
  const composerModel = document.getElementById('composerModel');
  if (modelSel && composerModel) composerModel.value = modelSel.value;
  const reasoning = document.getElementById('reasoningEffort');
  const composerReasoning = document.getElementById('composerReasoning');
  if (reasoning && composerReasoning) composerReasoning.value = reasoning.value;
}

function applyConfig() {
  const baseUrlInput = document.getElementById('baseUrlInput');
  const systemPromptInput = document.getElementById('systemPrompt');
  const apiKeyInput = document.getElementById('apiKeyInput');

  if (appConfig.base_url) baseUrlInput.value = appConfig.base_url;
  if (appConfig.default_system_prompt) systemPromptInput.value = appConfig.default_system_prompt;

  // The API key is held server-side and injected by the proxy; the client never
  // receives it. Show a placeholder so the user knows a key is configured.
  if (appConfig.has_api_key) {
    apiKeyInput.placeholder = 'Using server-configured key (leave blank)';
  }

  // Disable the Obsidian Memory toggle if no vault is configured on the server.
  const memoryToggle = document.getElementById('memoryToggle');
  const memoryRow = document.getElementById('memoryToggleRow');
  const autoRecallToggle = document.getElementById('memoryAutoRecallToggle');
  const autoRecallRow = document.getElementById('memoryAutoRecallRow');
  if (memoryToggle) {
    if (!appConfig.has_obsidian) {
      memoryToggle.checked = false;
      memoryToggle.disabled = true;
      memoryEnabled = false;
      if (autoRecallToggle) { autoRecallToggle.checked = false; autoRecallToggle.disabled = true; }
      memoryAutoRecall = false;
      if (memoryRow) {
        memoryRow.title = 'Set OBSIDIAN_VAULT_PATH in .env to enable long-term memory.';
        memoryRow.style.opacity = '0.5';
      }
      if (autoRecallRow) autoRecallRow.style.opacity = '0.5';
    } else {
      memoryToggle.disabled = false;
      if (autoRecallToggle) autoRecallToggle.disabled = false;
      if (memoryRow) {
        memoryRow.title = 'Let the model save to and recall from your Obsidian vault.';
        memoryRow.style.opacity = '';
      }
      if (autoRecallRow) autoRecallRow.style.opacity = '';
    }
  }
}

async function fetchContext7(query) {
  if (!appConfig.has_context7) {
    logger.warn('context7', 'Context7 config missing');
    return null;
  }

  const params = new URLSearchParams({ query: query || '' });
  try {
    logger.info('context7', 'Fetching context', { queryLength: query?.length || 0 });
    const resp = await fetch('/context7?' + params.toString());
    if (!resp.ok) {
      logger.warn('context7', `Fetch failed with status ${resp.status}`);
      return null;
    }

    const json = await resp.json();
    if (!json || typeof json.data === 'undefined') {
      logger.warn('context7', 'No data in response');
      return null;
    }
    logger.info('context7', 'Successfully fetched context', { dataLength: typeof json.data === 'string' ? json.data.length : JSON.stringify(json.data).length });
    return typeof json.data === 'string' ? json.data : JSON.stringify(json.data, null, 2);
  } catch (err) {
    logger.error('context7', 'Error fetching context', { error: err?.message });
    return null;
  }
}

let lastFetchedContext = null;
let context7Enabled = false;
let streamEnabled = true;
let toolsEnabled = false;
let memoryEnabled = false;
let memoryAutoRecall = false;
let currentSessionId = null;
// Tracks the in-flight request so the user can cancel it via the Stop button.
let activeAbortController = null;

// ─── UI settings persistence ─────────────────────────────────────────────────
// Save/restore user-facing controls to localStorage so they survive reloads.
const SETTINGS_KEY = 'usai.settings.v1';

function saveSettings() {
  try {
    const settings = {
      model: document.getElementById('modelSelect')?.value,
      modelCustom: document.getElementById('modelCustom')?.value,
      systemPrompt: document.getElementById('systemPrompt')?.value,
      temperature: document.getElementById('temperature')?.value,
      maxTokens: document.getElementById('maxTokens')?.value,
      reasoningEffort: document.getElementById('reasoningEffort')?.value,
      stream: document.getElementById('streamToggle')?.checked,
      tools: document.getElementById('toolsToggle')?.checked,
      jsonMode: document.getElementById('jsonModeToggle')?.checked,
      jsonSchema: document.getElementById('jsonSchema')?.value,
      context7: document.getElementById('context7Toggle')?.checked,
      memory: document.getElementById('memoryToggle')?.checked,
      memoryAutoRecall: document.getElementById('memoryAutoRecallToggle')?.checked,
      chunkSize: document.getElementById('chunkSize')?.value,
      topChunks: document.getElementById('topChunks')?.value,
      baseUrl: document.getElementById('baseUrlInput')?.value,
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (err) {
    logger.warn('settings', 'Could not save settings', { error: err?.message });
  }
}

// Apply saved settings to the DOM and sync the related state variables.
// Called after loadConfig so server defaults are applied first, then overridden
// by the user's saved preferences.
function restoreSettings() {
  let settings;
  try {
    settings = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null');
  } catch (_) {
    settings = null;
  }
  if (!settings) return;

  const setVal = (id, val) => {
    if (val === undefined || val === null) return;
    const el = document.getElementById(id);
    if (el) el.value = val;
  };
  const setChecked = (id, val) => {
    if (val === undefined || val === null) return;
    const el = document.getElementById(id);
    if (el) el.checked = !!val;
  };

  // Text/number/select inputs
  setVal('systemPrompt', settings.systemPrompt);
  setVal('temperature', settings.temperature);
  setVal('maxTokens', settings.maxTokens);
  setVal('reasoningEffort', settings.reasoningEffort);
  setVal('jsonSchema', settings.jsonSchema);
  setVal('chunkSize', settings.chunkSize);
  setVal('topChunks', settings.topChunks);
  if (settings.baseUrl) setVal('baseUrlInput', settings.baseUrl);

  // Model select (and custom box visibility)
  if (settings.model) {
    const sel = document.getElementById('modelSelect');
    if (sel && Array.from(sel.options).some(o => o.value === settings.model)) {
      sel.value = settings.model;
    } else if (sel && settings.modelCustom) {
      sel.value = 'custom';
    }
    setVal('modelCustom', settings.modelCustom);
    const custom = document.getElementById('modelCustom');
    if (custom) custom.style.display = (sel && sel.value === 'custom') ? 'block' : 'none';
  }

  // Toggles — set checkbox then sync state + dependent UI.
  setChecked('streamToggle', settings.stream);
  setChecked('toolsToggle', settings.tools);
  setChecked('jsonModeToggle', settings.jsonMode);
    setChecked('context7Toggle', settings.context7);
  setChecked('memoryToggle', settings.memory);
  setChecked('memoryAutoRecallToggle', settings.memoryAutoRecall);
  // Sync module state variables from the restored checkboxes.
  streamEnabled = document.getElementById('streamToggle')?.checked ?? streamEnabled;
  toolsEnabled = document.getElementById('toolsToggle')?.checked ?? toolsEnabled;
  context7Enabled = document.getElementById('context7Toggle')?.checked ?? context7Enabled;
  memoryEnabled = document.getElementById('memoryToggle')?.checked ?? memoryEnabled;
  memoryAutoRecall = document.getElementById('memoryAutoRecallToggle')?.checked ?? memoryAutoRecall;
  if (!Number.isNaN(parseInt(settings.chunkSize, 10))) chunkLineSize = parseInt(settings.chunkSize, 10);
  if (!Number.isNaN(parseInt(settings.topChunks, 10))) topChunksPerQuery = parseInt(settings.topChunks, 10);

  // Dependent UI: JSON schema box visibility, stream toggle disabling, Context7 button.
  const jsonOn = !!document.getElementById('jsonModeToggle')?.checked;
  const schemaBox = document.getElementById('jsonSchema');
  if (schemaBox) schemaBox.style.display = jsonOn ? 'block' : 'none';
  const streamToggle = document.getElementById('streamToggle');
  if (streamToggle) streamToggle.disabled = toolsEnabled || jsonOn;
  const fetchBtn = document.getElementById('fetchContextBtn');
  if (fetchBtn) {
    fetchBtn.disabled = !context7Enabled;
    fetchBtn.style.opacity = context7Enabled ? '' : '0.4';
  }

  logger.info('settings', 'Restored saved UI settings');
}
const conversationHistory = []; // API payload turns {role, content}
const chatDisplayHistory = []; // Persisted display turns {role, content, note, timestamp}

// Maximum number of model<->tool round-trips before we force a final answer.
const MAX_TOOL_ROUNDS = 5;

// ─── Tool registry ───────────────────────────────────────────────────────────
// Each tool has an OpenAI-format `definition` (sent to the model) and a `run`
// function (executed locally when the model requests it). `run` receives the
// parsed arguments object and must return a string (the tool result).
const TOOL_REGISTRY = {
  fetch_context7: {
    definition: {
      type: 'function',
      function: {
        name: 'fetch_context7',
        description: 'Fetch up-to-date library/framework documentation and code examples from Context7. Use when the user asks about a specific software library, API, or framework and you need authoritative reference material.',
        parameters: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'The documentation topic or question to look up, e.g. "React useEffect cleanup" or "Express JWT auth".',
            },
          },
          required: ['query'],
        },
      },
    },
    async run(args) {
      const query = safeTrim(args?.query);
      if (!query) return 'Error: no query provided.';
      const ctx = await fetchContext7(query);
      return ctx || 'No documentation was returned for that query.';
    },
  },

  search_uploaded_files: {
    definition: {
      type: 'function',
      function: {
        name: 'search_uploaded_files',
        description: 'Search the files the user has uploaded in this session and return the most relevant excerpts. Use when the user asks about the content of their uploaded documents.',
        parameters: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'What to look for within the uploaded files.',
            },
            top_k: {
              type: 'integer',
              description: 'How many excerpts to return (default 5).',
            },
          },
          required: ['query'],
        },
      },
    },
    async run(args) {
      const query = safeTrim(args?.query);
      if (!query) return 'Error: no query provided.';
      if (!fileChunks.length) return 'No files have been uploaded in this session.';
      const topK = Number.isInteger(args?.top_k) && args.top_k > 0 ? args.top_k : topChunksPerQuery;
      const chunks = getRelevantChunks(query, topK);
      if (!chunks.length) return 'No relevant excerpts found in the uploaded files.';
      return chunks
        .map((c, i) => `[Excerpt ${i + 1} from ${c.fileName} (relevance ${(c.score * 100).toFixed(0)}%)]\n${c.text}`)
        .join('\n\n---\n\n');
    },
  },

  calculator: {
    definition: {
      type: 'function',
      function: {
        name: 'calculator',
        description: 'Evaluate a basic arithmetic expression and return the numeric result. Supports + - * / ( ) and decimals.',
        parameters: {
          type: 'object',
          properties: {
            expression: {
              type: 'string',
              description: 'The arithmetic expression to evaluate, e.g. "(3 + 4) * 12.5".',
            },
          },
          required: ['expression'],
        },
      },
    },
    async run(args) {
      const expr = safeTrim(args?.expression);
      if (!expr) return 'Error: no expression provided.';
      // Only allow safe arithmetic characters to avoid arbitrary code execution.
      if (!/^[0-9+\-*/().\s]+$/.test(expr)) {
        return 'Error: expression contains unsupported characters. Only numbers and + - * / ( ) are allowed.';
      }
      try {
        // eslint-disable-next-line no-new-func
        const result = Function(`"use strict"; return (${expr});`)();
        if (typeof result !== 'number' || !Number.isFinite(result)) {
          return 'Error: expression did not evaluate to a finite number.';
        }
        return String(result);
      } catch (err) {
        return 'Error evaluating expression: ' + (err?.message || 'invalid expression');
      }
    },
  },

  search_memory: {
    definition: {
      type: 'function',
      function: {
        name: 'search_memory',
        description: 'Search the user\'s long-term memory (their Obsidian "second brain" vault) for previously saved notes, facts, preferences, or context. Use this when the user refers to something they told you before, or when past context would help answer.',
        parameters: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Keywords or a short phrase describing what to recall.',
            },
          },
          required: ['query'],
        },
      },
    },
    async run(args) {
      const query = safeTrim(args?.query);
      if (!query) return 'Error: no query provided.';
      try {
        const resp = await fetch(`/memory/search?q=${encodeURIComponent(query)}&k=5`);
        const data = await resp.json();
        if (!resp.ok) return `Error searching memory: ${data?.error || resp.status}`;
        const results = data?.results || [];
        if (!results.length) return 'No relevant memories were found.';
        logger.info('memory', `search_memory "${query}" → ${results.length} hit(s)`);
        return results
          .map((r, i) => `Memory ${i + 1} (${r.path}):\n${r.snippet}`)
          .join('\n\n---\n\n');
      } catch (err) {
        return 'Error searching memory: ' + (err?.message || 'request failed');
      }
    },
  },

  save_memory: {
    definition: {
      type: 'function',
      function: {
        name: 'save_memory',
        description: 'Save an important fact, preference, decision, or piece of context to the user\'s long-term memory (their Obsidian vault) so it can be recalled in future conversations. Use this when the user shares something worth remembering long-term, or asks you to remember something.',
        parameters: {
          type: 'object',
          properties: {
            title: {
              type: 'string',
              description: 'A short, descriptive title for this memory.',
            },
            content: {
              type: 'string',
              description: 'The full content of the memory to store, in Markdown.',
            },
            tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Optional tags to categorize this memory.',
            },
          },
          required: ['title', 'content'],
        },
      },
    },
    async run(args) {
      const title = safeTrim(args?.title);
      const content = safeTrim(args?.content);
      if (!content) return 'Error: no content provided to save.';
      try {
        const resp = await fetch('/memory/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, content, tags: args?.tags || [] }),
        });
        const data = await resp.json();
        if (!resp.ok) return `Error saving memory: ${data?.error || resp.status}`;
        logger.info('memory', `save_memory → ${data.path}`);
        return `Saved memory "${data.title || title}" to your vault (${data.path}).`;
      } catch (err) {
        return 'Error saving memory: ' + (err?.message || 'request failed');
      }
    },
  },
};

// Build the `tools` array for the API request based on availability.
function getEnabledTools() {
  const tools = [];
  for (const [name, tool] of Object.entries(TOOL_REGISTRY)) {
    // Only advertise Context7 if it's configured on the server AND the user
    // has explicitly enabled the Context7 toggle. Without this second check,
    // the model could call fetch_context7 even when Context7 is unchecked.
    if (name === 'fetch_context7' && (!appConfig.has_context7 || !context7Enabled)) continue;
    // Only advertise Obsidian memory tools when a vault is configured AND the
    // user has enabled the Obsidian Memory toggle.
    if ((name === 'search_memory' || name === 'save_memory')
        && (!appConfig.has_obsidian || !memoryEnabled)) continue;
    tools.push(tool.definition);
  }
  return tools;
}

// Execute a single tool call and return its string result.
async function executeToolCall(toolCall) {
  const name = toolCall?.function?.name;
  const rawArgs = toolCall?.function?.arguments || '{}';
  let args = {};
  try {
    args = JSON.parse(rawArgs);
  } catch (_) {
    return `Error: could not parse arguments for ${name}.`;
  }
  const tool = TOOL_REGISTRY[name];
  if (!tool) return `Error: unknown tool "${name}".`;
  try {
    logger.info('tools', `Executing tool: ${name}`, { args });
    const result = await tool.run(args);
    logger.info('tools', `Tool ${name} completed`, { resultLength: result?.length || 0 });
    return result;
  } catch (err) {
    logger.error('tools', `Tool ${name} threw`, { error: err?.message });
    return `Error running ${name}: ${err?.message || 'unknown error'}`;
  }
}

// Logger class for comprehensive debugging
class Logger {
  constructor() {
    this.localLogs = [];
    this.maxLocalLogs = 500;
  }

  async log(level, component, message, details = {}) {
    const timestamp = new Date().toISOString();
    const logEntry = { timestamp, level, component, message, details };
    
    // Store locally
    this.localLogs.push(logEntry);
    if (this.localLogs.length > this.maxLocalLogs) {
      this.localLogs.shift();
    }
    
    // Log to console with color
    const colors = { info: '#0ea5e9', warn: '#f59e0b', error: '#ef4444' };
    console.log(`%c[${level.toUpperCase()}] ${component}%c: ${message}`, 
      `color: ${colors[level] || '#666'}; font-weight: bold;`, 
      'color: inherit;', 
      details);
    
    // Send to server
    try {
      await fetch('/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level, component, message, details })
      });
    } catch (err) {
      console.error('Failed to send log to server:', err);
    }
    
    // Update UI if debug panel exists
    this.updateDebugPanel();
  }

  info(component, message, details) { return this.log('info', component, message, details); }
  warn(component, message, details) { return this.log('warn', component, message, details); }
  error(component, message, details) { return this.log('error', component, message, details); }

  updateDebugPanel() {
    const debugLogs = document.getElementById('debugLogs');
    if (!debugLogs) return;
    
    const filtered = this.getFilteredLogs();
    debugLogs.innerHTML = filtered.map(log => `
      <div class="log-entry log-${escapeHtml(log.level)}">
        <span class="log-time">${escapeHtml(new Date(log.timestamp).toLocaleTimeString())}</span>
        <span class="log-level">${escapeHtml(log.level.toUpperCase())}</span>
        <span class="log-component">${escapeHtml(log.component)}</span>
        <span class="log-message">${escapeHtml(log.message)}</span>
        ${Object.keys(log.details).length > 0 ? `<span class="log-details">${escapeHtml(JSON.stringify(log.details))}</span>` : ''}
      </div>
    `).join('');
    
    // Auto-scroll to bottom
    debugLogs.scrollTop = debugLogs.scrollHeight;
  }

  getFilteredLogs() {
    const filterInput = document.getElementById('debugFilter');
    const levelSelect = document.getElementById('debugLevel');
    
    if (!filterInput && !levelSelect) return this.localLogs;
    
    const filter = (filterInput?.value || '').toLowerCase();
    const level = levelSelect?.value || 'all';
    
    return this.localLogs.filter(log => {
      const matchLevel = level === 'all' || log.level === level;
      const matchFilter = !filter || 
        log.component.toLowerCase().includes(filter) ||
        log.message.toLowerCase().includes(filter);
      return matchLevel && matchFilter;
    });
  }

  async getLogs() {
    try {
      const resp = await fetch('/logs');
      return resp.ok ? await resp.json() : [];
    } catch (err) {
      console.error('Failed to fetch logs:', err);
      return [];
    }
  }

  async clear() {
    this.localLogs = [];
    try {
      await fetch('/logs/clear', { method: 'POST' });
    } catch (err) {
      console.error('Failed to clear logs:', err);
    }
    this.updateDebugPanel();
  }
}

const logger = new Logger();

// Embeddings-based file storage
const fileChunks = []; // { fileName, chunkId, text, embedding }
const uploadedFiles = [];

// Attached images for vision-capable models { name, dataUrl }
const pendingImages = [];

// Settings for chunking
let chunkLineSize = 200;
let topChunksPerQuery = 5;

function showUploadedFilesDisplay() {
  const el = document.getElementById('uploadedFilesDisplay');
  if (!uploadedFiles.length) {
    el.innerHTML = '';
    return;
  }
  const fileList = uploadedFiles.map(f => `<strong>${escapeHtml(f)}</strong>`).join(', ');
  const chunkCount = fileChunks.length;
  el.innerHTML = `Files: ${fileList} (${chunkCount} chunks)
    <button id="clearUploadedFilesBtn" style="margin-left:0.5rem;padding:0.2rem 0.5rem;cursor:pointer;">Clear</button>
    <button id="saveChunkCacheBtn" style="margin-left:0.3rem;padding:0.2rem 0.5rem;cursor:pointer;" title="Save to server cache for next session">Save to Cache</button>`;

  document.getElementById('clearUploadedFilesBtn')?.addEventListener('click', clearUploadedFiles);
  document.getElementById('saveChunkCacheBtn')?.addEventListener('click', saveChunkCache);
}

function clearUploadedFiles() {
  fileChunks.length = 0;
  uploadedFiles.length = 0;
  pendingImages.length = 0;
  showUploadedFilesDisplay();
  showPendingImages();
}

// Read a File as a base64 data URL (used for vision image input).
function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

// Render thumbnails of images attached to the next message.
function showPendingImages() {
  const el = document.getElementById('pendingImages');
  if (!el) return;
  if (!pendingImages.length) {
    el.innerHTML = '';
    return;
  }
  el.innerHTML = pendingImages
    .map((img, i) => `
      <span class="pending-image" title="${escapeHtml(img.name)}">
        <img src="${img.dataUrl}" alt="${escapeHtml(img.name)}" />
        <button class="pending-image-remove" data-index="${i}" title="Remove">✕</button>
      </span>`)
    .join('');
  el.querySelectorAll('.pending-image-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      pendingImages.splice(parseInt(btn.dataset.index, 10), 1);
      showPendingImages();
    });
  });
}

async function saveChunkCache() {
  if (!uploadedFiles.length) return;
  for (const filename of uploadedFiles) {
    const chunks = fileChunks.filter(c => c.fileName === filename);
    try {
      const resp = await fetch('/chunk-cache', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, chunks }),
      });
      if (resp.ok) {
        logger.info('cache', `Saved ${chunks.length} chunks for "${filename}" to server cache`);
      } else {
        logger.warn('cache', `Failed to save cache for "${filename}"`, { status: resp.status });
      }
    } catch (err) {
      logger.error('cache', `Error saving cache for "${filename}"`, { error: err?.message });
    }
  }
  document.getElementById('responseLog').textContent = `Cached ${uploadedFiles.length} file(s) to server.`;
  await showCachedFilesPanel();
}

async function deleteChunkCache(filename) {
  try {
    await fetch('/chunk-cache?file=' + encodeURIComponent(filename), { method: 'DELETE' });
    logger.info('cache', `Deleted cache for "${filename}"`);
  } catch (err) {
    logger.warn('cache', `Error deleting cache for "${filename}"`, { error: err?.message });
  }
  await showCachedFilesPanel();
}

async function restoreFromCache(filename) {
  try {
    const resp = await fetch('/chunk-cache?file=' + encodeURIComponent(filename));
    if (!resp.ok) {
      logger.warn('cache', `Cache not found for "${filename}"`);
      return;
    }
    const data = await resp.json();
    const chunks = data.chunks || [];
    fileChunks.length = 0;
    uploadedFiles.length = 0;
    for (const c of chunks) {
      fileChunks.push(c);
    }
    if (!uploadedFiles.includes(filename)) uploadedFiles.push(filename);
    showUploadedFilesDisplay();
    document.getElementById('responseLog').textContent = `Restored ${chunks.length} chunks from cache: "${filename}"`;
    logger.info('cache', `Restored "${filename}" from cache`, { chunkCount: chunks.length });
  } catch (err) {
    logger.error('cache', `Error restoring cache for "${filename}"`, { error: err?.message });
  }
  await showCachedFilesPanel();
}

async function archiveCurrentSession() {
  if (!chatDisplayHistory.length) return;
  const firstUserTurn = chatDisplayHistory.find(t => t.role === 'user');
  const raw = firstUserTurn ? firstUserTurn.content : 'Untitled chat';
  const title = raw.slice(0, 50).trim() + (raw.length > 50 ? '\u2026' : '');
  const id = currentSessionId || `session_${Date.now()}`;
  try {
    await fetch('/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id,
        title,
        turns: chatDisplayHistory.slice(-200),
        createdAt: chatDisplayHistory[0]?.timestamp || new Date().toISOString(),
      }),
    });
    currentSessionId = id;
    await showSessionsList();
  } catch (err) {
    logger.warn('history', 'Could not archive session', { error: err?.message });
  }
}

async function showSessionsList() {
  const el = document.getElementById('chatSessionsList');
  if (!el) return;
  try {
    const resp = await fetch('/sessions');
    const sessions = resp.ok ? await resp.json() : [];
    if (!sessions.length) {
      el.innerHTML = '<p class="sessions-empty">No saved chats yet</p>';
      return;
    }
    el.innerHTML = sessions.map(s => {
      const isActive = s.id === currentSessionId;
      return `<div class="session-item${isActive ? ' active' : ''}" data-id="${escapeHtml(s.id)}" title="${escapeHtml(s.title)}">
        <span class="session-title">${escapeHtml(s.title)}</span>
        <span class="session-meta">${s.messageCount} msg</span>
        <button class="session-delete" data-id="${escapeHtml(s.id)}" title="Delete">✕</button>
      </div>`;
    }).join('');
    el.querySelectorAll('.session-item').forEach(item => {
      item.addEventListener('click', e => {
        if (e.target.classList.contains('session-delete')) return;
        restoreSession(item.dataset.id);
      });
    });
    el.querySelectorAll('.session-delete').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        await fetch(`/sessions?id=${encodeURIComponent(btn.dataset.id)}`, { method: 'DELETE' });
        if (btn.dataset.id === currentSessionId) currentSessionId = null;
        showSessionsList();
      });
    });
  } catch (err) {
    logger.warn('history', 'Could not load sessions list', { error: err?.message });
  }
}

async function restoreSession(id) {
  try {
    const resp = await fetch(`/sessions?id=${encodeURIComponent(id)}`);
    if (!resp.ok) return;
    const data = await resp.json();
    const turns = data.turns || [];
    if (!turns.length) {
      document.querySelector('.main-content').classList.remove('in-conversation');
      return;
    }
    document.querySelector('.main-content').classList.add('in-conversation');

    // Archive current unsaved work first
    if (chatDisplayHistory.length && currentSessionId !== id) {
      await archiveCurrentSession();
    }

    const conversation = document.getElementById('conversation');
    conversation.innerHTML = '';
    conversationHistory.length = 0;
    chatDisplayHistory.length = 0;

    for (const turn of turns) {
      const { group } = appendMessage(conversation, turn.content, turn.role, turn.note || '', turn.images || []);
      addMessageActions(group, turn.role, chatDisplayHistory.length);
      // Rebuild API content as a multimodal array when the turn had images
      let apiContent = turn.content;
      if (turn.role === 'user' && turn.images && turn.images.length) {
        apiContent = [
          { type: 'text', text: turn.content },
          ...turn.images.map(url => ({ type: 'image_url', image_url: { url } })),
        ];
      }
      conversationHistory.push({ role: turn.role, content: apiContent });
      chatDisplayHistory.push(turn);
    }
    currentSessionId = id;
    conversation.scrollTop = conversation.scrollHeight;

    // Update active highlight
    document.querySelectorAll('.session-item').forEach(el => {
      el.classList.toggle('active', el.dataset.id === id);
    });
    logger.info('history', `Restored session with ${turns.length} messages`);
  } catch (err) {
    logger.warn('history', 'Could not restore session', { error: err?.message });
  }
}

async function saveChatHistory() {
  // Cap at 200 display turns (~100 exchanges) to keep the file manageable
  const MAX_TURNS = 200;
  const turns = chatDisplayHistory.slice(-MAX_TURNS);
  try {
    await fetch('/chat-history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ turns }),
    });
  } catch (err) {
    logger.warn('history', 'Could not save chat history', { error: err?.message });
  }
}

async function loadChatHistory() {
  try {
    const resp = await fetch('/chat-history');
    if (!resp.ok) return;
    const data = await resp.json();
    const turns = data.turns || [];
    if (!turns.length) {
      document.querySelector('.main-content').classList.remove('in-conversation');
      return;
    }
    document.querySelector('.main-content').classList.add('in-conversation');

    const conversation = document.getElementById('conversation');
    conversationHistory.length = 0;
    chatDisplayHistory.length = 0;

    for (const turn of turns) {
      const { group } = appendMessage(conversation, turn.content, turn.role, turn.note || '', turn.images || []);
      addMessageActions(group, turn.role, chatDisplayHistory.length);
      let apiContent = turn.content;
      if (turn.role === 'user' && turn.images && turn.images.length) {
        apiContent = [
          { type: 'text', text: turn.content },
          ...turn.images.map(url => ({ type: 'image_url', image_url: { url } })),
        ];
      }
      conversationHistory.push({ role: turn.role, content: apiContent });
      chatDisplayHistory.push(turn);
    }
    conversation.scrollTop = conversation.scrollHeight;
    logger.info('history', `Restored ${turns.length} messages from saved history`);
  } catch (err) {
    logger.warn('history', 'Could not load chat history', { error: err?.message });
  }
}

async function showCachedFilesPanel() {
  const el = document.getElementById('cachedFilesPanel');
  if (!el) return;
  try {
    const resp = await fetch('/chunk-cache');
    const entries = resp.ok ? await resp.json() : [];
    if (!entries.length) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = '<strong style="font-size:0.8rem;color:var(--color-text-secondary);">Cached files:</strong>' + 
      entries.map(e => `
      <div class="cached-file-item">
        <button class="cached-file-name restore-cache-btn" data-file="${escapeHtml(e.filename)}" title="Restore ${escapeHtml(e.filename)} (${e.chunkCount} chunks)">
          ${escapeHtml(e.filename)} (${e.chunkCount})
        </button>
        <button class="cached-file-delete-btn delete-cache-btn" data-file="${escapeHtml(e.filename)}" title="Remove from cache">✕</button>
      </div>`).join('');
    el.querySelectorAll('.restore-cache-btn').forEach(btn => {
      btn.addEventListener('click', () => restoreFromCache(btn.dataset.file));
    });
    el.querySelectorAll('.delete-cache-btn').forEach(btn => {
      btn.addEventListener('click', () => deleteChunkCache(btn.dataset.file));
    });
  } catch (_) {
    el.innerHTML = '';
  }
}

function scoreChunkByKeywords(chunkText, queryText) {
  // Simple keyword-based scoring as fallback to embeddings
  const queryWords = queryText.toLowerCase().split(/\s+/).filter(w => w.length > 3);
  const chunkLower = chunkText.toLowerCase();
  let score = 0;
  queryWords.forEach(word => {
    const count = (chunkLower.match(new RegExp(word, 'g')) || []).length;
    score += count;
  });
  return score / (queryWords.length || 1);
}

function chunkText(text, lineSize = 200) {
  const lines = text.split('\n');
  const chunks = [];
  for (let i = 0; i < lines.length; i += lineSize) {
    chunks.push(lines.slice(i, i + lineSize).join('\n'));
  }
  return chunks.filter(c => c.trim().length > 0);
}

async function handleFileUpload(event) {
  const files = event.target.files;
  if (!files || files.length === 0) return;

  fileChunks.length = 0;
  uploadedFiles.length = 0;
  document.getElementById('responseLog').textContent = 'Processing files...';

  // Separate images (sent inline to vision models) from text files (chunked for RAG)
  const imageFiles = [];
  const textFiles = [];
  for (const file of files) {
    if (file.type.startsWith('image/')) imageFiles.push(file);
    else textFiles.push(file);
  }

  logger.info('upload', `Starting upload of ${files.length} file(s)`, { images: imageFiles.length, textFiles: textFiles.length });

  // 1. Encode images as base64 data URLs for vision input
  for (const file of imageFiles) {
    try {
      const dataUrl = await readFileAsDataURL(file);
      pendingImages.push({ name: file.name, dataUrl });
      logger.info('upload', `Attached image: ${file.name}`, { size: file.size, type: file.type });
    } catch (err) {
      logger.error('upload', `Image read error for ${file.name}`, { error: err?.message });
    }
  }
  showPendingImages();

  // 2. Chunk text files for keyword retrieval
  let totalChunks = 0;
  for (let file of textFiles) {
    try {
      const text = await file.text();
      const chunks = chunkText(text, chunkLineSize);
      
      logger.info('upload', `Processed file: ${file.name}`, { chunks: chunks.length, size: text.length });
      
      for (let i = 0; i < chunks.length; i++) {
        fileChunks.push({
          fileName: file.name,
          chunkId: i,
          text: chunks[i],
          embedding: null, // Embeddings are disabled
        });
        totalChunks++;
      }
      uploadedFiles.push(file.name);
    } catch (err) {
      logger.error('upload', `File processing error for ${file.name}`, { error: err?.message });
      document.getElementById('responseLog').textContent = `Error processing ${file.name}: ${err.message}`;
    }
  }

  showUploadedFilesDisplay();
  const method = 'keyword matching';
  const summary = [];
  if (totalChunks) summary.push(`${totalChunks} chunks from ${uploadedFiles.length} file(s) (using ${method})`);
  if (pendingImages.length) summary.push(`${pendingImages.length} image(s) attached`);
  document.getElementById('responseLog').textContent = summary.length ? `Loaded ${summary.join(' · ')}` : 'No supported files found';
  logger.info('upload', `Upload complete`, { totalChunks, fileCount: uploadedFiles.length, images: pendingImages.length, method });

  // Auto-save text chunks to server cache after upload
  if (totalChunks) await saveChunkCache();

  // Reset the input so the same file can be re-selected later
  event.target.value = '';
}

function getRelevantChunks(query, topK = 5) {
  if (!fileChunks.length) return [];

  // Fallback to keyword matching
  const scored = fileChunks.map(chunk => ({
    ...chunk,
    score: scoreChunkByKeywords(chunk.text, query),
  }));
  
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK).map(item => ({
    fileName: item.fileName,
    text: item.text,
    score: item.score,
  }));
}

function showContextPreview(text) {
  const el = document.getElementById('contextPreview');
  if (!el) return;
  if (!text) {
    el.style.display = 'none';
    el.textContent = '';
  } else {
    el.style.display = 'block';
    el.textContent = text;
  }
}

function applyDefaultModel() {
  // If the user has a saved model preference, don't override it with the
  // server default — restoreSettings() will apply the saved value.
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null');
    if (saved && saved.model) return;
  } catch (_) { /* ignore */ }

  if (!appConfig.default_model) return;
  const sel = document.getElementById('modelSelect');
  const custom = document.getElementById('modelCustom');

  if (Array.from(sel.options).some((option) => option.value === appConfig.default_model)) {
    sel.value = appConfig.default_model;
    custom.style.display = 'none';
  } else {
    sel.value = 'custom';
    custom.style.display = 'block';
    custom.value = appConfig.default_model;
  }
}

async function loadConfig() {
  try {
    logger.info('config', 'Loading configuration from /config');
    const resp = await fetch('/config');
    if (!resp.ok) {
      logger.warn('config', `Config endpoint returned ${resp.status}`);
      return;
    }

    const config = await resp.json();
    Object.assign(appConfig, config || {});
    applyConfig();
    logger.info('config', 'Configuration loaded successfully', { keys: Object.keys(config || {}) });
  } catch (err) {
    logger.error('config', 'Failed to load configuration', { error: err?.message });
  }
}

function appendMessage(container, text, role, note = '', images = []) {
  const group = document.createElement('div');
  group.classList.add('message-group', role);
  const bubble = document.createElement('div');
  bubble.classList.add('message-bubble');

  // Render any attached images above the text
  if (images && images.length) {
    const gallery = document.createElement('div');
    gallery.classList.add('message-images');
    for (const img of images) {
      const imgEl = document.createElement('img');
      imgEl.src = typeof img === 'string' ? img : img.dataUrl;
      imgEl.alt = (typeof img === 'object' && img.name) ? img.name : 'attached image';
      imgEl.classList.add('message-image');
      gallery.appendChild(imgEl);
    }
    bubble.appendChild(gallery);
  }

  if (text) {
    const textEl = document.createElement('div');
    textEl.classList.add('message-text');
    // Assistant messages render as Markdown; user messages stay plain (escaped).
    if (role === 'assistant') {
      textEl.classList.add('markdown-body');
      textEl.innerHTML = renderMarkdown(text);
    } else {
      textEl.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');
    }
    bubble.appendChild(textEl);
  }

  // Stash the raw text on the bubble so the copy button can grab the original
  // (un-rendered) content regardless of Markdown formatting.
  bubble.dataset.rawText = text || '';
  // Add a "copy message" button (and wire up any per-code-block copy buttons).
  addCopyButton(bubble);
  enhanceCodeBlocks(bubble);

  group.appendChild(bubble);
  let noteEl = null;
  if (note) {
    noteEl = document.createElement('div');
    noteEl.classList.add('message-note');
    noteEl.textContent = note;
    group.appendChild(noteEl);
  }
  container.appendChild(group);
  return { group, bubble, noteEl };
}

// Render text into a bubble. `asMarkdown` enables Markdown formatting (used for
// assistant messages). Preserves any image gallery already present in the bubble.
// `addButtons` controls whether copy buttons are (re)attached — skip during
// streaming for performance, then enable once on the final render.
function renderBubbleText(bubble, text, asMarkdown = false, addButtons = true) {
  let textEl = bubble.querySelector('.message-text');
  if (!textEl) {
    textEl = document.createElement('div');
    textEl.classList.add('message-text');
    bubble.appendChild(textEl);
  }
  if (asMarkdown) {
    textEl.classList.add('markdown-body');
    textEl.innerHTML = renderMarkdown(text);
  } else {
    textEl.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');
  }
  bubble.dataset.rawText = text || '';
  if (addButtons) {
    addCopyButton(bubble);
    enhanceCodeBlocks(bubble);
  }
}

// Copy text to the clipboard, with a fallback for non-secure contexts.
async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (_) { /* fall through to legacy path */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch (_) {
    return false;
  }
}

// Briefly show a "Copied!" state on a button.
function flashCopied(btn, label = 'Copy') {
  const original = label;
  btn.classList.add('copied');
  btn.textContent = 'Copied!';
  setTimeout(() => {
    btn.classList.remove('copied');
    btn.textContent = original;
  }, 1200);
}

// Add a "copy whole message" button to a bubble (idempotent). Skips empty text.
function addCopyButton(bubble) {
  if (bubble.querySelector('.copy-msg-btn')) return; // already added
  if (!bubble.dataset.rawText) return; // nothing to copy yet
  const btn = document.createElement('button');
  btn.className = 'copy-msg-btn';
  btn.type = 'button';
  btn.textContent = 'Copy';
  btn.title = 'Copy message';
  btn.addEventListener('click', async () => {
    const ok = await copyToClipboard(bubble.dataset.rawText || '');
    if (ok) flashCopied(btn);
    else { btn.textContent = 'Failed'; setTimeout(() => (btn.textContent = 'Copy'), 1200); }
  });
  bubble.appendChild(btn);
  // Add a "Remember" button (saves the message to the Obsidian vault) when a
  // vault is configured on the server.
  addRememberButton(bubble);
}

// Persist arbitrary text to the Obsidian vault via the /memory/save endpoint.
// Returns the parsed response ({ ok, path, title }) or { error }.
async function saveMemory(title, content, tags = []) {
  try {
    const resp = await fetch('/memory/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, tags }),
    });
    const data = await resp.json();
    if (!resp.ok) return { error: data?.error || `HTTP ${resp.status}` };
    return data;
  } catch (err) {
    return { error: err?.message || 'request failed' };
  }
}

// Add a manual "💾 Remember" button to a bubble. Works regardless of the
// Tool-calling / auto-recall toggles — it only requires a configured vault.
function addRememberButton(bubble) {
  if (!appConfig.has_obsidian) return; // no vault configured
  if (bubble.querySelector('.remember-msg-btn')) return; // already added
  if (!bubble.dataset.rawText) return; // nothing to save
  const btn = document.createElement('button');
  btn.className = 'remember-msg-btn';
  btn.type = 'button';
  btn.textContent = '💾 Remember';
  btn.title = 'Save this message to your Obsidian memory';
  btn.addEventListener('click', async () => {
    const text = bubble.dataset.rawText || '';
    if (!text.trim()) return;
    // Derive a short title from the first non-empty line.
    const firstLine = text.split('\n').map((l) => l.trim()).find(Boolean) || 'Memory';
    const title = firstLine.slice(0, 60);
    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = 'Saving…';
    const result = await saveMemory(title, text, ['manual']);
    btn.disabled = false;
    if (result && result.ok) {
      btn.classList.add('copied');
      btn.textContent = 'Saved ✓';
      logger.info('memory', `Manually saved memory → ${result.path}`);
      setTimeout(() => { btn.classList.remove('copied'); btn.textContent = original; }, 1500);
    } else {
      btn.textContent = 'Failed';
      logger.warn('memory', 'Manual save failed', { error: result?.error });
      setTimeout(() => (btn.textContent = original), 1500);
    }
  });
  bubble.appendChild(btn);
}

// Add a "copy" button to each code block inside a bubble (idempotent).
function enhanceCodeBlocks(bubble) {
  const pres = bubble.querySelectorAll('pre.md-pre');
  pres.forEach((pre) => {
    if (pre.querySelector('.copy-code-btn')) return; // already enhanced
    const code = pre.querySelector('code');
    if (!code) return;
    const btn = document.createElement('button');
    btn.className = 'copy-code-btn';
    btn.type = 'button';
    btn.textContent = 'Copy';
    btn.title = 'Copy code';
    btn.addEventListener('click', async () => {
      const ok = await copyToClipboard(code.textContent || '');
      if (ok) flashCopied(btn);
      else { btn.textContent = 'Failed'; setTimeout(() => (btn.textContent = 'Copy'), 1200); }
    });
    pre.appendChild(btn);
  });
}

// Format a usage object into a compact human-readable token summary.
function formatUsage(usage) {
  if (!usage) return '';
  const prompt = usage.prompt_tokens ?? usage.input_tokens;
  const completion = usage.completion_tokens ?? usage.output_tokens;
  const total = usage.total_tokens ?? ((prompt || 0) + (completion || 0));
  const parts = [];
  if (prompt != null) parts.push(`${prompt} in`);
  if (completion != null) parts.push(`${completion} out`);
  if (total != null) parts.push(`${total} total`);
  return parts.length ? `${parts.join(' · ')} tokens` : '';
}

// Append or update a small note line (context details + token usage) on a group.
function setMessageNote(group, existingNoteEl, parts) {
  const text = parts.filter(Boolean).join('  •  ');
  if (!text) return existingNoteEl;
  let noteEl = existingNoteEl;
  if (!noteEl) {
    noteEl = document.createElement('div');
    noteEl.classList.add('message-note');
    group.appendChild(noteEl);
  }
  noteEl.textContent = text;
  return noteEl;
}

// ─── Edit & resend / regenerate ──────────────────────────────────────────────
// Re-run the conversation from a given point. `upToUserIndex` is the index in
// chatDisplayHistory of the user turn whose answer we want to (re)generate; all
// turns at and after the following assistant turn are discarded, then the user
// message is re-sent.
async function regenerateFromUser(userDisplayIndex, overrideContent = null) {
  if (activeAbortController) return; // don't interrupt an in-flight request

  const userTurn = chatDisplayHistory[userDisplayIndex];
  if (!userTurn || userTurn.role !== 'user') return;

  const content = overrideContent != null ? overrideContent : userTurn.content;
  const images = userTurn.images || [];

  // Truncate both histories to just before this user turn. We'll re-send the
  // user message via sendMessage(), which re-appends it and its response.
  conversationHistory.length = userDisplayIndex; // API history is 1:1 with display turns here
  chatDisplayHistory.length = userDisplayIndex;

  // Rebuild the visible conversation from the truncated display history.
  rerenderConversation();

  // Stage the original images (if any) and the (possibly edited) content, then send.
  pendingImages.length = 0;
  if (images.length) {
    for (const url of images) pendingImages.push({ dataUrl: url, name: 'image' });
  }
  showPendingImages();
  document.getElementById('content').value = content;
  await sendMessage();
}

// Re-render the whole conversation DOM from chatDisplayHistory.
function rerenderConversation() {
  const conversation = document.getElementById('conversation');
  conversation.innerHTML = '';
  chatDisplayHistory.forEach((turn, idx) => {
    const { group } = appendMessage(conversation, turn.content, turn.role, turn.note || '', turn.images || []);
    addMessageActions(group, turn.role, idx);
  });
  conversation.scrollTop = conversation.scrollHeight;
}

// Add per-message action buttons: "Regenerate" on assistant turns, "Edit" on
// user turns. `displayIndex` is the turn's index in chatDisplayHistory.
function addMessageActions(group, role, displayIndex) {
  if (!group || group.querySelector('.msg-actions')) return;
  const bar = document.createElement('div');
  bar.className = 'msg-actions';

  if (role === 'assistant') {
    const btn = document.createElement('button');
    btn.className = 'msg-action-btn';
    btn.type = 'button';
    btn.textContent = '↻ Regenerate';
    btn.title = 'Regenerate this response';
    btn.addEventListener('click', () => {
      // The preceding turn should be the user message that prompted this.
      const userIdx = displayIndex - 1;
      if (chatDisplayHistory[userIdx]?.role === 'user') {
        regenerateFromUser(userIdx);
      }
    });
    bar.appendChild(btn);
  } else if (role === 'user') {
    const btn = document.createElement('button');
    btn.className = 'msg-action-btn';
    btn.type = 'button';
    btn.textContent = '✎ Edit';
    btn.title = 'Edit and resend this message';
    btn.addEventListener('click', () => startEditUserMessage(group, displayIndex));
    bar.appendChild(btn);
  }

  group.appendChild(bar);
}

// Turn a user message bubble into an inline editor; on save, re-send from there.
function startEditUserMessage(group, displayIndex) {
  if (activeAbortController) return;
  const turn = chatDisplayHistory[displayIndex];
  if (!turn || turn.role !== 'user') return;
  if (group.querySelector('.msg-edit-area')) return; // already editing

  const bubble = group.querySelector('.message-bubble');
  const textEl = bubble?.querySelector('.message-text');
  if (textEl) textEl.style.display = 'none';

  const wrap = document.createElement('div');
  wrap.className = 'msg-edit-wrap';
  const ta = document.createElement('textarea');
  ta.className = 'msg-edit-area';
  ta.value = turn.content;
  const controls = document.createElement('div');
  controls.className = 'msg-edit-controls';
  const save = document.createElement('button');
  save.type = 'button';
  save.className = 'msg-edit-save';
  save.textContent = 'Send';
  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.className = 'msg-edit-cancel';
  cancel.textContent = 'Cancel';
  controls.appendChild(save);
  controls.appendChild(cancel);
  wrap.appendChild(ta);
  wrap.appendChild(controls);
  bubble.appendChild(wrap);
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);

  const cleanup = () => {
    wrap.remove();
    if (textEl) textEl.style.display = '';
  };
  cancel.addEventListener('click', cleanup);
  save.addEventListener('click', () => {
    const newContent = ta.value.trim();
    if (!newContent) return;
    regenerateFromUser(displayIndex, newContent);
  });
  ta.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') cleanup();
    else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      save.click();
    }
  });
}

async function loadModels() {
  const status = document.getElementById('modelsStatus');
  status.textContent = 'Loading models...';
  logger.info('models', 'Starting model load');
  // The key may be blank when the server holds it; the proxy injects it.
  const key = safeTrim(document.getElementById('apiKeyInput').value);
  const base = safeTrim(document.getElementById('baseUrlInput').value) || appConfig.base_url;
  if (!base || (!key && !appConfig.has_api_key)) {
    status.textContent = 'API key or Base URL missing';
    logger.warn('models', 'Missing API key or base URL');
    return;
  }

  const url = '/api/v1/models';

  try {
    logger.info('models', 'Fetching from API', { url });
    const headers = { Accept: 'application/json' };
    // Only send Authorization if the user typed a key; otherwise the proxy adds it.
    if (key) headers.Authorization = 'Bearer ' + key;
    const resp = await fetch(url, {
      method: 'GET',
      headers,
    });

    const text = await resp.text();
    if (!resp.ok) {
      status.textContent = `Failed (${resp.status}): ${resp.statusText}`;
      logger.error('models', `Fetch failed: ${resp.status}`, { statusText: resp.statusText });
      return;
    }

    let parsed = null;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      parsed = null;
    }

    // Simplify model parsing: expect 'data' or 'models' array, or a root array.
    const models = parsed?.data || parsed?.models || (Array.isArray(parsed) ? parsed : null);

    if (!models || models.length === 0) {
      status.textContent = 'No models found in response';
      logger.warn('models', 'No models found in response');
      return;
    }

    const sel = document.getElementById('modelSelect');
    sel.innerHTML = '';

    const groups = {};
    models.forEach((m) => {
      let id = typeof m === 'string' ? m : m.id || m.model || m.name || m.model_id || m.modelId || m.name_id;
      let label = typeof m === 'string' ? m : m.name || m.id || JSON.stringify(m);
      const provider = typeof m === 'object' && (m.provider || m.vendor || m.source || m.framework)
        ? m.provider || m.vendor || m.source || m.framework
        : 'Available';
      if (!id) id = label;
      groups[provider] = groups[provider] || [];
      groups[provider].push({ id, label });
    });

    Object.keys(groups).forEach((provider) => {
      const optg = document.createElement('optgroup');
      optg.label = provider;
      groups[provider].forEach((item) => {
        const opt = document.createElement('option');
        opt.value = item.id;
        opt.textContent = item.label;
        optg.appendChild(opt);
      });
      sel.appendChild(optg);
    });

    const otherOpt = document.createElement('option');
    otherOpt.value = 'custom';
    otherOpt.textContent = 'Other (paste model id)';
    sel.appendChild(otherOpt);
    status.textContent = `Loaded ${models.length} models`;
    document.getElementById('modelCustom').style.display = sel.value === 'custom' ? 'block' : 'none';
    applyDefaultModel();
    syncComposerModelOptions();
    updateParamFieldStates();
    logger.info('models', `Successfully loaded ${models.length} models`);
  } catch (err) {
    status.textContent = 'Error loading models: ' + (err && err.message ? err.message : err);
    logger.error('models', 'Error loading models', { error: err?.message });
  }
}

function getChatInputs() {
  return {
    key: safeTrim(document.getElementById('apiKeyInput').value),
    base: safeTrim(document.getElementById('baseUrlInput').value) || appConfig.base_url,
    content: safeTrim(document.getElementById('content').value),
    model: getSelectedModel(),
    systemPrompt: safeTrim(document.getElementById('systemPrompt').value) || appConfig.default_system_prompt,
    temperature: parseFloat(document.getElementById('temperature').value),
    maxTokens: parseInt(document.getElementById('maxTokens').value, 10),
    reasoningEffort: document.getElementById('reasoningEffort')?.value || '',
    jsonMode: document.getElementById('jsonModeToggle')?.checked || false,
    jsonSchema: safeTrim(document.getElementById('jsonSchema')?.value || ''),
  };
}

// Build the `response_format` object for structured output, if enabled.
// Returns { responseFormat, error }. `responseFormat` is null when disabled.
function buildResponseFormat(inputs) {
  if (!inputs.jsonMode) return { responseFormat: null };

  // No schema provided → fall back to plain JSON object mode.
  if (!inputs.jsonSchema) {
    return { responseFormat: { type: 'json_object' } };
  }

  let parsed;
  try {
    parsed = JSON.parse(inputs.jsonSchema);
  } catch (err) {
    return { error: 'Invalid JSON Schema: ' + (err?.message || 'could not parse') };
  }

  // Accept either a full json_schema wrapper ({ name, schema, strict }) or a
  // bare JSON Schema object ({ type: 'object', properties: {...} }).
  let name = 'response';
  let schema = parsed;
  let strict = true;
  if (parsed.schema && typeof parsed.schema === 'object') {
    name = parsed.name || 'response';
    schema = parsed.schema;
    strict = parsed.strict !== undefined ? parsed.strict : true;
  }

  // OpenAI strict mode requires every object to set additionalProperties:false
  // and list ALL properties in `required`. Auto-fix the schema so users don't
  // have to remember these rules. (Skipped when strict is explicitly false.)
  if (strict) {
    schema = enforceStrictSchema(schema);
  }

  return { responseFormat: { type: 'json_schema', json_schema: { name, schema, strict } } };
}

// Recursively make a JSON Schema compatible with OpenAI strict mode:
// every object gets additionalProperties:false and required = all property keys.
function enforceStrictSchema(node) {
  if (Array.isArray(node)) return node.map(enforceStrictSchema);
  if (!node || typeof node !== 'object') return node;

  const out = { ...node };

  if (out.type === 'object' || out.properties) {
    if (out.properties && typeof out.properties === 'object') {
      const props = {};
      for (const [key, value] of Object.entries(out.properties)) {
        props[key] = enforceStrictSchema(value);
      }
      out.properties = props;
      out.required = Object.keys(props);
    }
    if (out.additionalProperties === undefined) out.additionalProperties = false;
  }

  if (out.items) out.items = enforceStrictSchema(out.items);
  if (out.$defs) {
    const defs = {};
    for (const [k, v] of Object.entries(out.$defs)) defs[k] = enforceStrictSchema(v);
    out.$defs = defs;
  }

  return out;
}

async function prepareContextMessages(inputs) {
  const contextMessages = [];
  const contextDetails = [];

  // 1. Context7
  let context7Text = '';
  if (context7Enabled) {
    if (lastFetchedContext) {
      context7Text = lastFetchedContext;
      logger.info('chat', 'Using cached Context7 data');
    } else {
      document.getElementById('responseLog').textContent = 'Fetching context from Context7...';
      context7Text = await fetchContext7(inputs.content);
    }
    if (context7Text) {
      contextMessages.push({ role: 'system', content: 'Context7 context:\n' + context7Text });
      contextDetails.push('Context7');
    }
  }

  // 2. File Chunks
  if (fileChunks.length > 0) {
    const relevantChunks = getRelevantChunks(inputs.content, topChunksPerQuery);
    if (relevantChunks.length > 0) {
      const method = 'keyword matching';
      const CONTEXT_CHAR_LIMIT = 120000; // ~30k tokens
      let totalChars = 0;
      const includedChunks = relevantChunks.filter(chunk => {
        if (totalChars + chunk.text.length > CONTEXT_CHAR_LIMIT) return false;
        totalChars += chunk.text.length;
        return true;
      });
      const relevantChunksText = includedChunks
        .map((c, i) => `[Chunk ${i+1} from ${c.fileName} (relevance: ${(c.score * 100).toFixed(0)}%)]\n${c.text}`)
        .join('\n\n---\n\n');
      contextMessages.push({ role: 'system', content: `Uploaded files context (${method}):\n` + relevantChunksText });
      contextDetails.push(`Files: ${uploadedFiles.join(', ')}`);
    }
  }
  
  // 3. Obsidian memory auto-recall: search the vault and inject the top matches
  // as context before sending (opt-in, independent of the memory tools).
  if (memoryAutoRecall && appConfig.has_obsidian) {
    try {
      document.getElementById('responseLog').textContent = 'Recalling from Obsidian memory...';
      const resp = await fetch(`/memory/search?q=${encodeURIComponent(inputs.content)}&k=5`);
      const data = await resp.json();
      const results = (resp.ok && data?.results) ? data.results : [];
      if (results.length) {
        const recalled = results
          .map((r, i) => `[Memory ${i + 1} from ${r.path}]\n${r.snippet}`)
          .join('\n\n---\n\n');
        contextMessages.push({
          role: 'system',
          content: 'Relevant long-term memory from the user\'s Obsidian vault:\n' + recalled,
        });
        contextDetails.push(`Memory: ${results.length} note(s)`);
        logger.info('memory', `Auto-recalled ${results.length} memory note(s)`);
      }
    } catch (err) {
      logger.warn('memory', 'Auto-recall failed', { error: err?.message });
    }
  }

  return { contextMessages, contextDetails };
}

async function callChatApi(payload) {
  const endpoint = '/api/v1/chat/completions';
  const inputs = getChatInputs(); // We only need the key from here
  try {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    // Send Authorization only if the user typed a key; otherwise the proxy injects it.
    if (inputs.key) headers['Authorization'] = 'Bearer ' + inputs.key;
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: activeAbortController?.signal,
    });
    const text = await resp.text();
    if (!resp.ok) {
      logger.error('chat', `API error: ${resp.status}`, { response: text?.substring(0, 1000) });
      return { error: `API error ${resp.status}: ${text || resp.statusText}` };
    }
    const parsed = JSON.parse(text);
    const message = parsed?.choices?.[0]?.message || null;
    const assistantText = message?.content || null;
    const usage = parsed?.usage || null;
    return { assistantText, message, usage };
  } catch (err) {
    if (err?.name === 'AbortError') {
      logger.info('chat', 'Request cancelled by user');
      return { aborted: true };
    }
    logger.error('chat', 'Network error sending message', { error: err?.message });
    return { error: 'Network error: ' + err.message };
  }
}

// Append a small "tool activity" indicator into the conversation.
function appendToolActivity(container, toolNames) {
  const el = document.createElement('div');
  el.classList.add('tool-activity');
  const labels = toolNames.map(n => `<span class="tool-chip">🔧 ${escapeHtml(n)}</span>`).join('');
  el.innerHTML = `<span class="tool-activity-label">Using tools:</span> ${labels}`;
  container.appendChild(el);
  return el;
}

// Run the chat completion with tool support. Performs up to MAX_TOOL_ROUNDS
// rounds of: call model → if it requests tool calls, execute them and loop.
// Returns { assistantText, usage, toolsUsed } or { error }.
async function runWithTools(basePayload, conversation) {
  const messages = basePayload.messages.slice();
  const tools = getEnabledTools();
  const toolsUsed = [];
  let lastUsage = null;

  if (!tools.length) {
    logger.warn('tools', 'No tools available to advertise; falling back to a normal call');
    const { assistantText, usage, error, aborted } = await callChatApi(basePayload);
    if (aborted) return { aborted: true };
    return error ? { error } : { assistantText, usage, toolsUsed };
  }

  logger.info('tools', `Starting tool loop`, { toolCount: tools.length, toolNames: tools.map(t => t.function?.name) });

  for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
    // Tool calls require a non-streaming request so we can inspect tool_calls.
    const payload = { ...basePayload, messages, tools, tool_choice: 'auto' };
    const { message, usage, error, aborted } = await callChatApi(payload);
    if (aborted) return { aborted: true };
    if (error) {
      logger.error('tools', `Round ${round} request failed`, { error });
      return { error };
    }
    lastUsage = usage || lastUsage;

    if (!message) {
      logger.error('tools', `Round ${round} returned no message object`);
      return { error: 'The model returned no message. The selected model may not support tool calling.' };
    }

    const toolCalls = message?.tool_calls || [];
    logger.info('tools', `Round ${round} response`, { hasContent: !!message.content, toolCallCount: toolCalls.length });

    if (!toolCalls.length) {
      // No tools requested — this is the final answer.
      return { assistantText: message?.content || null, usage: lastUsage, toolsUsed };
    }

    // Record the assistant's tool-call turn verbatim (required by the API).
    messages.push(message);

    // Surface which tools are running in the UI.
    appendToolActivity(conversation, toolCalls.map(tc => tc.function?.name || 'tool'));
    conversation.scrollTop = conversation.scrollHeight;

    // Execute each requested tool and append its result.
    for (const toolCall of toolCalls) {
      const name = toolCall.function?.name || 'tool';
      toolsUsed.push(name);
      const result = await executeToolCall(toolCall);
      messages.push({
        role: 'tool',
        tool_call_id: toolCall.id,
        name,
        content: typeof result === 'string' ? result : JSON.stringify(result),
      });
    }
  }

  // Hit the round limit — make one final call without tools to force an answer.
  logger.warn('tools', `Reached MAX_TOOL_ROUNDS (${MAX_TOOL_ROUNDS}); forcing final answer`);
  const finalPayload = { ...basePayload, messages };
  const { assistantText, usage, error, aborted } = await callChatApi(finalPayload);
  if (aborted) return { aborted: true };
  if (error) return { error };
  return { assistantText, usage: usage || lastUsage, toolsUsed };
}

// Stream a chat completion, invoking onDelta(textChunk) as tokens arrive.
// Returns { assistantText } on success or { error } on failure.
async function streamChatApi(payload, onDelta) {
  const endpoint = '/api/v1/chat/completions';
  const inputs = getChatInputs();
  let assistantText = '';
  try {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    };
    if (inputs.key) headers['Authorization'] = 'Bearer ' + inputs.key;
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        ...payload,
        stream: true,
        // Ask the API to emit a final chunk containing token usage
        stream_options: { include_usage: true },
      }),
      signal: activeAbortController?.signal,
    });

    if (!resp.ok) {
      const text = await resp.text();
      logger.error('chat', `API error: ${resp.status}`, { response: text?.substring(0, 300) });
      return { error: `API error ${resp.status}: ${text || resp.statusText}` };
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let usage = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by blank lines
      const frames = buffer.split('\n\n');
      buffer = frames.pop() || ''; // keep the (possibly partial) last frame

      for (const frame of frames) {
        for (const line of frame.split('\n')) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const data = trimmed.slice(5).trim();
          if (data === '[DONE]') continue;
          try {
            const json = JSON.parse(data);
            const delta = json?.choices?.[0]?.delta?.content;
            if (delta) {
              assistantText += delta;
              if (onDelta) onDelta(delta, assistantText);
            }
            // The usage chunk arrives with an empty choices array near the end
            if (json?.usage) usage = json.usage;
          } catch (_) {
            // Ignore keep-alive comments or partial JSON; will be retried next chunk
          }
        }
      }
    }

    return { assistantText: assistantText || null, usage };
  } catch (err) {
    if (err?.name === 'AbortError') {
      logger.info('chat', 'Stream cancelled by user');
      // Return whatever was streamed so far so it can be kept on screen.
      return { aborted: true, assistantText: typeof assistantText !== 'undefined' ? assistantText : null };
    }
    logger.error('chat', 'Network error during stream', { error: err?.message });
    return { error: 'Network error: ' + err.message };
  }
}

// Persist a completed user/assistant exchange to history and clear the input.
async function persistExchange(userMessage, assistantText, contextNote, usageText = '', userApiContent = null, userImages = [], assistantNoteParts = null) {
  // The assistant's display note combines context details and token usage so
  // both are restored when the conversation is reloaded from history.
  // `assistantNoteParts` (when provided) lets the caller override the context
  // segments shown on the assistant turn — e.g. to substitute a "Tools: …"
  // note in place of a misleading "No external context" label.
  const assistantNoteSegments = Array.isArray(assistantNoteParts)
    ? [...assistantNoteParts, usageText]
    : [contextNote, usageText];
  const assistantNote = assistantNoteSegments.filter(Boolean).join('  •  ');

  // For the API history, preserve the multimodal content array if images were sent.
  conversationHistory.push({ role: 'user', content: userApiContent != null ? userApiContent : userMessage });
  conversationHistory.push({ role: 'assistant', content: assistantText });

  // For display history, store the plain text plus image data URLs so thumbnails
  // can be re-rendered when a session is restored.
  const userTurn = { role: 'user', content: userMessage, note: contextNote, timestamp: new Date().toISOString() };
  if (userImages && userImages.length) {
    userTurn.images = userImages.map(img => (typeof img === 'string' ? img : img.dataUrl));
  }
  chatDisplayHistory.push(userTurn);
  chatDisplayHistory.push({ role: 'assistant', content: assistantText, note: assistantNote, usage: usageText || undefined, timestamp: new Date().toISOString() });

  await saveChatHistory();
  const contentEl = document.getElementById('content');
  contentEl.value = '';
  contentEl.style.height = 'auto';
  }

function normalizeAssistantText(assistantMessage) {
  if (assistantMessage == null) return 'No assistant text received.';
  if (typeof assistantMessage === 'object') return JSON.stringify(assistantMessage, null, 2);
  return assistantMessage;
}

// Try hard to pull a JSON value out of a model response that may be wrapped in
// Markdown code fences or surrounded by prose. Returns the parsed value, or
// null if nothing parseable is found.
function extractJson(text) {
  if (typeof text !== 'string') return null;

  // 1. Direct parse
  try { return JSON.parse(text); } catch (_) {}

  // 2. Strip ```json ... ``` or ``` ... ``` fences
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) {
    try { return JSON.parse(fence[1].trim()); } catch (_) {}
  }

  // 3. Grab the first {...} or [...] block by scanning balanced brackets
  const candidate = extractBalanced(text);
  if (candidate) {
    try { return JSON.parse(candidate); } catch (_) {}
  }

  return null;
}

// Extract the first balanced {...} or [...] substring, respecting strings.
function extractBalanced(text) {
  const start = text.search(/[{[]/);
  if (start === -1) return null;
  const open = text[start];
  const close = open === '{' ? '}' : ']';
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (escape) { escape = false; continue; }
    if (ch === '\\') { escape = true; continue; }
    if (ch === '"') inString = !inString;
    if (inString) continue;
    if (ch === open) depth++;
    else if (ch === close) {
      depth--;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

async function sendMessage() {
  const startTime = performance.now();
  const inputs = getChatInputs();
  const responseLog = document.getElementById('responseLog');
  responseLog.textContent = '';

  if ((!inputs.key && !appConfig.has_api_key) || !inputs.base || !inputs.content) {
    alert('API key, base URL and message are required');
    return;
  }
  document.querySelector('.main-content').classList.add('in-conversation');
  logger.info('chat', 'Sending message', { userMessage: inputs.content.substring(0, 100), model: inputs.model });

  // 1. Prepare context from files, Context7, etc.
  const { contextMessages, contextDetails } = await prepareContextMessages(inputs);
  
  // 2. Build final message payload
  const messages = [];
  if (inputs.systemPrompt) messages.push({ role: 'system', content: inputs.systemPrompt });
  messages.push(...conversationHistory); // Add prior turns
  messages.push(...contextMessages);     // Add file/plugin context

  // Build the current user message. If images are attached, use the
  // multimodal content-array format that vision models expect.
  const attachedImages = pendingImages.slice();
  let userApiContent;
  if (attachedImages.length) {
    userApiContent = [
      { type: 'text', text: inputs.content },
      ...attachedImages.map(img => ({ type: 'image_url', image_url: { url: img.dataUrl } })),
    ];
  } else {
    userApiContent = inputs.content;
  }
  messages.push({ role: 'user', content: userApiContent });

    const payload = { model: inputs.model, messages };

  // Some models reject certain params (e.g. reasoning models deprecate
  // `temperature`). Omit any excluded params for the selected model.
  const excludedParams = getExcludedParams(inputs.model);

  if (!excludedParams.has('temperature') && !Number.isNaN(inputs.temperature)) {
    payload.temperature = inputs.temperature;
  } else if (excludedParams.has('temperature') && !Number.isNaN(inputs.temperature)) {
    logger.info('chat', `Omitting "temperature" — not supported by model "${inputs.model}"`);
  }

  if (!excludedParams.has('max_tokens') && !Number.isNaN(inputs.maxTokens) && inputs.maxTokens > 0) {
    payload.max_tokens = inputs.maxTokens;
  } else if (excludedParams.has('max_tokens') && !Number.isNaN(inputs.maxTokens) && inputs.maxTokens > 0) {
    logger.info('chat', `Omitting "max_tokens" — not supported by model "${inputs.model}"`);
  }

  // Reasoning effort (for reasoning-capable models): low | medium | high
  if (inputs.reasoningEffort && !excludedParams.has('reasoning_effort')) {
    payload.reasoning_effort = inputs.reasoningEffort;
  } else if (inputs.reasoningEffort && excludedParams.has('reasoning_effort')) {
    logger.info('chat', `Omitting "reasoning_effort" — not supported by model "${inputs.model}"`);
  }

  // Structured output via response_format (json_object or json_schema)
  const { responseFormat, error: rfError } = buildResponseFormat(inputs);
  if (rfError) {
    responseLog.textContent = rfError;
    logger.warn('chat', 'Structured output disabled — schema error', { error: rfError });
    return;
  }
  if (responseFormat) {
    payload.response_format = responseFormat;
    logger.info('chat', 'Structured output enabled', { type: responseFormat.type, responseFormat });

    // Belt-and-suspenders: many OpenAI-compatible gateways IGNORE response_format.
    // Add an explicit system instruction so the model returns raw JSON regardless.
    let jsonInstruction = 'You must respond with ONLY a single valid JSON value. '
      + 'Do not include any explanatory text, Markdown, code fences, or formatting — output raw JSON only.';
    if (responseFormat.type === 'json_schema' && responseFormat.json_schema?.schema) {
      jsonInstruction += ' The JSON must conform exactly to this JSON Schema:\n'
        + JSON.stringify(responseFormat.json_schema.schema);
    }
    // Prepend so user/system prompts still take precedence on content, but the
    // formatting rule is always present.
    messages.unshift({ role: 'system', content: jsonInstruction });
  }

  const conversation = document.getElementById('conversation');
  const contextDetailsWithImages = attachedImages.length
    ? [...contextDetails, `${attachedImages.length} image(s)`]
    : contextDetails;
  const contextNote = contextDetailsWithImages.join(' + ') || 'No external context';

  // Render the user's message immediately (with image thumbnails).
  // Its index in chatDisplayHistory will be the current length (persistExchange
  // pushes the user turn next, then the assistant turn).
  const userDisplayIndex = chatDisplayHistory.length;
  const { group: userGroup } = appendMessage(conversation, inputs.content, 'user', contextNote, attachedImages);
  addMessageActions(userGroup, 'user', userDisplayIndex);
  conversation.scrollTop = conversation.scrollHeight;

  // Clear the staged images now that they're part of the conversation
  pendingImages.length = 0;
  showPendingImages();

  // Disable send button while a response is in flight, and switch it to a Stop
  // button the user can click to abort the request.
  const sendBtn = document.getElementById('send');
  activeAbortController = new AbortController();
  setSendButtonState(true);

  try {
    if (toolsEnabled) {
      // 3a. Tool-calling path (non-streaming, multi-round)
      const { assistantText, usage, toolsUsed, error, aborted } = await runWithTools(payload, conversation);
      responseLog.textContent = '';

      if (aborted) {
        responseLog.textContent = 'Request cancelled.';
        return;
      }
      if (error) {
        responseLog.textContent = error;
        return;
      }

      const finalText = normalizeAssistantText(assistantText);
      const usageText = formatUsage(usage);
      const uniqueTools = toolsUsed && toolsUsed.length ? [...new Set(toolsUsed)] : [];
      const toolNote = uniqueTools.length ? `Tools: ${uniqueTools.join(', ')}` : '';
      // When the model actually used tools to pull in external info, the
      // pre-fetch "No external context" label is misleading — suppress it so the
      // note reflects what really happened.
      const contextNoteForAssistant = (uniqueTools.length && contextNote === 'No external context')
        ? ''
        : contextNote;
      const { group, noteEl } = appendMessage(conversation, finalText, 'assistant', contextNote);
      setMessageNote(group, noteEl, [contextNoteForAssistant, toolNote, usageText]);
      addMessageActions(group, 'assistant', userDisplayIndex + 1);
      conversation.scrollTop = conversation.scrollHeight;
      await persistExchange(inputs.content, finalText, contextNote, usageText, userApiContent, attachedImages, [contextNoteForAssistant, toolNote]);

      const duration = (performance.now() - startTime).toFixed(2);
      logger.info('chat', 'Tool-assisted response received', { duration: `${duration}ms`, textLength: finalText.length, usage: usage || null, toolsUsed });
    } else if (streamEnabled && !inputs.jsonMode) {
      // 3b. Stream the response, rendering tokens as they arrive
      const { group, bubble, noteEl } = appendMessage(conversation, '', 'assistant', contextNote);
      bubble.classList.add('streaming');

      const { assistantText, usage, error, aborted } = await streamChatApi(payload, (_delta, full) => {
        // Render partial tokens as plain text (Markdown on incomplete input looks
        // broken); the final text is re-rendered as Markdown below.
        renderBubbleText(bubble, full, false, false);
        conversation.scrollTop = conversation.scrollHeight;
      });

      bubble.classList.remove('streaming');

      if (error) {
        group.remove();
        responseLog.textContent = error;
        return;
      }

      // On abort, keep whatever streamed so far (if anything) and persist it.
      const finalText = normalizeAssistantText(assistantText);
      if (aborted && !assistantText) {
        group.remove();
        responseLog.textContent = 'Request cancelled.';
        return;
      }
      renderBubbleText(bubble, finalText, true);
      const usageText = formatUsage(usage);
      setMessageNote(group, noteEl, [contextNote, aborted ? 'cancelled' : '', usageText]);
      addMessageActions(group, 'assistant', userDisplayIndex + 1);
      conversation.scrollTop = conversation.scrollHeight;
      await persistExchange(inputs.content, finalText, contextNote, usageText, userApiContent, attachedImages);
      if (aborted) responseLog.textContent = 'Request cancelled (partial response kept).';

      const duration = (performance.now() - startTime).toFixed(2);
      logger.info('chat', 'Streamed response received', { duration: `${duration}ms`, textLength: finalText.length, usage: usage || null, aborted: !!aborted });
    } else {
      // 3c. Non-streaming request (also used for structured-output JSON mode)
      const { assistantText, usage, error, aborted } = await callChatApi(payload);
      responseLog.textContent = '';

      if (aborted) {
        responseLog.textContent = 'Request cancelled.';
        return;
      }
      if (error) {
        responseLog.textContent = error;
        return;
      }

      let finalText = normalizeAssistantText(assistantText);
      // Pretty-print JSON when structured output is enabled and the result parses.
      let jsonNote = '';
      if (inputs.jsonMode && typeof finalText === 'string') {
        const extracted = extractJson(finalText);
        if (extracted !== null) {
          // Wrap in a fenced code block so the Markdown renderer shows it as a
          // formatted JSON code block rather than reflowing it as prose.
          finalText = '```json\n' + JSON.stringify(extracted, null, 2) + '\n```';
          jsonNote = 'JSON ✓';
        } else {
          jsonNote = 'JSON ✕ (model returned invalid JSON)';
        }
      }
      const usageText = formatUsage(usage);
      const { group, noteEl } = appendMessage(conversation, finalText, 'assistant', contextNote);
      setMessageNote(group, noteEl, [contextNote, jsonNote, usageText]);
      addMessageActions(group, 'assistant', userDisplayIndex + 1);
      conversation.scrollTop = conversation.scrollHeight;
      await persistExchange(inputs.content, finalText, contextNote, usageText, userApiContent, attachedImages);

      const duration = (performance.now() - startTime).toFixed(2);
      logger.info('chat', 'Message sent and response received', { duration: `${duration}ms`, textLength: finalText.length, usage: usage || null, jsonMode: inputs.jsonMode });
    }
  } finally {
    activeAbortController = null;
    setSendButtonState(false);
  }
}

// Toggle the send button between "send" (↑) and "stop" (■) states.
function setSendButtonState(busy) {
  const sendBtn = document.getElementById('send');
  if (!sendBtn) return;
  if (busy) {
    sendBtn.classList.add('is-stop');
    sendBtn.textContent = '■';
    sendBtn.title = 'Stop generating';
  } else {
    sendBtn.classList.remove('is-stop');
    sendBtn.textContent = '↑';
    sendBtn.title = 'Send message (Ctrl+Enter)';
  }
}

// Abort the in-flight request, if any.
function cancelActiveRequest() {
  if (activeAbortController) {
    logger.info('chat', 'User requested cancellation');
    activeAbortController.abort();
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  if (prefersDark || localStorage.getItem('theme') === 'dark') {
    setTheme(true);
  }

  themeToggle.addEventListener('click', () => {
    setTheme(!document.body.classList.contains('dark-mode'));
  });

  document.querySelector('.new-chat-btn').addEventListener('click', async () => {
    document.getElementById('conversation').innerHTML = '';
    document.getElementById('content').value = '';
    clearUploadedFiles();
    pendingImages.length = 0;
    showPendingImages();
    lastFetchedContext = null;
    conversationHistory.length = 0;
    chatDisplayHistory.length = 0;
    currentSessionId = null;
    await fetch('/new-chat-session', { method: 'POST' });
    await showSessionsList();
    logger.info('chat', 'New chat started — conversation history cleared');
    document.querySelector('.main-content').classList.remove('in-conversation');
  });

  document.getElementById('send').addEventListener('click', () => {
    // The same button acts as Send or Stop depending on request state.
    if (activeAbortController) {
      cancelActiveRequest();
    } else {
      sendMessage();
    }
  });

  document.getElementById('streamToggle')?.addEventListener('change', (e) => {
    streamEnabled = e.target.checked;
    saveSettings();
    logger.info('chat', `Streaming ${streamEnabled ? 'enabled' : 'disabled'}`);
  });

  document.getElementById('toolsToggle')?.addEventListener('change', (e) => {
    toolsEnabled = e.target.checked;
    // Tool calling requires inspecting the full response, so it runs non-streamed.
    const streamToggle = document.getElementById('streamToggle');
    if (streamToggle) streamToggle.disabled = toolsEnabled;
    saveSettings();
    logger.info('tools', `Tool calling ${toolsEnabled ? 'enabled' : 'disabled'}`);
  });

  document.getElementById('jsonModeToggle')?.addEventListener('change', (e) => {
    const enabled = e.target.checked;
    const schemaBox = document.getElementById('jsonSchema');
    if (schemaBox) schemaBox.style.display = enabled ? 'block' : 'none';
    // Structured output needs the complete response to validate/format JSON,
    // so it runs non-streamed (like tool calling).
    const streamToggle = document.getElementById('streamToggle');
    if (streamToggle) streamToggle.disabled = enabled || toolsEnabled;
    saveSettings();
    logger.info('chat', `Structured output ${enabled ? 'enabled' : 'disabled'}`);
  });

  // Live-validate the JSON Schema textarea so users get immediate feedback.
  document.getElementById('jsonSchema')?.addEventListener('input', (e) => {
    const status = document.getElementById('jsonSchemaStatus');
    saveSettings();
    if (!status) return;
    const text = safeTrim(e.target.value);
    if (!text) {
      status.textContent = 'Empty → plain JSON object mode';
      status.style.color = 'var(--color-text-secondary)';
      return;
    }
    try {
      JSON.parse(text);
      status.textContent = '✓ Valid JSON';
      status.style.color = '#22c55e';
    } catch (err) {
      status.textContent = '✕ ' + (err?.message || 'Invalid JSON');
      status.style.color = '#ef4444';
    }
  });

  document.getElementById('reasoningEffort')?.addEventListener('change', (e) => {
    syncComposerFromSidebar();
    saveSettings();
    logger.info('chat', `Reasoning effort set to "${e.target.value || 'default'}"`);
  });
  document.getElementById('modelSelect').addEventListener('change', (e) => {
    const custom = document.getElementById('modelCustom');
    custom.style.display = e.target.value === 'custom' ? 'block' : 'none';
    syncComposerFromSidebar();
    updateParamFieldStates();
    saveSettings();
  });

  // Composer toolbar selects mirror the sidebar selects (and vice-versa).
  document.getElementById('composerModel')?.addEventListener('change', (e) => {
    const sel = document.getElementById('modelSelect');
    if (sel) {
      sel.value = e.target.value;
      sel.dispatchEvent(new Event('change'));
    }
  });
  document.getElementById('composerReasoning')?.addEventListener('change', (e) => {
    const sel = document.getElementById('reasoningEffort');
    if (sel) {
      sel.value = e.target.value;
      sel.dispatchEvent(new Event('change'));
    }
  });

  document.getElementById('modelCustom')?.addEventListener('input', () => {
    updateParamFieldStates();
    saveSettings();
  });
  document.getElementById('systemPrompt')?.addEventListener('input', saveSettings);
  document.getElementById('temperature')?.addEventListener('change', saveSettings);
  document.getElementById('maxTokens')?.addEventListener('change', saveSettings);
  document.getElementById('baseUrlInput')?.addEventListener('change', saveSettings);

  document.getElementById('loadModelsBtn').addEventListener('click', loadModels);

  const fetchBtn = document.getElementById('fetchContextBtn');
  fetchBtn.disabled = true;
  fetchBtn.style.opacity = '0.4';

  document.getElementById('context7Toggle').addEventListener('change', (e) => {
    context7Enabled = e.target.checked;
    const fetchBtn = document.getElementById('fetchContextBtn');
    fetchBtn.disabled = !context7Enabled;
    fetchBtn.style.opacity = context7Enabled ? '' : '0.4';
    if (!context7Enabled) {
      lastFetchedContext = null;
      showContextPreview(null);
    }
    saveSettings();
    logger.info('context7', `Context7 ${context7Enabled ? 'enabled' : 'disabled'}`);
  });

  document.getElementById('memoryToggle')?.addEventListener('change', (e) => {
    memoryEnabled = e.target.checked;
    saveSettings();
    logger.info('memory', `Obsidian memory ${memoryEnabled ? 'enabled' : 'disabled'}`);
  });

  document.getElementById('memoryAutoRecallToggle')?.addEventListener('change', (e) => {
    memoryAutoRecall = e.target.checked;
    saveSettings();
    logger.info('memory', `Memory auto-recall ${memoryAutoRecall ? 'enabled' : 'disabled'}`);
  });

  document.getElementById('fetchContextBtn').addEventListener('click', async () => {
    if (!context7Enabled) {
      document.getElementById('responseLog').textContent = 'Context7 is disabled.';
      return;
    }
    const content = safeTrim(document.getElementById('content').value);
    if (!content) {
      document.getElementById('responseLog').textContent = 'Enter a message to fetch context for.';
      return;
    }
    document.getElementById('responseLog').textContent = 'Fetching context...';
    const ctx = await fetchContext7(content);
    if (!ctx) {
      document.getElementById('responseLog').textContent = 'No context returned or context7 not configured.';
      showContextPreview(null);
      lastFetchedContext = null;
      return;
    }
    lastFetchedContext = ctx;
    showContextPreview(ctx);
    document.getElementById('responseLog').textContent = 'Context fetched. It will be included in next send.';
  });

  document.getElementById('content').addEventListener('keydown', (e) => {
    // Ignore send shortcuts while a request is in flight.
    if (activeAbortController) return;
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      sendMessage();
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  document.getElementById('fileUpload').addEventListener('change', handleFileUpload);

  // Composer attach button reuses the hidden file input.
  document.getElementById('composerAttach')?.addEventListener('click', () => {
    document.getElementById('fileUpload').click();
  });

  // Sidebar collapse/expand toggle (also acts as a drawer on mobile).
  document.getElementById('sidebarToggle')?.addEventListener('click', (e) => {
    const collapsed = document.querySelector('.app-container')
      ?.classList.toggle('sidebar-collapsed');
    e.currentTarget.setAttribute('aria-expanded', String(!collapsed));
  });

  // Auto-grow the message textarea up to its max-height.
  const contentEl = document.getElementById('content');
  const autoGrow = () => {
    if (!contentEl) return;
    contentEl.style.height = 'auto';
    contentEl.style.height = Math.min(contentEl.scrollHeight, 200) + 'px';
  };
  contentEl?.addEventListener('input', autoGrow);

  // Example-prompt chips in the empty state populate the composer and focus it.
  document.querySelectorAll('.example-prompt-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      if (contentEl) {
        contentEl.value = chip.textContent.trim();
        contentEl.focus();
        autoGrow();
      }
    });
  });

  document.getElementById('chunkSize').addEventListener('change', (e) => {
    chunkLineSize = parseInt(e.target.value, 10);
    saveSettings();
  });

  document.getElementById('topChunks').addEventListener('change', (e) => {
    topChunksPerQuery = parseInt(e.target.value, 10);
    saveSettings();
  });

  // Debug panel event listeners
  document.getElementById('debugLevel')?.addEventListener('change', () => {
    logger.updateDebugPanel();
  });

  document.getElementById('debugFilter')?.addEventListener('input', () => {
    logger.updateDebugPanel();
  });

  document.getElementById('debugClear')?.addEventListener('click', async () => {
    await logger.clear();
  });

  document.getElementById('debugToggle')?.addEventListener('click', () => {
    const panel = document.getElementById('debugPanel');
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
  });

  // Debug panel hidden by default
  document.getElementById('debugPanel').style.display = 'none';

  await loadConfig();
  // Restore saved UI settings (overrides server defaults applied by loadConfig).
  restoreSettings();
  // loadModels() repopulates the model dropdown; re-apply the saved model after.
  await loadModels();
  restoreSettings();
  // Sync the composer toolbar selects with the now-final sidebar values.
  syncComposerModelOptions();
  syncComposerFromSidebar();
  updateParamFieldStates();
  showCachedFilesPanel();
  showSessionsList();
  await loadChatHistory();
});

// ─── Test hook (Node only) ────────────────────────────────────────────────────
// Export pure helper functions so the Node test runner (`node --test`) can import
// and unit-test them. This block is a no-op in the browser: `module` is undefined
// there, so nothing leaks into the page and behavior is unchanged.
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    escapeHtml,
    renderMarkdown,
    extractJson,
    extractBalanced,
    formatUsage,
    getExcludedParams,
    MODEL_PARAM_EXCLUSIONS,
    buildResponseFormat,
    // Additional pure helpers exposed for unit testing (no browser effect):
    safeTrim,
    enforceStrictSchema,
    scoreChunkByKeywords,
    chunkText,
    normalizeAssistantText,
  };
}
