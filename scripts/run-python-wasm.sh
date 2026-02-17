#!/bin/bash
set -e

PYTHON_FILE="$1"
PYTHON_WASM="/opt/wasmedge-python/bin/python-3.11.1-wasmedge-aot.wasm"
WASMEDGE_LIB="/opt/wasmedge-python"

if [ -z "$PYTHON_FILE" ]; then
  echo "Usage: run-python-wasm.sh <path-to-python-file>" >&2
  exit 1
fi

if [ ! -f "$PYTHON_FILE" ]; then
  echo "Error: File not found: $PYTHON_FILE" >&2
  exit 2
fi

# Get directory of the uploaded file so we can mount it
SCRIPT_DIR=$(dirname "$(realpath "$PYTHON_FILE")")
SCRIPT_NAME=$(basename "$PYTHON_FILE")

wasmedge \
  --dir /:/opt/wasmedge-python \
  --dir /scripts:"$SCRIPT_DIR" \
  --time-limit 10000 \
  --memory-page-limit 2048 \
  "$PYTHON_WASM" \
  /scripts/"$SCRIPT_NAME"
