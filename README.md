# WasmForge

A platform for running AI-powered Python plugins inside WebAssembly sandboxes. Developers write small Python scripts using a simple SDK, deploy them through a web UI, and users run them — all without touching infrastructure.

Plugins run inside WasmEdge (a WASM runtime) so they can't access the network, filesystem, or anything outside their sandbox. AI model access goes through a stdin/stdout bridge that the platform controls.

Built for the Akamai hackathon.

## Quick start

**Frontend only** (backend already deployed):

```bash
git clone https://github.com/Hungruong/wasm-forge
cd wasm-forge/frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend talks to the backend at `172.234.27.110:8000`.

If models or plugins don't load, the backend might be down — see the [backend README](backend/README.md) for how to restart it (one SSH command).

**Requirements:** Node.js 18+

## What it does

1. Developer opens the **Builder** (browser code editor), writes a plugin using the SDK:

```python
from platform_sdk import call_ai, get_input, send_output

text = get_input()
result = call_ai("qwen2.5:1.5b", "Summarize: " + text)
send_output(result)
```

2. Clicks **Deploy** — plugin goes to PostgreSQL and shows up in the marketplace.

3. User opens the **Runner**, picks a plugin, types input, clicks **Run**. The backend spins up a WasmEdge sandbox, executes the plugin, brokers AI calls through Ollama, and returns the result.

## How the sandbox works

```
User clicks Run
      │
      ▼
  FastAPI receives request
      │
      ▼
  bridge.py creates temp dir, writes plugin + SDK
      │
      ▼
  WasmEdge spawns python.wasm in sandbox
  (no network, no filesystem, no subprocess)
      │
      ▼
  Plugin calls call_ai() → JSON over stdout → bridge reads it
      │
      ▼
  bridge.py validates model/prompt → forwards to Ollama → pipes response back via stdin
      │
      ▼
  Plugin calls send_output() → result flows back to user
```

Plugins communicate with the outside world **only** through stdin/stdout. WasmEdge enforces this at the WASM level — there's no network stack inside the sandbox. If a plugin tries `import socket` or `import subprocess`, it gets an `OSError`.

On systems where WasmEdge isn't available (Windows, macOS), there's a Python-level fallback that blocks dangerous imports. Good enough for development, not for production.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Linode Instance (172.234.27.110)                       │
│                                                         │
│  Frontend (React/Vite)     API Server (FastAPI :8000)   │
│  localhost:5173        ──► routes.py                    │
│                              │                          │
│                              ▼                          │
│                           bridge.py                     │
│                              │                          │
│                    ┌─────────┴──────────┐               │
│                    ▼                    ▼               │
│              WasmEdge sandbox     Ollama :11434         │
│              python.wasm          ├─ mistral:latest     │
│              plugin.py            ├─ qwen2.5:1.5b       │
│              platform_sdk.py      ├─ gemma2:2b          │
│                                   └─ llama3.2:latest    │
│                                                         │
│  PostgreSQL (Akamai managed, 172.239.42.137:17581)      │
└─────────────────────────────────────────────────────────┘
```

Frontend runs locally on the developer's machine. Backend + Ollama + WasmEdge all run on one Linode instance. Database is Akamai's managed PostgreSQL.

## Project structure

```
wasm-forge/
├── README.md                ← you're here
├── backend/
│   ├── main.py              — FastAPI app, CORS, startup/shutdown
│   ├── routes.py            — API endpoints (models, plugins, run)
│   ├── bridge.py            — sandbox runner + stdin/stdout bridge
│   ├── ollama.py            — Ollama HTTP client
│   ├── database.py          — PostgreSQL CRUD (asyncpg)
│   ├── config.py            — reads .env
│   ├── deploy.sh            — full server setup script
│   ├── requirements.txt
│   ├── env.example
│   └── sdk/
│       └── platform_sdk.py  — injected into every plugin
└── frontend/
    ├── src/
    │   ├── App.jsx          — routing
    │   ├── api/
    │   │   ├── api.js       — all backend calls
    │   │   └── mock.js      — offline dev data
    │   ├── components/
    │   │   └── Navbar.jsx
    │   └── pages/
    │       ├── Landing.jsx  — homepage
    │       ├── Builder.jsx  — code editor + deploy form
    │       ├── Marketplace.jsx — plugin list
    │       ├── Runner.jsx   — execute plugins
    │       └── Models.jsx   — AI model status
    ├── package.json
    └── vite.config.js
```

## Plugin SDK

Every plugin gets `platform_sdk.py` injected. Four functions:

```python
from platform_sdk import call_ai, get_input, send_output, list_models

text = get_input()                              # read user input
result = call_ai("qwen2.5:1.5b", "..." + text) # call AI model
send_output(result)                             # return to user
models = list_models()                          # what's available
```

Available models (exact names — must match Ollama):

- `mistral:latest` — code review, generation, debugging
- `qwen2.5:1.5b` — multilingual text processing
- `gemma2:2b` — lightweight text generation
- `llama3.2:latest` — summarization, translation, Q&A

## API

Base URL: `http://172.234.27.110:8000`

- `GET /health` — server status
- `GET /health/ollama` — Ollama connection + loaded models
- `GET /api/models/list` — models with availability info
- `GET /api/plugins/list` — all deployed plugins
- `GET /api/plugins/{name}/code` — plugin source code
- `POST /api/plugins/upload` — deploy a plugin (multipart form)
- `DELETE /api/plugins/{name}` — remove a plugin
- `POST /api/plugins/run` — execute a plugin (form: plugin_name + input_data)

## Security model

What plugins **can** do: call approved AI models, process input data, return results, use Python standard library.

What plugins **cannot** do: access the internet, read server files, access other plugins' data, execute system commands, call unapproved models, exceed prompt length or call limits.

The bridge enforces: model validation, prompt length limits (4000 chars), rate limiting (10 AI calls per execution), execution timeout (120s).

## Deploying the backend

If you need to deploy to a new server:

```bash
scp -r backend/* root@your-server:/root/wasmforge-src/
ssh root@your-server
cd /root/wasmforge-src && bash deploy.sh
```

`deploy.sh` handles everything: installs Ollama + models, WasmEdge + python.wasm, creates venv, prompts for DB credentials, tests the connection, sets up systemd. See the [backend README](backend/README.md) for details.

## Tech stack

- **Sandbox:** WasmEdge + python.wasm (Python 3.11 compiled to WASM)
- **Backend:** Python, FastAPI, asyncpg
- **AI inference:** Ollama (local, same server)
- **Frontend:** React 19, Vite, Monaco Editor
- **Database:** PostgreSQL (Akamai managed)
- **Hosting:** Akamai Linode

## Team

- Hung Truong
- Nhan Ngo

## License

MIT
