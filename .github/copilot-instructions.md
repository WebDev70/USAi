# Copilot Instructions for USAi Chat

This repository is a small static frontend and Python config server for a USAi-compatible chat UI.

## Key points

- The UI is served from `index.html` and loads configuration from `/config`.
- `server.py` serves the frontend and exposes the `.env` settings to `/config`.
- `app.js` contains frontend request logic and should be the primary place to edit chat behavior.
- `styles.css` contains the UI styling.
- `my_server.py` is an example Python MCP server, but is not currently connected to the frontend.

## What to edit

- Change UI layout or behavior in `index.html` and `app.js`.
- Change styling in `styles.css`.
- Change local config loading in `server.py`.

## What to avoid

- Do not commit secret API keys.
- Do not hardcode `API_KEY` or `BASE_URL` into `index.html`.
- Avoid adding unrelated build tooling; the project is intentionally static.

## Running locally

Start the local server and open the app at `http://localhost:8000`:

```bash
cd /Users/ronaldbblake/Documents/Dev/usai
python3 server.py
```

The UI will load env values from `/config` rather than requiring manual entry on the page.
