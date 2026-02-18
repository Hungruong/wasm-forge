!/bin/bash
################################################################################
# WASM AI Platform - Complete Platform Setup Script
# 
# Sets up WasmEdge + Python WASM for running Python programs in sandbox
#
# Prerequisites: Ubuntu 22.04+ (Linode instance) as non-root user
# Usage: chmod +x setup-complete.sh && ./setup-complete.sh
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓ SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[! WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[✗ ERROR]${NC} $1"; }

# Banner
clear
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           ${GREEN}WASM AI Platform - Complete Setup${CYAN}                ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Safety checks
if [[ $EUID -eq 0 ]]; then
   log_error "Don't run this script as root/sudo"
   log_info "Create a regular user: adduser myuser && usermod -aG sudo myuser"
   exit 1
fi

source /etc/os-release
log_info "OS: $PRETTY_NAME | User: $USER"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 0

START_TIME=$(date +%s)

################################################################################
# STEP 1: System Dependencies
################################################################################

log_step "STEP 1/7: Installing System Dependencies"

log_info "Updating package lists..."
sudo apt update -qq

log_info "Installing required packages..."
sudo apt install -y curl wget git build-essential unzip python3 python3-pip python3-venv > /dev/null 2>&1

log_success "System dependencies installed"

################################################################################
# STEP 2: WasmEdge Runtime
################################################################################

log_step "STEP 2/7: Installing WasmEdge Runtime"

if command -v wasmedge &> /dev/null; then
    log_warning "WasmEdge already installed: $(wasmedge --version 2>&1 | head -n1)"
else
    log_info "Installing WasmEdge 0.13.5..."
    curl -sSf https://raw.githubusercontent.com/WasmEdge/WasmEdge/master/utils/install.sh | bash -s -- -v 0.13.5 > /dev/null 2>&1
    log_success "WasmEdge installed"
fi

export WASMEDGE_DIR="$HOME/.wasmedge"
export PATH="$WASMEDGE_DIR/bin:$PATH"
source "$HOME/.wasmedge/env" 2>/dev/null || true

if ! grep -q "wasmedge/env" ~/.bashrc 2>/dev/null; then
    echo '' >> ~/.bashrc
    echo '# WasmEdge Runtime' >> ~/.bashrc
    echo 'source $HOME/.wasmedge/env' >> ~/.bashrc
fi

if command -v wasmedge &> /dev/null; then
    log_success "WasmEdge ready: $(wasmedge --version 2>&1 | head -n1)"
else
    log_error "WasmEdge installation failed. Try: source ~/.wasmedge/env"
    exit 1
fi

################################################################################
# STEP 3: Python WebAssembly Binary
################################################################################

log_step "STEP 3/7: Downloading Python 3.11.1 WebAssembly Binary"

PYTHON_WASM_DIR="/opt/wasmedge-python"

if [[ -f "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" ]]; then
    log_warning "Python WASM already exists ($(du -h "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" | cut -f1))"
else
    log_info "Creating $PYTHON_WASM_DIR..."
    sudo mkdir -p "$PYTHON_WASM_DIR"
    sudo chown -R $USER:$USER "$PYTHON_WASM_DIR"
    
    cd "$PYTHON_WASM_DIR"
    log_info "Downloading (~100MB, may take 2-5 min)..."
    wget -q --show-progress https://github.com/vmware-labs/webassembly-language-runtimes/releases/download/python%2F3.11.1%2B20230127-c8036b4/python-aio-3.11.1.zip
    
    log_info "Extracting..."
    unzip -q python-aio-3.11.1.zip
    rm python-aio-3.11.1.zip
    
    log_success "Python WASM extracted"
fi

if [[ ! -f "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" ]]; then
    log_error "Python WASM binary not found at $PYTHON_WASM_DIR/bin/"
    exit 1
fi

log_success "Python WASM ready: $(du -h "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" | cut -f1)"

################################################################################
# STEP 4: AOT Compilation
################################################################################

log_step "STEP 4/7: AOT Compiling Python Binary (3-5 minutes)"

AOT_BINARY="$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge-aot.wasm"

if [[ -f "$AOT_BINARY" ]]; then
    log_warning "AOT binary exists ($(du -h "$AOT_BINARY" | cut -f1))"
else
    log_info "Compiling..."
    
    wasmedge compile \
        "$PYTHON_WASM_DIR/bin/python-3.11.1-wasmedge.wasm" \
        "$AOT_BINARY" &
    
    COMPILE_PID=$!
    while kill -0 $COMPILE_PID 2>/dev/null; do
        for s in / - \\ \|; do
            printf "\r  [%s] Compiling..." "$s"
            sleep 0.2
        done
    done
    wait $COMPILE_PID
    printf "\r\033[K"
    
    log_success "AOT compilation complete"
fi

log_success "AOT binary: $(du -h "$AOT_BINARY" | cut -f1)"

################################################################################
# STEP 5: Test Python Execution
################################################################################

log_step "STEP 5/7: Testing Python Execution in WasmEdge"

# Create test script
TEST_FILE="$HOME/wasmedge_test_$$.py"
cat > "$TEST_FILE" << 'EOF'
print("=" * 50)
print("Python in WasmEdge Test")
print("=" * 50)

import sys
print(f"Python: {sys.version}")

result = 5 + 3 * 2
squares = [x**2 for x in range(5)]

print(f"Math: 5 + 3 * 2 = {result}")
print(f"List: {squares}")
print("\n✓ Test passed!")
EOF

log_info "Running test..."
echo ""

# Mount both Python dir and home dir
if wasmedge \
    --dir /python:$PYTHON_WASM_DIR \
    --dir /workspace:$HOME \
    --env PYTHONHOME=/python/usr/local \
    "$AOT_BINARY" \
    "/workspace/$(basename $TEST_FILE)" 2>&1; then
    echo ""
    log_success "Python execution works!"
else
    log_error "Test failed"
    rm -f "$TEST_FILE"
    exit 1
fi

rm -f "$TEST_FILE"

################################################################################
# STEP 6: Project Structure & Dependencies
################################################################################

log_step "STEP 6/7: Setting Up Project"

# Determine project root
if git rev-parse --git-dir > /dev/null 2>&1; then
    PROJECT_ROOT=$(git rev-parse --show-toplevel)
    log_info "Git repo: $PROJECT_ROOT"
else
    PROJECT_ROOT="$HOME/wasm-ai-platform"
    mkdir -p "$PROJECT_ROOT"
    log_info "New project: $PROJECT_ROOT"
fi

cd "$PROJECT_ROOT"

# Create directories
for dir in backend backend/sdk plugins/examples plugins/deployed frontend docs tests; do
    mkdir -p "$dir"
done
log_success "Project structure created"

# Python virtual environment
if [[ ! -d "venv" ]]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Requirements
cat > backend/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
httpx==0.26.0
pydantic==2.5.3
python-dotenv==1.0.0
pytest==7.4.4
EOF

log_info "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

log_success "Python dependencies installed"

# Configuration
cat > backend/.env << EOF
OLLAMA_BASE_URL=http://localhost:11434
WASM_PYTHON_PATH=$AOT_BINARY
WASM_PYTHON_DIR=$PYTHON_WASM_DIR
PLUGINS_DIR=$PROJECT_ROOT/plugins/deployed
SDK_PATH=$PROJECT_ROOT/backend/sdk/platform_sdk.py
MAX_EXECUTION_TIME=30
MAX_PROMPT_LENGTH=4000
MAX_AI_CALLS_PER_EXECUTION=10
ALLOWED_MODELS=llama3,llava,mistral
API_HOST=0.0.0.0
API_PORT=8000
EOF

log_success "Configuration: backend/.env"

################################################################################
# STEP 7: Helper Scripts & Documentation
################################################################################

log_step "STEP 7/7: Creating Helper Scripts"

# Run script with proper mounting
cat > "$PROJECT_ROOT/run-python-wasm.sh" << 'SCRIPT'
#!/bin/bash
# Run Python scripts in WasmEdge sandbox
# Usage: ./run-python-wasm.sh <script.py>

if [ -z "$1" ]; then
    echo "Usage: ./run-python-wasm.sh <script.py>"
    exit 1
fi

SCRIPT_FILE="$1"
if [ ! -f "$SCRIPT_FILE" ]; then
    echo "Error: File not found: $SCRIPT_FILE"
    exit 1
fi

# Get absolute paths
SCRIPT_PATH="$(realpath "$SCRIPT_FILE")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
SCRIPT_NAME="$(basename "$SCRIPT_PATH")"

# Paths from setup
WASM_PYTHON="__AOT_BINARY__"
PYTHON_DIR="__PYTHON_DIR__"

# Run with proper directory mounts
wasmedge \
    --dir /python:$PYTHON_DIR \
    --dir /workspace:$SCRIPT_DIR \
    --env PYTHONHOME=/python/usr/local \
    "$WASM_PYTHON" \
    /workspace/"$SCRIPT_NAME"
SCRIPT

# Replace placeholders
sed -i "s|__AOT_BINARY__|$AOT_BINARY|g" "$PROJECT_ROOT/run-python-wasm.sh"
sed -i "s|__PYTHON_DIR__|$PYTHON_WASM_DIR|g" "$PROJECT_ROOT/run-python-wasm.sh"
chmod +x "$PROJECT_ROOT/run-python-wasm.sh"

log_success "Helper: run-python-wasm.sh"

# Test plugin
cat > plugins/examples/hello_world.py << 'EOF'
#!/usr/bin/env python3
"""
Hello World Plugin - Minimal Example
Demonstrates Python execution in WasmEdge sandbox
"""

print("=" * 60)
print("Hello from WasmEdge Python!")
print("=" * 60)
print()

import sys
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print()

# Test basic operations
numbers = [1, 2, 3, 4, 5]
squares = [n**2 for n in numbers]
print(f"Input: {numbers}")
print(f"Squares: {squares}")
print()

# Test function
def calculate_sum(items):
    return sum(items)

total = calculate_sum(squares)
print(f"Sum of squares: {total}")
print()

print("✓ Plugin execution successful!")
print("✓ Ready for AI enhancement!")
EOF

log_success "Plugin: plugins/examples/hello_world.py"

# Quick start guide
cat > QUICK_START.md << EOF
# Quick Start Guide

## ✨ Installation Complete!

Everything is ready to run Python in WasmEdge.

## Quick Test

\`\`\`bash
cd $PROJECT_ROOT
./run-python-wasm.sh plugins/examples/hello_world.py
\`\`\`

You should see:
\`\`\`
============================================================
Hello from WasmEdge Python!
============================================================
...
✓ Plugin execution successful!
\`\`\`

## Running Your Own Scripts

\`\`\`bash
# Easy way (recommended):
./run-python-wasm.sh your_script.py

# Manual way:
wasmedge \\
    --dir /python:$PYTHON_WASM_DIR \\
    --dir /workspace:\$(dirname \$(realpath your_script.py)) \\
    --env PYTHONHOME=/python/usr/local \\
    $AOT_BINARY \\
    /workspace/\$(basename your_script.py)
\`\`\`

## Important Notes

### Directory Mounting
- Python stdlib is at: \`/python\`
- Your script dir is at: \`/workspace\`
- Scripts can only access files in mounted directories

### Python Limitations in WASM
- ✅ All stdlib modules work
- ✅ Pure Python code works perfectly
- ❌ No pip install (stdlib only)
- ❌ No native extensions (C/C++ modules)
- ❌ No network access (by design - security)
- ❌ No filesystem access outside mounted dirs

## Next Steps

### 1. Activate Virtual Environment
\`\`\`bash
cd $PROJECT_ROOT
source venv/bin/activate
\`\`\`

### 2. Update Ollama Configuration
Edit \`backend/.env\` with your GPU instance IP:
\`\`\`bash
nano backend/.env
# Change: OLLAMA_BASE_URL=http://YOUR_GPU_IP:11434
\`\`\`

### 3. Implement the SDK
Create \`backend/sdk/platform_sdk.py\` with:
- \`call_ai(model, prompt)\` - Call AI models
- \`get_input()\` - Get user input
- \`send_output(data)\` - Return results
- \`list_models()\` - List available models

### 4. Implement the API Server
Create \`backend/main.py\` with FastAPI endpoints

### 5. Build the Frontend
Create React app in \`frontend/\`

## Key Paths
- **Python WASM:** $AOT_BINARY
- **Python stdlib:** $PYTHON_WASM_DIR
- **Project:** $PROJECT_ROOT
- **Config:** backend/.env
- **Plugins:** plugins/examples/

## Troubleshooting

### "can't open file" error
Make sure you're using the helper script or mounting the correct directory.

### "Capabilities insufficient"
The script is outside mounted directories. Use the helper script.

### Import errors
Remember: only Python stdlib is available. No pip packages.

## What's Next?

Now that Python execution works, you can:
1. Implement the stdin/stdout bridge (SDK)
2. Create the FastAPI backend
3. Build example plugins
4. Set up the GPU instance with Ollama
5. Connect everything together

See IMPLEMENTATION_PLAN.md for detailed steps.

Happy coding! 🚀
EOF

log_success "Guide: QUICK_START.md"

################################################################################
# Final Summary
################################################################################

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✨  INSTALLATION COMPLETE!  ✨                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

log_success "Completed in ${MINUTES}m ${SECONDS}s"
echo ""

echo -e "${CYAN}📦 Installed:${NC}"
echo "  ✓ WasmEdge $(wasmedge --version 2>&1 | head -n1)"
echo "  ✓ Python WASM (interpreter + AOT)"
echo "  ✓ Virtual environment + dependencies"
echo "  ✓ Project structure"
echo "  ✓ Helper scripts"
echo ""

echo -e "${CYAN}🚀 Quick Test:${NC}"
echo "  cd $PROJECT_ROOT"
echo "  ./run-python-wasm.sh plugins/examples/hello_world.py"
echo ""

echo -e "${CYAN}📚 Next Steps:${NC}"
echo "  1. Test it: ./run-python-wasm.sh plugins/examples/hello_world.py"
echo "  2. Read: cat QUICK_START.md"
echo "  3. Build: Implement backend SDK and API server"
echo ""

log_info "All files in: $PROJECT_ROOT"
echo ""
