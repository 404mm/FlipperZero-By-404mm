from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMMessage:
    role: str
    content: str


class LLM:
    def __init__(self, temperature: float = 0.2) -> None:
        self.temperature = float(temperature)

    def chat(self, messages: List[LLMMessage]) -> str:
        raise NotImplementedError

    def chat_json(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        import json

        text = self.chat(messages)
        try:
            return json.loads(text)
        except Exception:
            # Intento de extracción naive del primer bloque JSON
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    return json.loads(text[start : end + 1])
            except Exception:
                pass
            return {"error": "Invalid JSON from model", "raw": text}


class OpenAIChatLLM(LLM):
    def __init__(self, api_key: str, model: str, temperature: float = 0.2) -> None:
        super().__init__(temperature)
        self.api_key = api_key
        self.model = model

    def chat(self, messages: List[LLMMessage]) -> str:
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "La librería 'openai' no está instalada. Instálala para usar este backend."
            ) from exc

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return response.choices[0].message.content or ""


class OllamaLLM(LLM):
    def __init__(self, model: str, base_url: str = "http://localhost:11434", temperature: float = 0.2) -> None:
        super().__init__(temperature)
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[LLMMessage]) -> str:
        import requests

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        return content


class EchoLLM(LLM):
    def chat(self, messages: List[LLMMessage]) -> str:
        import json

        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        payload = {
            "action": "final_answer",
            "input": {
                "answer": f"[Echo] No hay LLM configurado. Mensaje recibido: {last_user[:200]}"
            },
        }
        return json.dumps(payload, ensure_ascii=False)