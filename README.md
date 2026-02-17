# 🔌 WASM AI Plugin Platform

An open-source platform that lets developers write, deploy, and run AI-powered plugins securely inside WebAssembly sandboxes on Akamai Cloud.

**Developers write Python plugins → Platform compiles and runs them in WASM sandboxes → Plugins access GPU-accelerated AI models safely through a controlled bridge.**

---

## The Problem

Today, if a developer wants to run an AI workflow on the cloud, they must:

1. Rent and configure GPU servers
2. Install CUDA drivers, dependencies, and AI frameworks
3. Download and manage AI models
4. Write API servers from scratch
5. Handle security — one bad plugin can compromise the entire server
6. Manage scaling when traffic grows

Every developer repeats this process. It's slow, expensive, and insecure.

---

## Our Solution

We built a **plugin platform** with two layers:

- **Platform Layer (we build once):** GPU infrastructure, AI models, WASM sandboxes, API server — all hosted on Akamai Cloud.
- **Plugin Layer (developers build):** Small Python scripts that contain only business logic. Developers don't touch infrastructure.

Developers write a few lines of Python, upload to the platform, and their AI workflow is live — running securely in a WASM sandbox with access to GPU-accelerated models.

---

## Architecture

```
                         Internet
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│  Akamai Linode Instance 1 (Compute)                       │
│                                                           │
│  ┌─────────────┐    ┌──────────────────────────────────┐  │
│  │             │    │  WasmEdge Sandbox                │  │
│  │  Frontend   │    │  ┌─────────────────────────────┐ │  │
│  │  (React)    │    │  │  python.wasm                │ │  │
│  │  :3000      │    │  │  ┌───────────────────────┐  │ │  │
│  │             │    │  │  │  plugin.py            │  │ │  │
│  └──────┬──────┘    │  │  │  platform_sdk.py      │  │ │  │
│         │           │  │  │                       │  │ │  │
│         ▼           │  │  │  NO network access    │  │ │  │
│  ┌──────────────┐   │  │  │  NO filesystem access │  │ │  │
│  │              │   │  │  │  ONLY stdin/stdout    │  │ │  │
│  │  API Server  │   │  │  └──────┬────────────────┘  │ │  │
│  │  (FastAPI)   │◄──┼──┼─────────┘ stdin/stdout      │ │  │
│  │  :8000       │   │  │         bridge              │ │  │
│  │              │   │  └─────────────────────────────┘ │  │
│  │  - Validate  │   │                                  │  │
│  │  - Rate limit│   │                                  │  │
│  │  - Route AI  │   │                                  │  │
│  └──────┬───────┘   │                                  │  │
│         │           │                                  │  │
└─────────┼───────────┼──────────────────────────────────┘  │
          │ HTTP                                            │
          ▼                                                 │
┌────────────────────────────────────────────────────────┐  │
│  Akamai Linode Instance 2 (GPU)                        │  │
│                                                        │  │
│  Ollama :11434                                         │  │
│  ├── llama3   (text processing)                        │  │
│  ├── llava    (image understanding)                    │  │
│  └── mistral  (code analysis)                          │  │
│                                                        │  │
│  Firewall: accepts requests ONLY from Instance 1       │  │
└───────────────────────────────────────────────────────────┘
```

---

## How It Works

### For Developers (write plugins)

1. Open the web IDE on the platform
2. Write a Python plugin using our SDK:

```python
from platform_sdk import call_ai, get_input, send_output

text = get_input()
result = call_ai("llama3", "summarize this: " + text)
send_output(result)
```

3. Click **Deploy** — plugin is live

### For End Users (use plugins)

1. Open the Marketplace — browse available plugins
2. Select a plugin (e.g., "Text Summarizer")
3. Provide input, click **Run**
4. Receive AI-powered results in seconds

### What Happens Behind the Scenes

```
User clicks "Run"
    │
    ▼
API Server receives request
    │
    ▼
WasmEdge creates sandbox (NO network, NO filesystem)
    │
    ▼
python.wasm loads and runs plugin.py inside sandbox
    │
    ▼
Plugin calls call_ai() → sends request via stdout
    │
    ▼
API Server reads stdout → validates model, prompt, rate limit
    │
    ▼
API Server forwards to GPU Instance → Ollama runs inference
    │
    ▼
Result flows back: Ollama → API Server → stdin → plugin → stdout → User
```

---

## Security Model: stdin/stdout Bridge

Plugins run inside a **WASM sandbox with zero network access**. They communicate with the outside world exclusively through stdin/stdout, controlled by the API Server.

**Why not let plugins call HTTP directly?**

A malicious plugin could send user data to external servers, scan internal networks, or attack other services. Our stdin/stdout bridge eliminates this entirely — the sandbox has no network stack.

**Why not use WASM host functions?**

WasmEdge's Python SDK is still maturing. The stdin/stdout bridge achieves the same security guarantees with battle-tested subprocess I/O, making it reliable for production use.

**What the bridge controls:**
- Model validation — only approved models can be called
- Prompt length limits — prevents resource abuse
- Rate limiting — caps AI calls per plugin execution
- Request format validation — rejects malformed requests

```
Plugin CAN:                    Plugin CANNOT:
✅ Call approved AI models     ❌ Access the internet
✅ Process input data          ❌ Read server files
✅ Return results              ❌ Access other plugins' data
✅ Use Python standard lib     ❌ Execute system commands
                               ❌ Call unapproved endpoints
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Runtime | WasmEdge + python.wasm | Secure sandbox for plugins |
| API Server | Python + FastAPI | Request handling, plugin orchestration |
| AI Inference | Ollama | GPU-accelerated model serving |
| Frontend | React + Monaco Editor | Web IDE, marketplace, plugin runner |
| Infrastructure | Akamai Linode Compute | Cloud hosting |
| AI Models | Llama3, LLaVA, Mistral | Text, vision, code processing |

---

## Plugin SDK Reference

### Available Functions

```python
from platform_sdk import call_ai, get_input, send_output, list_models

