# División tentativa de tareas

Roles genéricos; se ajustan sobre la marcha. Cada uno es dueño de sus contratos (ver `PLAN.md`).

## Fran — datos y plataforma (bases de datos)

- [ ] `make setup` / `make datos`: entorno, modelos locales, datos de práctica, script oficial en `vendor/`.
- [ ] **ingest**: CSV.gz → Parquet en DuckDB; limpieza, zona -03:00, `texto_norm`, `texto_hash`, dedup.
- [ ] Casos borde de datos sucios (ids duplicados, fechas rotas, cuentas sin perfil, respuestas huérfanas/ciclos).
- [ ] Tablas SQL de co-ocurrencia de cuentas (misma publicación + ventana) y respuestas mutuas → para Antony.
- [ ] `make run` de punta a punta, ejecución en paralelo de narrativas y coordinación.
- [ ] Medición de tiempo/tokens/USD por etapa → `costo.json` automático.
- [ ] `make check` (validador de formato) y `make score`.
- [ ] Validación dejando un tema afuera / por tiempo / datos ensuciados.
- [ ] README: almacenamiento (por qué DuckDB + Parquet) y cómo escala a millones/día.
- [ ] Viernes: correr el set final, commitear `entrega/`, **pasar el repo a público**.

## Sebastián — narrativas

- [ ] Fase 0: comparar multilingual-e5-small vs EmbeddingGemma 2 (tiempo + B-cubed con el script oficial).
- [ ] Embeddings con caché por hash.
- [ ] Ruido: reglas (pregunta, saludo, emoji, reacción) + clasificador sobre embeddings.
- [ ] Agrupamiento fino (narrativa × postura); reducción de dimensión.
- [ ] Herencia por respuestas (acuerdo/desacuerdo).
- [ ] Capa LLM (`radar/llm.py`): proveedor intercambiable, caché, reintentos, respaldo sin clave.
- [ ] LLM por grupo: afirmación, unir variantes de redacción, emparejar pro/contra.
- [ ] Destilación de postura: LLM etiqueta muestra → clasificador local.
- [ ] Origen: primer pico real de cada narrativa.
- [ ] Títulos y frases clave de `narrativas.csv`.

## Antony — coordinación y demo

- [ ] Rasgos de cuenta: antigüedad relativa, seguidores/siguiendo, actividad nocturna, hashtags, textos copiados.
- [ ] v1: textos casi idénticos + ráfagas (campañas tipo C1/C3).
- [ ] Grafo de co-ocurrencia **contra lo esperable** (coincidir en un posteo viral vale poco) + respuestas mutuas (tipo C2).
- [ ] Comunidades (Leiden) y filtro de grupos densos/anómalos; umbral optimizado por precisión.
- [ ] Vincular cada operación con la narrativa que empuja (para la demo: "quién lo empuja").
- [ ] Dashboard: línea de tiempo por narrativa (apoya/rechaza), operaciones, y modo "en vivo" con alertas.
- [ ] Video (≤ 3 min) y pitch.

## Compartido

- [ ] Preguntas a la organización (ver `EVALUACION.md`).
- [ ] Revisar PRs del otro antes de mergear a `main`.
- [ ] Ensayo general el jueves a la noche.
