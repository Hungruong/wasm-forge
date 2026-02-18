"""
core/exceptions.py — Domain-specific exceptions for structured error handling.
"""


class PluginNotFoundError(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Plugin '{name}' not found")


class PluginUploadError(Exception):
    pass


class PluginValidationError(Exception):
    pass


class SandboxError(Exception):
    """WasmEdge failed to launch or crashed."""
    pass


class SandboxTimeoutError(Exception):
    """Plugin exceeded MAX_EXECUTION_TIME."""
    pass


class BridgeProtocolError(Exception):
    """Malformed message crossing the stdin/stdout bridge."""
    pass


class OllamaUnavailableError(Exception):
    pass


class ModelNotAllowedError(Exception):
    def __init__(self, model: str, allowed: list[str]):
        self.model = model
        super().__init__(f"Model '{model}' is not allowed. Use one of: {allowed}")


class PromptTooLongError(Exception):
    def __init__(self, length: int, max_length: int):
        super().__init__(f"Prompt length {length} exceeds limit of {max_length}")