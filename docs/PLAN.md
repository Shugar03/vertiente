# Plan — mapa del sistema (estado final)

> Este documento empezó como plan y se actualizó con lo que efectivamente se construyó. Las decisiones que cambiaron
> respecto del plan original están marcadas con **Cambio** y justificadas por experimentos (`experimentos/`).

## Principio

**Lo local hace el trabajo; el LLM (opcional, por API) solo juzga donde las señales locales son débiles.**
**Cambio:** el plan preveía destilar postura con un LLM etiquetando una muestra. No hizo falta: la estructura de
respuestas da la postura gratis (E03–E06). El LLM quedó para una sola decisión por narrativa: qué bando afirma, y su
título (≈13 llamadas por corrida).

## Mapa

```
datos/<set>/*.csv.gz ─► INGEST (DuckDB) ─────────────────────────────► interim/<set>/*.parquet
                          limpiar · dedup · fechas · respuestas huérfanas/cíclicas · texto_norm · hash
                                   │
                          NARRATIVAS
                          1 embeddings e5-small de textos únicos (caché por hash)
                          2 microgrupos: Leiden sobre kNN
                          3 grafo de microgrupos por respuestas con contenido (misma narrativa, postura opuesta)
                          4 ruido: textos frecuentes sin respuestas (umbral adaptativo) + microgrupos sin respuestas
                          5 narrativas = comunidades; postura = bipartición espectral; lado que afirma: señales
                            locales o profesor LLM
                          6 herencia de "acompañamiento" (tal cual, coincido) por la cadena de respuestas
                          7 origen robusto; título; frases clave c-TF-IDF
                                   │
                          COORDINACIÓN (usa las narrativas predichas)
                          A sincronía alineada (SQL): misma publicación + narrativa + postura, ≤ 30 min,
                            en ≥ 2 publicaciones, normalizada por actividad
                          B se descartan aristas sin vecinos comunes (el azar no forma triángulos)
                          C Leiden + densidad del grupo + rescate de núcleo k-core; orden determinístico
                                   │
                          ENTREGA: comentarios.csv · narrativas.csv · cuentas.csv · costo.json  (+ dashboard.html)
```

**Cambio:** coordinación ya no corre en paralelo con narrativas: la usa (E17). La señal que separa a las campañas
—empujar lo mismo— necesita saber qué narrativa y qué postura tiene cada comentario.

## Contratos entre etapas (Parquet en `interim/<set>/`)

| Archivo | Etapa | Columnas |
|---|---|---|
| `comentarios.parquet` | ingest | `comentario_id, publicacion_id, cuenta_id, ts, texto, respuesta_a, me_gusta, texto_norm, texto_hash` |
| `cuentas.parquet` | ingest | `cuenta_id, usuario, fecha_creacion, seguidores, siguiendo` (+ cuentas que comentan sin perfil) |
| `publicaciones.parquet` | ingest | `publicacion_id, fuente_id, ts, titular` |
| `narrativas_asig.parquet` | narrativas | `comentario_id, narrativa, postura, micro, heredado` |
| `narrativas_meta.parquet` | narrativas | `narrativa, titulo, frases_clave, fecha_origen, apoya, rechaza, total` |
| `grupos.parquet` | coordinación | `cuenta_id, grupo` |
| `operaciones_meta.parquet` | coordinación | `grupo, cuentas, comentarios, narrativa, postura, foco, antiguedad_mediana_dias, frac_nocturna, primera_actividad` |
| `reporte.json` | cli | reporte de calidad de datos, tiempos y costo por etapa |
| `interim/cache_emb/*.parquet` | embeddings | `texto_hash, vector` |

## Modelos

| Uso | Dónde | Elegido |
|---|---|---|
| Embeddings | local | `intfloat/multilingual-e5-small` (E01–E02: igual calidad que EmbeddingGemma 2, 6x más rápido) |
| Profesor (opcional) | API | `claude-opus-5-5` por defecto (`LLM_MODEL` lo cambia; `claude-haiku-5-5` abarata) |
| Clasificadores / NLI | — | **Cambio:** no hicieron falta (la estructura de respuestas resuelve postura y ruido) |

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

## Velocidad (medido, Apple M5 16 GB)

| Etapa | Tiempo |
|---|---|
| ingest (200k comentarios) | ~2 s |
| embeddings de 62k textos únicos | ~40 s en frío (MPS) · 0 s con caché |
| narrativas (kNN + Leiden + grafo + herencia) | ~8 s |
| coordinación (2,6 M pares en SQL + grafo) | ~1 s |
| **total** | **~15 s con caché · ~60 s en frío** |

## Confiabilidad

- Sin LLM funciona completo; con LLM, caché commiteable (`cache/llm/`) y respaldo ante cualquier falla.
- Determinístico: textos ordenados por hash, aristas ordenadas, semillas fijas (E26).
- DuckDB con tope de memoria y de spill a disco (un experimento llegó a escribir 107 GB de temporales; ya no puede).
- `make check` valida el formato contra las trampas del script oficial; `make test` (52 tests); `make validar`.
