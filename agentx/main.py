from __future__ import annotations

import argparse
import os
import sys

from .agent import Agent
from .config import AgentConfig, auto_select_backend


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgentX - Agente de IA modular")
    parser.add_argument("-q", "--query", type=str, help="Tarea o pregunta a resolver", required=True)
    parser.add_argument("--backend", type=str, default=None, choices=["auto", "openai", "ollama", "echo"], help="Backend LLM")
    parser.add_argument("--openai-model", type=str, default=None, help="Modelo OpenAI")
    parser.add_argument("--ollama-model", type=str, default=None, help="Modelo Ollama")
    parser.add_argument("--max-steps", type=int, default=None, help="Pasos máximos del planificador")
    parser.add_argument("--temperature", type=float, default=None, help="Temperatura del modelo")
    parser.add_argument("--no-reflection", action="store_true", help="Desactivar reflexión final")
    parser.add_argument("--allow-shell", action="store_true", help="(Reservado) Permitir herramientas de shell")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config = AgentConfig.from_env_and_args(
        backend=args.backend,
        temperature=args.temperature,
        max_steps=args.max_steps,
        use_reflection=(not args.no_reflection),
        openai_model=args.openai_model,
        ollama_model=args.ollama_model,
        allow_shell=args.allow_shell,
    )

    choice = auto_select_backend(config)
    config.backend = choice.name

    agent = Agent(config=config)
    answer = agent.run(args.query)

    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())