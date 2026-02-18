#!/bin/bash
# WASM AI Platform - Runtime Setup
# Prerequisites: Ubuntu 22.04+, non-root user
# Usage: chmod +x setup-runtime.sh && ./setup-runtime.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo "  $1"; }

echo ""
echo "WASM AI Platform - Runtime Setup"
echo "---------------------------------"
echo ""

# Safety check
[[ $EUID -eq 0 ]] && err "Do not run as root. Use a regular sudo-enabled user."

source /etc/os-release
info "OS: $PRETTY_NAME | User: $USER"
echo ""
read -p "Continue? (y/n) " -n 1 -r; echo
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
echo ""

START_TIME=$(date +%s)

# ── Step 1: System Dependencies ──────────────────────────────────────────────

echo "[ 1/5 ] System dependencies"
sudo apt update -qq
sudo apt install -y curl wget git build-essential unzip python3 python3-pip python3-venv > /dev/null 2>&1
ok "Done"
echo ""

# ── Step 2: WasmEdge ─────────────────────────────────────────────────────────

echo "[ 2/5 ] WasmEdge runtime"

if command -v wasmedge &> /dev/null; then
    warn "Already installed: $(wasmedge --version 2>&1 | head -n1)"
else
    curl -sSf https://raw.githubusercontent.com/WasmEdge/WasmEdge/master/utils/install.sh | bash -s -- -v 0.13.5 > /dev/null 2>&1
    ok "Installed"
fi

export WASMEDGE_DIR="$HOME/.wasmedge"
export PATH="$WASMEDGE_DIR/bin:$PATH"
source "$HOME/.wasmedge/env" 2>/dev/null || true

if ! grep -q "wasmedge/env" ~/.bashrc 2>/dev/null; then
    echo '' >> ~/.bashrc
    echo '# WasmEdge' >> ~/.bashrc
    echo 'source $HOME/.wasmedge/env' >> ~/.bashrc
fi

command -v wasmedge &> /dev/null || err "WasmEdge install failed. Try: source ~/.wasmedge/env"
ok "WasmEdge ready: $(wasmedge --version 2>&1 | head -n1)"
echo ""

# ── Step 3: Python WASM Binary ───────────────────────────────────────────────

echo "[ 3/5 ] Python 3.11.1 WASM binary"

PYTHON_WASM_DIR="/opt/wasmedge-python"

if [[ -f "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" ]]; then
    warn "Already exists ($(du -h "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" | cut -f1))"
else
    sudo mkdir -p "$PYTHON_WASM_DIR"
    sudo chown -R $USER:$USER "$PYTHON_WASM_DIR"
    cd "$PYTHON_WASM_DIR"
    info "Downloading (~100MB, may take a few minutes)..."
    wget -q --show-progress https://github.com/vmware-labs/webassembly-language-runtimes/releases/download/python%2F3.11.1%2B20230127-c8036b4/python-aio-3.11.1.zip
    unzip -q python-aio-3.11.1.zip
    rm python-aio-3.11.1.zip
    ok "Extracted"
fi

[[ ! -f "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" ]] && err "Python WASM binary not found at $PYTHON_WASM_DIR/bin/"
ok "Python WASM ready ($(du -h "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" | cut -f1))"
echo ""

# ── Step 4: AOT Compilation ──────────────────────────────────────────────────

echo "[ 4/5 ] AOT compilation (3-5 minutes)"

AOT_BINARY="$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge-aot.wasm"

if [[ -f "$AOT_BINARY" ]]; then
    warn "Already compiled ($(du -h "$AOT_BINARY" | cut -f1))"
else
    wasmedge compile \
        "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" \
        "$AOT_BINARY" &

    COMPILE_PID=$!
    SPIN='/-\|'
    i=0
    while kill -0 $COMPILE_PID 2>/dev/null; do
        printf "\r  [%s] Compiling..." "${SPIN:$((i % 4)):1}"
        sleep 0.2
        ((i++))
    done
    wait $COMPILE_PID
    printf "\r\033[K"
    ok "Compilation complete"
fi

ok "AOT binary: $(du -h "$AOT_BINARY" | cut -f1)"
echo ""

# ── Step 5: Verification ─────────────────────────────────────────────────────

echo "[ 5/5 ] Verifying installation"

# Create temp workspace for test
TEMP_DIR=$(mktemp -d)
TEST_FILE="$TEMP_DIR/test.py"

cat > "$TEST_FILE" << 'EOF'
import sys
result = 5 + 3 * 2
squares = [x**2 for x in range(5)]
print(f"Python {sys.version.split()[0]} | math={result} | squares={squares}")
print("OK")
EOF

OUTPUT=$(wasmedge \
    --dir /python:$PYTHON_WASM_DIR \
    --dir /workspace:$TEMP_DIR \
    --env PYTHONHOME=/python/usr/local \
    "$AOT_BINARY" \
    /workspace/test.py 2>&1)

# Clean up temp files
rm -rf "$TEMP_DIR"

if echo "$OUTPUT" | grep -q "OK"; then
    ok "Test passed: $OUTPUT"
else
    err "Test failed: $OUTPUT"
fi
echo ""

# ── Helper Script ─────────────────────────────────────────────────────────────

# Determine project root (git repo or cwd)
if git rev-parse --git-dir > /dev/null 2>&1; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
else
    PROJECT_ROOT="$(pwd)"
fi

cat > "$PROJECT_ROOT/run-plugin.sh" << SCRIPT
#!/bin/bash
# Run a Python plugin in WasmEdge sandbox
# Usage: ./run-plugin.sh <script.py>

[[ -z "\$1" ]] && { echo "Usage: ./run-plugin.sh <script.py>"; exit 1; }
[[ ! -f "\$1" ]] && { echo "File not found: \$1"; exit 1; }

SCRIPT_PATH="\$(realpath "\$1")"
SCRIPT_DIR="\$(dirname "\$SCRIPT_PATH")"
SCRIPT_NAME="\$(basename "\$SCRIPT_PATH")"

wasmedge \\
    --dir /python:$PYTHON_WASM_DIR \\
    --dir /workspace:\$SCRIPT_DIR \\
    --env PYTHONHOME=/python/usr/local \\
    $AOT_BINARY \\
    /workspace/"\$SCRIPT_NAME"
SCRIPT
chmod +x "$PROJECT_ROOT/run-plugin.sh"
ok "Created: run-plugin.sh"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "---------------------------------"
ok "Setup complete in $((DURATION / 60))m $((DURATION % 60))s"
echo ""
info "WasmEdge:    $(wasmedge --version 2>&1 | head -n1)"
info "Python WASM: $AOT_BINARY"
info "Run helper:  ./run-plugin.sh <script.py>"
echo ""
warn "Reload shell or run: source ~/.wasmedge/env"
echo ""
