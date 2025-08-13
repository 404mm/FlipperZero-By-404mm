# AgentX — Agente de IA modular, reflexivo y conectado a herramientas

AgentX es un agente de IA minimalista pero potente, diseñado para ser:
- Modular (herramientas enchufables)
- Reflexivo (auto-revisión opcional)
- Con memoria (corto y largo plazo)
- Conectado (búsqueda y scraping web)
- Flexible en el backend de LLM (OpenAI, Ollama o modo local "echo" sin dependencias externas)

## Características clave
- Planificación estilo ReAct con salidas estrictas en JSON (robusto al parseo)
- Herramientas incluidas: `web_search`, `web_scrape`, `file_read`, `file_write`
- Memoria de corto plazo (historial) y largo plazo (JSON indexado con TF‑IDF liviano)
- Paso de reflexión opcional para mejorar la respuesta final
- Seguridad básica en escritura/lectura de archivos (acotada al directorio actual)
- Backend automático: usa OpenAI si hay `OPENAI_API_KEY`, si no intenta Ollama, y si no, cae a `echo` para funcionar de inmediato

## Requisitos
- Python 3.10+

## Instalación (opcional para herramientas web)
Para uso básico en modo `echo` no necesitas instalar dependencias. Si quieres usar herramientas web (búsqueda/scraping), instala:
```
pip install -r requirements.txt
```

## Uso rápido
- Sin ninguna clave (modo "echo"), ejecuta y podrás probar el ciclo completo:
```
python3 -m agentx.main -q "Resume en 3 puntos las últimas noticias sobre IA" --backend echo
```

- Con OpenAI (recomendado):
```
export OPENAI_API_KEY=tu_api_key
python3 -m agentx.main -q "Crea un plan de lanzamiento para mi app en 5 pasos" --backend openai --openai-model gpt-4o-mini
```

- Con Ollama local (ej. `llama3.1`):
```
export OLLAMA_BASE_URL=http://localhost:11434
python3 -m agentx.main -q "Genera una propuesta de investigación sobre energías renovables" --backend ollama --ollama-model llama3.1
```

## Ejemplos
- Búsqueda y scraping web en 2-4 pasos:
```
python3 -m agentx.main -q "¿Qué anunció NVIDIA en su último keynote? Cita fuentes." --max-steps 4
```

## Añadir herramientas propias
Crea una clase que herede de `Tool` en `agentx/tools.py`, define `name`, `description`, un `input_schema` (dict JSON Schema) y el método `run(tool_input: dict) -> dict`. Regístrala en el `ToolRegistry`.

## Estructura
```
agentx/
  agent.py        # Orquestación del ciclo del agente
  config.py       # Configuración y detección del backend
  llm.py          # Abstracción de LLMs (OpenAI, Ollama, Echo)
  memory.py       # Memoria corto/largo plazo (TF‑IDF simple)
  tools.py        # Herramientas incluidas + registro (sin dependencias obligatorias)
  planner.py      # Planificador ReAct (JSON estricto)
  main.py         # CLI
```

## Notas
- El modo `echo` permite ejecutar el pipeline sin un LLM real ni dependencias externas; útil para probar flujos y herramientas. Para máxima calidad, usa OpenAI u Ollama.
- El agente intenta mantener salidas estructuradas en JSON para robustez en el pipeline.
