#!/bin/bash
# WasmForge deploy script for Ubuntu (Linode/Akamai)
#
# Installs everything from scratch and starts the API as a systemd service.
# Run this on the server after uploading backend files.
#
#   scp -r backend/* root@your-server:/root/wasmforge-src/
#   ssh root@your-server
#   cd /root/wasmforge-src && bash deploy.sh

set -e

DEPLOY_DIR="/root/wasmforge"
WASM_DIR="/opt/wasmedge-python"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() { echo "[deploy] $1"; }
die() { echo "[deploy] ERROR: $1"; exit 1; }

echo ""
echo "WasmForge deploy"
echo "================"
echo ""

# --- check files exist ---

for f in main.py routes.py bridge.py ollama.py database.py config.py requirements.txt; do
    [ -f "${SCRIPT_DIR}/${f}" ] || die "missing ${f} — upload backend files first"
done
[ -f "${SCRIPT_DIR}/sdk/platform_sdk.py" ] || die "missing sdk/platform_sdk.py"
log "files ok"

# --- system packages ---

log "installing packages..."
apt update -qq 2>/dev/null
apt install -y -qq python3 python3-pip python3-venv curl unzip lsof > /dev/null 2>&1

# --- ollama ---

log "setting up ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    nohup ollama serve > /dev/null 2>&1 &
    sleep 5
fi
curl -s http://localhost:11434/api/tags > /dev/null 2>&1 || die "ollama won't start"

for model in mistral:latest qwen2.5:1.5b gemma2:2b llama3.2:latest; do
    if ! ollama list 2>/dev/null | grep -q "$(echo ${model} | cut -d: -f1)"; then
        log "pulling ${model}..."
        ollama pull "${model}"
    fi
done

# figure out what ollama actually has (names must match exactly)
DETECTED_MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(','.join(m['name'] for m in d.get('models',[])))
" 2>/dev/null || echo "mistral:latest,qwen2.5:1.5b,gemma2:2b,llama3.2:latest")
log "models: ${DETECTED_MODELS}"

# --- wasmedge ---

log "setting up wasmedge..."
if [ -f "$HOME/.wasmedge/bin/wasmedge" ]; then
    source "$HOME/.wasmedge/env" 2>/dev/null
else
    curl -sSf https://raw.githubusercontent.com/WasmEdge/WasmEdge/master/utils/install_v2.sh | bash
    source "$HOME/.wasmedge/env"
fi

# persist across sessions
grep -q "wasmedge/env" "$HOME/.bashrc" 2>/dev/null || echo 'source $HOME/.wasmedge/env 2>/dev/null' >> "$HOME/.bashrc"

# python wasm runtime (~11MB)
USE_WASM="false"
if [ ! -f "${WASM_DIR}/bin/python-3.11.1-wasmedge.wasm" ]; then
    mkdir -p "${WASM_DIR}" && cd "${WASM_DIR}"
    curl -L -o python-aio.zip \
        "https://github.com/vmware-labs/webassembly-language-runtimes/releases/download/python/3.11.1%2B20230127-c8036b4/python-aio-3.11.1.zip"
    SIZE=$(stat -c%s python-aio.zip 2>/dev/null || echo 0)
    if [ "$SIZE" -lt 1000000 ]; then
        log "python.wasm download failed, will use python sandbox"
        rm -f python-aio.zip
    else
        unzip -o python-aio.zip && rm -f python-aio.zip
    fi
fi

# quick sanity check
if [ -f "${WASM_DIR}/bin/python-3.11.1-wasmedge.wasm" ]; then
    echo 'print("ok")' > /tmp/_wt.py
    R=$(wasmedge --dir "/":"${WASM_DIR}" --dir /tmp:/tmp "${WASM_DIR}/bin/python-3.11.1-wasmedge.wasm" /tmp/_wt.py 2>/dev/null || echo "")
    rm -f /tmp/_wt.py
    if [ "$R" = "ok" ]; then
        USE_WASM="true"
        log "wasmedge sandbox working"
    else
        log "wasmedge test failed, falling back to python sandbox"
    fi
fi

# --- copy files ---

log "copying files to ${DEPLOY_DIR}..."
mkdir -p "${DEPLOY_DIR}/sdk" "${DEPLOY_DIR}/certs"
for f in main.py routes.py bridge.py ollama.py database.py config.py requirements.txt; do
    cp "${SCRIPT_DIR}/${f}" "${DEPLOY_DIR}/"
done
cp "${SCRIPT_DIR}/sdk/platform_sdk.py" "${DEPLOY_DIR}/sdk/"

if [ -f "${SCRIPT_DIR}/certs/ca-certificate.crt" ]; then
    cp "${SCRIPT_DIR}/certs/ca-certificate.crt" "${DEPLOY_DIR}/certs/"
else
    log "WARNING: no SSL cert found at certs/ca-certificate.crt"
    log "  download from akamai dashboard -> database -> connection details"
fi

# --- .env ---

