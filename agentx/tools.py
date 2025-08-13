from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]

    def run(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_specs(self) -> List[ToolSpec]:
        specs: List[ToolSpec] = []
        for tool in self._tools.values():
            specs.append(
                ToolSpec(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
            )
        return specs


# ------------------------ Herramientas concretas -------------------------


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Busca en la web usando DuckDuckGo y devuelve resultados con título, snippet y URL."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Consulta de búsqueda"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 15, "default": 5},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def run(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        query = str(tool_input.get("query", "")).strip()
        max_results = int(tool_input.get("max_results", 5))
        if not query:
            return {"ok": False, "error": "query requerido"}
        try:
            from duckduckgo_search import DDGS  # type: ignore
        except Exception:
            return {"ok": False, "error": "duckduckgo-search no está instalado"}

        start = time.time()
        results: List[Dict[str, Any]] = []
        with DDGS() as ddgs:
            for idx, r in enumerate(ddgs.text(query, max_results=max_results)):
                results.append(
                    {
                        "title": r.get("title"),
                        "snippet": r.get("body"),
                        "url": r.get("href"),
                        "rank": idx + 1,
                    }
                )
        duration = time.time() - start
        return {"ok": True, "took_seconds": round(duration, 3), "results": results}


class WebScrapeTool(Tool):
    name = "web_scrape"
    description = "Descarga una página y extrae su texto visible principal."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL a extraer"},
            "max_chars": {"type": "integer", "minimum": 500, "maximum": 20000, "default": 6000},
        },
        "required": ["url"],
        "additionalProperties": False,
    }

    def run(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        url = str(tool_input.get("url", "")).strip()
        max_chars = int(tool_input.get("max_chars", 6000))
        if not url:
            return {"ok": False, "error": "url requerida"}
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
        }
        try:
            import requests  # type: ignore
            from bs4 import BeautifulSoup  # type: ignore
        except Exception:
            return {"ok": False, "error": "Falta 'requests' o 'beautifulsoup4'"}

        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
        except Exception as exc:
            return {"ok": False, "error": f"request failed: {exc}"}

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "svg"]):
            tag.extract()
        text = re.sub(r"\s+", " ", soup.get_text(separator=" ").strip())
        if len(text) > max_chars:
            text = text[:max_chars] + " …"
        return {"ok": True, "content": text}


class FileReadTool(Tool):
    name = "file_read"
    description = "Lee un archivo de texto dentro del directorio de trabajo actual."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta del archivo relativa al cwd"},
            "max_bytes": {"type": "integer", "minimum": 100, "maximum": 500000, "default": 20000},
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    def run(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        path = os.path.abspath(str(tool_input.get("path", "")))
        max_bytes = int(tool_input.get("max_bytes", 20000))
        cwd = os.path.abspath(os.getcwd())
        if not path.startswith(cwd):
            return {"ok": False, "error": "Acceso fuera del directorio de trabajo denegado"}
        if not os.path.exists(path):
            return {"ok": False, "error": "Archivo no encontrado"}
        try:
            with open(path, "rb") as f:
                data = f.read(max_bytes)
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                text = data.decode("latin-1", errors="replace")
            return {"ok": True, "content": text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


class FileWriteTool(Tool):
    name = "file_write"
    description = "Escribe texto en un archivo dentro del directorio de trabajo actual."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta destino relativa al cwd"},
            "content": {"type": "string", "description": "Contenido a escribir"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    }

    def run(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        path = os.path.abspath(str(tool_input.get("path", "")))
        content = str(tool_input.get("content", ""))
        cwd = os.path.abspath(os.getcwd())
        if not path.startswith(cwd):
            return {"ok": False, "error": "Acceso fuera del directorio de trabajo denegado"}
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"ok": True, "path": path}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(WebScrapeTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    return registry