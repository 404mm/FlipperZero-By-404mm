from __future__ import annotations

import json
from typing import Any, Dict, List

from .llm import LLM, LLMMessage
from .tools import ToolSpec


PLANNER_SYSTEM_PROMPT = (
    "Eres un planificador de un agente de IA. Debes decidir el siguiente paso en formato JSON estricto."
    " Dispones de herramientas y del historial. NUNCA reveles tu razonamiento; solo devuelve JSON."
)


def build_planner_user_prompt(task: str, history: List[Dict[str, str]], tools: List[ToolSpec]) -> str:
    tools_str = []
    for t in tools:
        tools_str.append(
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
        )
    payload = {
        "task": task,
        "history": history,
        "tools": tools_str,
        "instructions": (
            "Responde exclusivamente con un JSON de la forma:\n"
            "{\n  \"action\": \"tool_name | final_answer\",\n  \"input\": { ... },\n  \"reason\": \"breve justificación\",\n  \"confidence\": 0.0\n}\n"
            "Si necesitas buscar información, usa 'web_search'. Para leer una página, usa 'web_scrape'."
            " Para finalizar, usa 'final_answer' con un campo 'answer'."
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def plan_next_action(llm: LLM, task: str, history: List[Dict[str, str]], tools: List[ToolSpec]) -> Dict[str, Any]:
    messages = [
        LLMMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
        LLMMessage(role="user", content=build_planner_user_prompt(task, history, tools)),
    ]
    result = llm.chat_json(messages)
    if not isinstance(result, dict):
        return {"action": "final_answer", "input": {"answer": "No pude planificar."}}
    action = result.get("action")
    if action not in {"final_answer"} | {t.name for t in tools}:
        result["action"] = "final_answer"
        result["input"] = {"answer": "Acción inválida; finalizando."}
    if "input" not in result:
        result["input"] = {}
    return result