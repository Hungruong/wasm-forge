# WasmForge Backend

API server for running untrusted Python plugins inside a WasmEdge sandbox. Plugins can call AI models (via Ollama) but can't touch the network, filesystem, or run system commands.

> **Just want to use WasmForge?** If the backend is already running at `http://172.234.27.110:8000`, go to the [frontend README](../frontend/README.md) and run the React app. If the server is down, see "Starting the server" below.

## Starting the server

The backend is deployed on a Linode server. The `.env` with database credentials and config is already on the server — it's not in the repo (gitignored) so you don't need to create one unless deploying to a new server.

If the server is not running (check with `curl http://172.234.27.110:8000/health`), SSH in and start it:

```bash
ssh root@172.234.27.110
cd /root/wasmforge
source venv/bin/activate
source ~/.wasmedge/env
kill $(lsof -t -i:8000) 2>/dev/null    # free the port if something's stuck
uvicorn main:app --host 0.0.0.0 --port 8000
```

Keep this terminal open — closing it kills the server. If you want it to run in the background:

```bash
# option 1: systemd (already set up)
systemctl start wasmforge

# option 2: nohup (quick and dirty)
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
```

Ask the team for the SSH password if you don't have it.

## How it works

```
Frontend → FastAPI → bridge.py → WasmEdge (python.wasm) → plugin.py
                                      ↕ stdin/stdout
                                   Ollama (AI inference)
```

Plugins talk to the outside world through a bridge protocol over stdin/stdout. When a plugin calls `call_ai("mistral:latest", "summarize this")`, the bridge intercepts it, validates the request (allowed model? prompt too long? too many calls?), forwards it to Ollama, and pipes the response back. The plugin never knows where Ollama lives or how to reach it.

WasmEdge enforces the rest — no `subprocess`, no `socket`, no reading `/etc/passwd`. If you `import subprocess` inside the sandbox, you get `OSError: wasi does not support processes`. That's WASM doing its job.

On systems where WasmEdge isn't available (Windows, macOS), there's a Python-level fallback that blocks dangerous imports. Not as bulletproof, but good enough for development.

## Files

```
main.py           — FastAPI app, CORS, startup/shutdown
routes.py         — 6 API endpoints
bridge.py         — sandbox runner + bridge protocol
ollama.py         — Ollama HTTP client
database.py       — PostgreSQL CRUD (asyncpg, no ORM)
config.py         — reads .env
sdk/platform_sdk.py — injected into every plugin
```

## Running locally

Only needed if you want to run the backend on your own machine (for development). Otherwise just use the server.

Needs Python 3.10+, Ollama with at least one model pulled, and a PostgreSQL database.

```bash
# linux/mac
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env   # edit this
uvicorn main:app --host 0.0.0.0 --port 8000
```

```powershell
# windows
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy env.example .env   # edit this
uvicorn main:app --host 0.0.0.0 --port 8000
```

Set `USE_WASMEDGE=false` in `.env` on Windows/macOS — WasmEdge only runs on Linux.

## .env

Not in the repo. On the deployed server it's at `/root/wasmforge/.env`. For local dev, copy from template:

```bash
cp env.example .env
# fill in your DB credentials
```

Contents:
```
DB_HOST=172.239.42.137        # use IPv4, hostname resolves to IPv6 and times out
DB_PORT=17581
DB_NAME=defaultdb
DB_USER=akmadmin
DB_PASSWORD=...
DB_SSL_CERT=./certs/ca-certificate.crt

OLLAMA_BASE_URL=http://localhost:11434
ALLOWED_MODELS=mistral:latest,llama3.2:latest,gemma2:2b,qwen2.5:1.5b

SDK_PATH=./sdk/platform_sdk.py
MAX_EXECUTION_TIME=120
MAX_PROMPT_LENGTH=4000
MAX_AI_CALLS_PER_EXECUTION=10

USE_WASMEDGE=true
WASM_PYTHON_PATH=/opt/wasmedge-python/bin/python-3.11.1-wasmedge.wasm
WASM_PYTHON_DIR=/opt/wasmedge-python
```

`ALLOWED_MODELS` must match Ollama's exact names. Run `curl http://localhost:11434/api/tags` to check.

## API

Health:
- `GET /health` — server status, whether WasmEdge is on
- `GET /health/ollama` — Ollama connection, list of loaded models

Models:
- `GET /api/models/list` — models with availability and type info

Plugins:
- `GET /api/plugins/list` — all deployed plugins
- `GET /api/plugins/{name}/code` — source code of a plugin
- `POST /api/plugins/upload` — deploy a plugin (multipart: file + description + input_type + input_hint)
- `DELETE /api/plugins/{name}` — remove a plugin
- `POST /api/plugins/run` — execute a plugin (form: plugin_name + input_data)

Quick test:
```bash
# linux/mac
curl http://localhost:8000/health
curl http://localhost:8000/api/models/list

# windows
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/api/models/list
```

## Plugin SDK

Every plugin gets `platform_sdk.py` injected into its sandbox. Four functions:

```python
from platform_sdk import call_ai, get_input, send_output, list_models

text = get_input()                                    # read user input
result = call_ai("qwen2.5:1.5b", "Summarize: " + text)  # call AI
send_output(result)                                   # return to user
models = list_models()                                # what's available
```

That's it. No imports needed beyond `platform_sdk`. Anything else the plugin tries to import goes through the sandbox — if it's dangerous, it gets blocked.

## Security testing

Deploy these through the Builder UI and run them. They should all fail:

```python
# subprocess — blocked by WASM
import subprocess
subprocess.run(["cat", "/etc/shadow"])
```

```python
# network — blocked by WASM
import socket
s = socket.socket()
s.connect(("evil.com", 80))
```

```python
# filesystem — only sees sandbox dir, not host
import os
print(os.listdir("/"))   # returns ['bin', 'usr'], not the real root
```

A normal plugin using `call_ai()` should still work fine.

## Deploying to Linode

Upload files and run `deploy.sh`:

```bash
scp -r backend/* root@172.234.27.110:/root/wasmforge-src/
ssh root@172.234.27.110
cd /root/wasmforge-src && bash deploy.sh
```

The script installs everything (Ollama, WasmEdge, Python WASM, venv), prompts for DB credentials, tests the connection, sets up a systemd service, and runs a health check.

After that:
```bash
systemctl status wasmforge    # check status
journalctl -u wasmforge -f    # tail logs
systemctl restart wasmforge   # restart after code changes
```

## Gotchas

- **DB hostname times out.** Akamai's hostname resolves to IPv6 first, which hangs. Use the IPv4 address directly.
- **`curl` vs `curl.exe` on Windows.** PowerShell aliases `curl` to `Invoke-WebRequest`. Use `curl.exe` for the real thing.
- **Model names must be exact.** `mistral` won't match `mistral:latest`. Check `ollama list` for the real names.
- **Port 8000 already in use.** `kill $(lsof -t -i:8000)` on Linux, or just restart the terminal.
- **WasmEdge env not loaded.** Run `source ~/.wasmedge/env` or restart your shell.