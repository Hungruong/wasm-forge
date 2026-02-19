"""
platform_sdk.py — WasmForge Plugin SDK

Available functions:
    get_input()             → Read user-provided input
    call_ai(model, prompt)  → Call an AI model, returns response string
    send_output(result)     → Return final result to user
    list_models()           → Get list of available model names
"""

import sys
import json

_input_cache = None


def get_input() -> str:
    """Read user input passed via stdin by the bridge."""
    global _input_cache
    if _input_cache is None:
        _input_cache = sys.stdin.readline().strip()
    return _input_cache


def call_ai(model: str, prompt: str) -> str:
    """
    Call an AI model through the bridge.

    Args:
        model:  "mistral", "llama3", "gemma2", "qwen2.5", etc.
        prompt: The prompt to send

    Returns:
        Model response as a string
    """
    request = json.dumps({"type": "ai_call", "model": model, "prompt": prompt})
    print(request, flush=True)

    response_line = sys.stdin.readline().strip()
    if not response_line:
        return "[ERROR] No response from bridge"

    try:
        response = json.loads(response_line)
        if response.get("type") == "result":
            return response.get("data", "")
        elif response.get("type") == "error":
            return f"[ERROR] {response.get('error', 'Unknown error')}"
        else:
            return f"[ERROR] Unexpected response: {response_line}"
    except json.JSONDecodeError:
        return f"[ERROR] Invalid response: {response_line}"


def send_output(result: str) -> None:
    """Return the final result to the user via stdout."""
    print(str(result), flush=True)


def list_models() -> list:
    """Get list of available AI model names."""
    print(json.dumps({"type": "list_models"}), flush=True)
    line = sys.stdin.readline().strip()
    try:
        response = json.loads(line)
        return json.loads(response.get("data", "[]"))
    except (json.JSONDecodeError, TypeError):
        return []