if [ -f "${DEPLOY_DIR}/.env" ]; then
    log ".env exists, updating model list and wasmedge config..."
    sed -i "s/ALLOWED_MODELS=.*/ALLOWED_MODELS=${DETECTED_MODELS}/" "${DEPLOY_DIR}/.env"
    sed -i "s/USE_WASMEDGE=.*/USE_WASMEDGE=${USE_WASM}/" "${DEPLOY_DIR}/.env"
    grep -q "WASM_PYTHON_PATH" "${DEPLOY_DIR}/.env" || {
        echo "WASM_PYTHON_PATH=${WASM_DIR}/bin/python-3.11.1-wasmedge.wasm" >> "${DEPLOY_DIR}/.env"
        echo "WASM_PYTHON_DIR=${WASM_DIR}" >> "${DEPLOY_DIR}/.env"
    }
else
    echo ""
    echo "Need database credentials (from Akamai dashboard)."
    echo "Use the IPv4 address for host, NOT the hostname — hostname resolves"
    echo "to IPv6 first which causes connection timeouts."
    echo ""
    read -rp "DB host (IPv4): " DB_HOST
    [ -z "$DB_HOST" ] && die "db host required"
    read -rp "DB port [17581]: " DB_PORT; DB_PORT=${DB_PORT:-17581}
    read -rp "DB name [defaultdb]: " DB_NAME; DB_NAME=${DB_NAME:-defaultdb}
    read -rp "DB user [akmadmin]: " DB_USER; DB_USER=${DB_USER:-akmadmin}
    read -rsp "DB password: " DB_PASSWORD; echo ""
    [ -z "$DB_PASSWORD" ] && die "password required"

    cat > "${DEPLOY_DIR}/.env" << EOF
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_SSL_CERT=./certs/ca-certificate.crt

OLLAMA_BASE_URL=http://localhost:11434
ALLOWED_MODELS=${DETECTED_MODELS}

SDK_PATH=./sdk/platform_sdk.py
MAX_EXECUTION_TIME=120
MAX_PROMPT_LENGTH=4000
MAX_AI_CALLS_PER_EXECUTION=10

USE_WASMEDGE=${USE_WASM}
WASM_PYTHON_PATH=${WASM_DIR}/bin/python-3.11.1-wasmedge.wasm
WASM_PYTHON_DIR=${WASM_DIR}
EOF
    log ".env created"
fi

# --- python venv ---

log "setting up python..."
cd "${DEPLOY_DIR}"
[ -d "venv" ] || python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q 2>/dev/null
pip install -r requirements.txt -q 2>/dev/null

# --- test db connection ---

log "testing database connection..."
DB_OK=$(python3 -c "
import asyncio,ssl,asyncpg,os
from dotenv import load_dotenv
load_dotenv()
async def t():
    try:
        ctx=ssl.create_default_context(cafile=os.getenv('DB_SSL_CERT',''))
        c=await asyncio.wait_for(asyncpg.connect(
            host=os.getenv('DB_HOST'),port=int(os.getenv('DB_PORT',17581)),
            database=os.getenv('DB_NAME'),user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),ssl=ctx),timeout=10)
        await c.close(); print('ok')
    except Exception as e: print(f'fail:{e}')
asyncio.run(t())
" 2>/dev/null)

if [ "$DB_OK" != "ok" ]; then
    die "database connection failed: $(echo $DB_OK | cut -d: -f2-)
  check DB_HOST is ipv4, password is correct, cert exists, firewall allows outbound ${DB_PORT}"
fi
log "database ok"

# --- systemd ---

log "setting up service..."
lsof -t -i:8000 > /dev/null 2>&1 && kill $(lsof -t -i:8000) 2>/dev/null && sleep 2

cat > /etc/systemd/system/wasmforge.service << EOF
[Unit]
Description=WasmForge API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${DEPLOY_DIR}
Environment=PATH=${DEPLOY_DIR}/venv/bin:/root/.wasmedge/bin:/usr/local/bin:/usr/bin:/bin
Environment=LD_LIBRARY_PATH=/root/.wasmedge/lib
ExecStart=${DEPLOY_DIR}/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wasmforge > /dev/null 2>&1
systemctl restart wasmforge

# --- wait for it ---

log "waiting for api..."
for i in $(seq 1 15); do
    curl -s http://localhost:8000/health > /dev/null 2>&1 && break
    sleep 1
done

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo "done. api running at http://${IP}:8000"
    echo ""
    echo "  wasmedge:  ${USE_WASM}"
    echo "  models:    ${DETECTED_MODELS}"
    echo ""
    echo "  endpoints:"
    echo "    http://${IP}:8000/health"
    echo "    http://${IP}:8000/api/models/list"
    echo "    http://${IP}:8000/api/plugins/list"
    echo ""
    echo "  manage:"
    echo "    systemctl status wasmforge"
    echo "    journalctl -u wasmforge -f"
    echo "    systemctl restart wasmforge"
    echo ""
    echo "  frontend: set API_URL=\"http://${IP}:8000\" in src/api/api.js"
    echo ""
else
    die "api didn't start. check: journalctl -u wasmforge --no-pager -n 30"
fi