call_ai(model, prompt)    # Call an AI model → returns string
get_input()               # Get user input → returns string
send_output(result)       # Return result to user
list_models()             # See available models → returns list
```

### Available Models

| Model | Type | Best For |
|-------|------|----------|
| `llama3` | Text | Summarization, translation, analysis, Q&A |
| `llava` | Vision | Image description, visual understanding |
| `mistral` | Code | Code review, bug detection, generation |

### Example: Simple Plugin

```python
from platform_sdk import call_ai, get_input, send_output

text = get_input()
result = call_ai("llama3", "Translate to Vietnamese: " + text)
send_output(result)
```

### Example: Complex Plugin (Multi-step AI Workflow)

```python
from platform_sdk import call_ai, get_input, send_output
import json

text = get_input()

# Step 1: AI analyzes content
analysis = call_ai("llama3",
    "Analyze this text for harmful content. Rate severity 0-10: " + text)

# Step 2: Pure logic (no AI needed)
score = 0
for word in analysis.split():
    try:
        score = float(word)
        break
    except:
        pass

if score > 7:
    decision = "BLOCKED"
elif score > 4:
    decision = "NEEDS REVIEW"
else:
    decision = "APPROVED"

# Step 3: AI writes report
report = call_ai("llama3",
    f"Write a moderation report. Content: {text}. Decision: {decision}")

send_output(json.dumps({
    "decision": decision,
    "score": score,
    "report": report
}, indent=2))
```

---

## Quick Start

### Prerequisites

- Akamai Cloud account with GPU instance
- Docker (optional)

### 1. Setup GPU Instance

```bash
ssh root@<gpu-instance-ip>
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
ollama pull llava
ollama pull mistral
```

### 2. Setup Platform Instance

```bash
ssh root@<platform-instance-ip>

# Install WasmEdge
curl -sSf https://raw.githubusercontent.com/WasmEdge/WasmEdge/master/utils/install.sh | bash

# Download python.wasm
wget -O /opt/python.wasm https://github.com/vmware-labs/webassembly-language-runtimes/releases/download/python-3.11.1%2B20230118-16d9bee/python-3.11.1-wasmedge.wasm

# Setup directories
mkdir -p /plugins /opt/sdk

# Install dependencies
pip3 install fastapi uvicorn python-multipart requests

# Start API server
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open in Browser

```
Frontend:  http://<platform-ip>:3000
API Docs:  http://<platform-ip>:8000/docs
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/models/list` | List available AI models |
| `GET` | `/api/plugins/list` | List all deployed plugins |
| `POST` | `/api/plugins/upload` | Upload a new plugin (.py file) |
| `POST` | `/api/plugins/run` | Run a plugin with input data |

### Run a plugin

```bash
curl -X POST http://localhost:8000/api/plugins/run \
  -F "plugin_name=summarize" \
  -F "input_data=Your long text here..."
```

---

## Project Structure

```
wasm-ai-platform/
├── README.md
├── docker-compose.yaml
│
├── backend/
│   ├── main.py                  # API Server + stdin/stdout bridge
│   ├── requirements.txt
│   ├── Dockerfile
│   └── sdk/
│       └── platform_sdk.py      # SDK for plugin developers
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Builder.jsx      # Web IDE with Monaco Editor
│   │   │   ├── Marketplace.jsx  # Plugin marketplace
│   │   │   ├── Runner.jsx       # Plugin execution UI
│   │   │   └── Models.jsx       # Available AI models
│   │   └── components/
│   │       └── Navbar.jsx
│   ├── package.json
│   └── Dockerfile
│
├── plugins/                     # Sample plugins
│   ├── summarize.py
│   ├── translate.py
│   ├── moderator.py
│   └── code_review.py
│
└── docs/
    ├── architecture.md
    └── plugin-guide.md
```

---

## Sample Plugins Included

| Plugin | Description | AI Calls | Complexity |
|--------|-------------|----------|------------|
| `summarize.py` | Summarize any text | 1 | Simple |
| `translate.py` | Translate text to Vietnamese | 1 | Simple |
| `moderator.py` | Content moderation with scoring | 3 | Complex |
| `code_review.py` | Find bugs, security issues, optimizations | 3 | Complex |

---

## Future Roadmap

- **Kubernetes (LKE):** Auto-scale plugin execution across multiple nodes
- **Model Registry:** Dynamic model management with versioning
- **Multi-language Plugins:** Support Rust, Go, JavaScript plugins alongside Python
- **Edge Deployment:** Run lightweight plugins on Akamai edge servers worldwide
- **Plugin Marketplace:** Rating, reviews, and plugin discovery
- **Real WASM Host Functions:** As WasmEdge Python SDK matures, migrate from stdin/stdout bridge to native host functions for lower latency

---

## Infrastructure

Hosted entirely on **Akamai Cloud Computing (Linode)**:

- **Compute Instance:** API Server + WasmEdge Runtime + Frontend
- **GPU Instance:** Ollama with Llama3, LLaVA, Mistral models

All components are open-source and self-hostable.

---

## Team

- [Name 1] — Backend, Infrastructure
- [Name 2] — Frontend, Plugins, Demo

---

## License

MIT

