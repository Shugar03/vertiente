# Plan — mapa del sistema

## Principio

**Lo que es BERT corre local; lo que es LLM va por API, y solo como "profesor".** El LLM nunca procesa comentario por
comentario: nombra grupos, une variantes y etiqueta una muestra; con esa muestra se entrenan clasificadores locales que
deciden los ~150.000 comentarios en segundos (destilación).

## Mapa

```
                    ┌──────────────────────── ingest (Fran) ────────────────────────┐
datos/<set>/*.csv.gz│ limpiar · normalizar texto · zona -03:00 · hash · dedup        │──► interim/*.parquet (DuckDB)
                    └──────────────┬──────────────────────────────────┬─────────────┘
                                   │                                  │
          ┌────────── NARRATIVAS (Sebastián) ──────────┐   ┌──── COORDINACIÓN (Antony) ────┐
          │ 1 embeddings de textos únicos (local)       │   │ A rasgos de cuenta            │
          │ 2 ruido: reglas + clasificador              │   │ B grafo co-ocurrencia en      │
          │ 3 agrupamiento fino (narrativa × postura)   │   │   misma publicación/ventana,  │
          │ 4 LLM por grupo: afirmación, postura,       │   │   pesado contra lo esperable  │
          │   unir variantes, emparejar pro/contra      │   │   + respuestas mutuas (SQL)   │
          │ 5 LLM etiqueta muestra → clasificador de    │   │ C comunidades (Leiden) →      │
          │   postura local (destilación)               │   │   grupos densos y anómalos    │
          │ 6 propagar: kNN + herencia por respuestas   │   │ D umbral por precisión        │
          │ 7 origen: primer pico real de cada grupo    │   └───────────────┬───────────────┘
          └──────────────────────┬──────────────────────┘                   │
                                 └──────────── escribir entrega/ ◄──────────┘
                                   comentarios.csv · narrativas.csv · cuentas.csv · costo.json
                                                     │
                                       make check (formato) · make score (oficial)
```

Narrativas y coordinación son **independientes** → corren en paralelo.

## Contratos entre etapas (Parquet en `interim/<set>/`)

| Archivo | Dueño | Columnas |
|---|---|---|
| `comentarios.parquet` | Fran | `comentario_id, publicacion_id, cuenta_id, ts (tz -03:00), texto, texto_norm, texto_hash, respuesta_a, me_gusta` |
| `cuentas.parquet` | Fran | `cuenta_id, usuario, fecha_creacion, seguidores, siguiendo` (+ cuentas que comentan sin perfil) |
| `publicaciones.parquet` | Fran | `publicacion_id, fuente_id, ts, titular` |
| `embeddings.parquet` | Sebastián | `texto_hash, vector` (caché por hash) |
| `narrativas_asig.parquet` | Sebastián | `comentario_id, narrativa, postura, confianza` |
| `narrativas_meta.parquet` | Sebastián | `narrativa, titulo, frases_clave, fecha_origen` |
| `cuentas_feat.parquet` | Antony/Fran | `cuenta_id, …rasgos` |
| `grupos.parquet` | Antony | `cuenta_id, grupo, score` |

`entrega` lee solo estos contratos. Cambiar un contrato = avisar a los otros dos.

## Modelos

| Uso | Dónde | Candidatos (se decide en Fase 0 con datos) |
|---|---|---|
| Embeddings | local | multilingual-e5-small · EmbeddingGemma 2 |
| Clasificadores de decisión (postura, ruido, acuerdo/desacuerdo en respuestas) | local | regresión logística / MLP sobre embeddings |
| Casos dudosos | local (opcional) | NLI multilingüe (mDeBERTa-v3-xnli) |
| Profesor | API | el modelo más barato/rápido de OpenAI o Claude que pase la validación |

## Casos borde

