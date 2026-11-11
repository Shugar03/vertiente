# Roadmap

Medimos todo con el script oficial sobre práctica (`make score`). Línea base oficial: ~17/55.

| Fase | Cuándo | Objetivo | Listo cuando |
|---|---|---|---|
| **0 · Base** | Mié 11, tarde | Ingest a DuckDB/Parquet, `make score` y `make check` andando, comparación de embeddings | Medimos la línea base y elegimos modelo de embeddings con datos |
| **1 · v1 completa** | Mié 11, noche | Embeddings + agrupamiento + ruido + herencia por respuestas; coordinación por copias y ráfagas; `entrega/` válida | Pipeline de punta a punta con un comando; **> ~35/55** |
| **2 · Puntaje** | Jue 12, mañana/tarde | LLM por grupo, destilación de postura, origen; grafo contra lo esperable + Leiden; validación dejando un tema afuera | **> ~45/55** en práctica y sin caída fuerte con el tema afuera |
| **3 · Producto** | Jue 12, tarde/noche | Dashboard "en vivo", `costo.json` automático, README de almacenamiento y escala, caché LLM commiteada | **Congelamiento de funcionalidades: jue 22 h.** Ensayo general desde clon limpio |
| **4 · Entrega** | Vie 13, mañana | Correr el set final, commitear `entrega/`, video, Hacki, pitch | Commit pusheado **antes del cierre** y **repo público** |

## Reglas de juego

- Cada mejora se mide con `make score` antes de mergear. Si no sube (o baja con el tema afuera), no entra.
- Después del congelamiento solo se arreglan bugs.
- El viernes nadie toca código salvo para que corra: primero entrega válida, después mejoras.
- Si algo de la Fase 2 no anda el jueves a las 18 h, se descarta y se sigue con lo de la Fase 1.
