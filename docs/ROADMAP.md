# Roadmap

Medimos todo con la réplica del puntaje oficial (`make score`). Línea base oficial: ~17/55.

| Fase | Objetivo | Estado |
|---|---|---|
| **0 · Base** | Ingest a DuckDB/Parquet, réplica del puntaje, validador de formato, elección de embeddings | ✅ e5-small elegido (E01–E02) |
| **1 · v1 completa** | Narrativas + coordinación + entrega de punta a punta con un comando | ✅ |
| **2 · Puntaje** | Postura, origen, ruido; coordinación robusta | ✅ **53,76/55** en práctica |
| **3 · Producto** | Validación de robustez, profesor LLM opcional, dashboard, README de almacenamiento/escala | ✅ |
| **4 · Entrega** | Set final -> `entrega/`, video, Hacki, pitch | ⏳ viernes 13 (ver checklist) |

## Checklist del viernes

1. [ ] Bajar el set final a `datos/final/` (mismos 4 archivos `.csv.gz` + `fuentes.csv`).
2. [ ] (Opcional) `.env` con `ANTHROPIC_API_KEY` para que el profesor decida bandos y títulos.
3. [ ] `make entrega` → debe terminar con `OK: formato válido`. Revisar `entrega/costo.json`.
4. [ ] `make demo DATOS=datos/final SALIDA=entrega` → dashboard del set final para el pitch.
5. [ ] `git add entrega cache/llm && git commit && git push` **antes del cierre**.
6. [ ] **Pasar el repo a público** (Settings → General → Danger zone → Change visibility).
7. [ ] Cargar en Hacki: link al repo + video (guion en `docs/PITCH.md`).

## Reglas de juego

- Cada cambio se mide con `make score` y `make validar` antes de mergear: si no mejora el promedio y el peor caso,
  no entra.
- El viernes nadie toca código salvo para que corra: primero entrega válida, después mejoras.
