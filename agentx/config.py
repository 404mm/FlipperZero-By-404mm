from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    backend: str = "auto"  # auto | openai | ollama | echo
    temperature: float = 0.2
    max_steps: int = 8
    use_reflection: bool = True

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # Ollama
    ollama_base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = "llama3.1"

    # Seguridad/herramientas
    allow_shell: bool = False

    # Memoria
    memory_path: str = os.path.abspath("agentx_data/memory.json")

    @classmethod
    def from_env_and_args(
        cls,
        backend: Optional[str] = None,
        temperature: Optional[float] = None,
        max_steps: Optional[int] = None,
        use_reflection: Optional[bool] = None,
        openai_model: Optional[str] = None,
        ollama_model: Optional[str] = None,
        allow_shell: Optional[bool] = None,
    ) -> "AgentConfig":
        config = cls()
        if backend:
            config.backend = backend
        if temperature is not None:
            config.temperature = float(temperature)
        if max_steps is not None:
            config.max_steps = int(max_steps)
        if use_reflection is not None:
            config.use_reflection = bool(use_reflection)
        if openai_model:
            config.openai_model = openai_model
        if ollama_model:
            config.ollama_model = ollama_model
        if allow_shell is not None:
            config.allow_shell = bool(allow_shell)

        config.openai_api_key = os.environ.get("OPENAI_API_KEY")
        return config


@dataclass
class RuntimeBackendChoice:
    name: str
    reason: str


def auto_select_backend(config: AgentConfig) -> RuntimeBackendChoice:
    if config.backend != "auto":
        return RuntimeBackendChoice(config.backend, "Backend definido por el usuario")

    if config.openai_api_key:
        return RuntimeBackendChoice("openai", "Se detectó OPENAI_API_KEY")

    try:
        import requests  # type: ignore

        base = config.ollama_base_url.rstrip("/")
        response = requests.get(f"{base}/api/tags", timeout=1.5)
        if response.status_code == 200:
            return RuntimeBackendChoice("ollama", "Servidor Ollama disponible")
    except Exception:
        pass

    return RuntimeBackendChoice("echo", "Sin backend externo; usando modo local")