from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .config import AgentConfig
from .llm import EchoLLM, LLM, LLMMessage, OllamaLLM, OpenAIChatLLM
from .memory import LongTermMemory, ShortTermMemory
from .planner import plan_next_action
from .tools import ToolRegistry, default_tool_registry


REFLECTION_SYSTEM = (
    "Eres un revisor crítico. Dado un borrador de respuesta y el objetivo del usuario, sugiere mejoras concisas."
    " Devuelve JSON: {\n  \"improved_answer\": str,\n  \"notes\": str\n}"
)


def _llm_from_config(config: AgentConfig) -> LLM:
    backend = config.backend
    if backend == "openai" and config.openai_api_key:
        return OpenAIChatLLM(api_key=config.openai_api_key, model=config.openai_model, temperature=config.temperature)
    if backend == "ollama":
        return OllamaLLM(model=config.ollama_model, base_url=config.ollama_base_url, temperature=config.temperature)
    return EchoLLM(temperature=config.temperature)


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.config = config
        self.llm = _llm_from_config(config)
        self.tools = tool_registry or default_tool_registry()
        self.st_memory = ShortTermMemory()
        self.lt_memory = LongTermMemory(config.memory_path)

    def run(self, task: str) -> str:
        self.st_memory.add("user", task)
        history_for_planner: List[Dict[str, str]] = [
            {"role": m.role, "content": m.content} for m in self.st_memory.history()
        ]

        final_answer: Optional[str] = None

        for step in range(self.config.max_steps):
            plan = plan_next_action(
                self.llm,
                task=task,
                history=history_for_planner,
                tools=self.tools.list_specs(),
            )

            action = plan.get("action")
            tool_input: Dict[str, Any] = plan.get("input", {})

            if action == "final_answer":
                final_answer = str(tool_input.get("answer", ""))
                break

            tool = self.tools.get(action or "")
            if not tool:
                final_answer = "No se encontró la herramienta solicitada; finalizando."
                break

            try:
                observation = tool.run(tool_input)
            except Exception as exc:
                observation = {"ok": False, "error": f"error ejecutando herramienta: {exc}"}

            obs_text = json.dumps(observation, ensure_ascii=False)
            self.st_memory.add("assistant", f"[action:{action}] {json.dumps(tool_input, ensure_ascii=False)}")
            self.st_memory.add("tool", obs_text)
            history_for_planner = [
                {"role": m.role, "content": m.content} for m in self.st_memory.history()
            ]

        if final_answer is None:
            final_answer = "No se pudo completar la tarea en los pasos permitidos."

        if self.config.use_reflection and not isinstance(self.llm, EchoLLM):
            try:
                messages = [
                    LLMMessage(role="system", content=REFLECTION_SYSTEM),
                    LLMMessage(
                        role="user",
                        content=json.dumps({"task": task, "draft": final_answer}, ensure_ascii=False, indent=2),
                    ),
                ]
                reflection = self.llm.chat(messages)
                try:
                    data = json.loads(reflection)
                    improved = data.get("improved_answer")
                    final_answer = improved or final_answer
                except Exception:
                    pass
            except Exception:
                pass

        try:
            snippet = (final_answer or "")[:1000]
            if snippet:
                self.lt_memory.add_document(snippet, {"source": "final_answer"})
        except Exception:
            pass

        return final_answer or ""