**Texto**
- Typos ("ahroa"), abreviaturas ("x", "q", "tmb", "pa"), mayúsculas, emojis, hashtags, URLs, menciones.
- Texto vacío/nulo; ids duplicados.
- Negación que rechaza ("es mentira que X" rechaza X con las mismas palabras).
- Contraargumento sin negación ("el agua se corta hace 20 años" rechaza "la mina se queda con el agua").
- Sarcasmo; comentarios con dos narrativas (asignar la dominante).
- Memes genuinos: "Y el agua? 💧" ×578 es gente real, **no** campaña.

**Respuestas (`respuesta_a`)**
- Corta y sin contenido ("Coincido", "Tal cual") ⇒ hereda narrativa y postura del padre (también si es "rechaza").
- Contradice ("Mentira", "Eso es falso") ⇒ misma narrativa, postura opuesta.
- Con argumento propio ⇒ se clasifica por su texto.
- Responde a ruido ⇒ ruido.
- Cadenas largas ⇒ resolución recursiva con límite de profundidad.
- Padre inexistente o posterior ⇒ tratar como comentario suelto. Ciclos ⇒ detectar y cortar.

**Fechas y cuentas**
- Zonas mezcladas / fechas mal formadas ⇒ normalizar a -03:00; lo irrecuperable se loguea y se sigue.
- Cuenta creada después de su primer comentario; seguidores negativos o no numéricos ⇒ limpiar y marcar.
- Cuentas que comentan sin perfil ⇒ crear perfil vacío (deben estar en `cuentas.csv`).

**Trampas del desafío**
- Picos virales genuinos: mucha gente junta **una vez**. Coordinación = **repetición** de las mismas cuentas juntas.
- Campañas de estilos distintos; en el final puede haber estilos nuevos ⇒ combinar señales, ninguna sola.
- Cuentas de campaña que comentan de todo y en ambas posturas (tipo C2).
- Narrativas emergentes y rumores ⇒ origen = primer pico real, no el primer comentario suelto.

## Generalización (el final trae otros temas)

- **Cero palabras de los temas de práctica** en código o prompts.
- Umbrales **relativos** (percentiles, z-scores, lo normal por publicación), nunca absolutos.
- Cantidad de narrativas y de campañas: la decide el método.
- Validación: **dejar un tema afuera** (litio/colectivo/hospital rotando), **por tiempo** (primeros días vs últimos),
  **datos ensuciados** (submuestreo 75%, typos, horas desordenadas).
- Todos los parámetros en `config.yaml`.

## Velocidad

| Palanca | Efecto |
|---|---|
| Dedup de texto normalizado antes de embeber | 200k → ~97k |
| Modelo chico, int8, ONNX/MPS, por lotes | minutos en CPU |
| Caché de embeddings por hash | re-correr ≈ gratis |
| Reducir dimensión (Matryoshka/UMAP) o kNN-grafo antes de agrupar | agrupamiento en segundos-minutos |
| Vecinos aproximados (FAISS/HNSW) para propagar | segundos |
| LLM por grupo + muestra, asíncrono, con caché | ~3.200 llamadas, < USD 1 |
| Narrativas ‖ coordinación en paralelo | resta la etapa más corta |
| Grafo de cuentas en SQL (DuckDB) con ventana temporal | evita explosión de pares |
| `make setup` baja modelos antes | el viernes no dependemos de la red |

**Meta:** set final en **< 10 min** en notebook y **< USD 1**. Pico de RAM estimado 4–6 GB (entra en 16 GB).

## Confiabilidad

- LLM: timeout, reintentos con espera creciente, validación del JSON; si falla ⇒ reglas de respaldo.
- **Sin clave** ⇒ `cache/llm/` commiteada (por hash del prompt) y, si no hay caché, reglas (c-TF-IDF para nombres,
  clasificadores con semillas para postura). Peor calidad, nunca se rompe.
- Cada etapa escribe su Parquet ⇒ se retoma desde donde quedó.
- Reproducible: semillas fijas, temperatura 0, `uv.lock`, Python fijo.
- `make check` antes de cada commit de `entrega/`.
- Logs por etapa: tiempo, filas, avisos de datos sucios. `costo.json` se genera solo.
- **Ensayo general el jueves a la noche**: clonar de cero, `make setup && make entrega` cronometrado.
