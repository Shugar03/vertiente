"""Capa LLM (profesor). Dueño: Sebastián.

- Proveedor intercambiable (openai | anthropic | none) vía LLM_PROVIDER / LLM_MODEL.
- Caché en cache/llm/ por hash del prompt (se commitea → el jurado puede re-correr sin clave).
- Timeout, reintentos con espera creciente, validación del JSON de salida.
- Contabiliza tokens y USD para costo.json.
- Sin clave y sin caché → devuelve None y el llamador usa reglas de respaldo.
"""
