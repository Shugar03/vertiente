# Roadmap

Medimos todo con la réplica del puntaje oficial (`make score`). Línea base oficial: ~17/55.

| Fase | Objetivo | Estado |
|---|---|---|
| **0 · Base** | Ingest a DuckDB/Parquet, réplica del puntaje, validador de formato, elección de embeddings | ✅ e5-small elegido (E01–E02) |
| **1 · v1 completa** | Narrativas + coordinación + entrega de punta a punta con un comando | ✅ |
| **2 · Puntaje** | Postura, origen, ruido; coordinación robusta | ✅ **53,62/55** en práctica |
| **3 · Producto** | Validación de robustez, profesor LLM opcional, dashboard, README de almacenamiento/escala | ✅ |
| **4 · Entrega** | Set final -> `entrega/`, video, Hacki, pitch | ⏳ viernes 13 (ver checklist) |

## Checklist del viernes

Todo automatizado y ensayado (con un set final simulado) en `scripts/entrega_final.sh`:

1. [ ] Desde temprano: `make final` — espera a que se publique el set final (revisa el repo del desafío cada 5 min;
       o copiá los CSV a `datos/final/`), y entonces corre, valida, testea, genera `demo/dashboard.html` y
       `demo/demo.mp4`, commitea `entrega/` y hace push.
2. [ ] (Opcional, antes) `.env` con `ANTHROPIC_API_KEY` para que el profesor decida bandos y títulos.
3. [ ] **Repo público** antes del cierre: `make publicar` (o `PUBLICAR=1 make final` hace todo junto).
4. [ ] Cargar en Hacki el link al repo + `demo/demo.mp4` (o `docs/demo_practica.mp4`). Pitch: `docs/PITCH.md`.

## Reglas de juego

- Cada cambio se mide con `make score` y `make validar` antes de mergear: si no mejora el promedio y el peor caso,
  no entra.
- El viernes nadie toca código salvo para que corra: primero entrega válida, después mejoras.
