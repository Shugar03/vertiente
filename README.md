# Radar — narrativas y coordinación a escala

Hackathon Argentina Space 2026 · Desafío QualyData (Big Data) · Salta, 11–13 nov.

Sobre cientos de miles de comentarios, **descubre qué narrativas circulan** (con su postura y su origen) y **detecta
las operaciones coordinadas que las empujan**. Rápido (≈15 s para 200.000 comentarios en una notebook), barato
(USD 0 sin LLM) y sin depender de los temas del set de práctica.

**Práctica: 53,62 / 55 puntos automáticos** (línea base oficial ≈ 17). Detalle y robustez en
[docs/VALIDACION.md](docs/VALIDACION.md). Probado además sobre dos sets sintéticos escritos por agentes que no
vieron el pipeline (temas y campañas nuevas): narrativas 29,7/30 sobre temas nunca vistos
([docs/SINTETICOS.md](docs/SINTETICOS.md)).

## Cómo correrlo

Requisitos: Python 3.12 y [uv](https://docs.astral.sh/uv/). Sin GPU. ~3 GB de disco (entorno + modelo).

```bash
make setup                      # entorno, modelo de embeddings, datos de práctica y script oficial
make run                        # pipeline completo sobre datos/practica -> salida/practica/
make check                      # valida el formato de la entrega
make score                      # puntaje (réplica del oficial)   |   make score-oficial: el script del desafío
make demo                       # dashboard -> salida/practica/dashboard.html
make test                       # 76 tests, cobertura 93% (pipeline de producción ≈ 98%)
make validar                    # robustez: variantes ensuciadas, submuestreadas, sin un tema, otras semillas
```

**Set final (viernes):** copiar los CSV a `datos/final/` y correr **un solo comando**:

```bash
make entrega                    # = run + check sobre datos/final -> entrega/ (se commitea)
make final                      # todo el viernes: espera el set, corre, valida, dashboard + video, commit y push
make publicar                   # repo público (requisito excluyente al cierre)
```

Video de demo (práctica): [docs/demo_practica.mp4](docs/demo_practica.mp4) — se regenera con `scripts/grabar_video.sh`.

LLM opcional: copiar `.env.example` a `.env` y poner `ANTHROPIC_API_KEY`. Sin clave el pipeline corre igual (usa la
caché `cache/llm/` si existe y, si no, reglas locales).

## Cómo funciona

```
CSV.gz ─► ingest (DuckDB): limpieza, dedup, fechas, respuestas huérfanas/cíclicas, texto normalizado + hash
       ─► narrativas
            1. embeddings locales (multilingual-e5-small) SOLO de textos únicos (200k -> 62k), caché por hash
            2. microgrupos (Leiden sobre kNN)
            3. grafo de microgrupos unido por RESPUESTAS: una respuesta siempre es de la misma narrativa y,
               si tiene contenido propio, de la postura opuesta  -> narrativas = comunidades
            4. postura = bipartición espectral de ese grafo; qué lado afirma: señales locales o profesor LLM
            5. ruido: textos frecuentes con los que nadie discute + microgrupos sin vida de respuestas
            6. respuestas de acompañamiento ("tal cual") heredan narrativa y postura del padre
            7. origen = primer pico real (no el primer comentario suelto); título y frases clave (c-TF-IDF)
       ─► coordinación (SQL)
            sincronía alineada: mismas cuentas, misma publicación, MISMA narrativa y postura, a minutos,
            repetida en varias publicaciones; aristas sin vecinos comunes se descartan (el azar no forma
            triángulos); comunidades densas (Leiden) con rescate del núcleo k-core
       ─► entrega: comentarios.csv, narrativas.csv, cuentas.csv, costo.json (+ dashboard)
```

Si el set casi no trae respuestas, el pipeline lo detecta y pasa a un **modo degradado** por significado
(comunidades de microgrupos + dos bandos por similitud): 32,6/55 en vez de colapsar (E32).

Ideas clave, todas agnósticas del tema:
- **La conversación misma es la etiqueta.** Las respuestas conectan los dos bandos de cada narrativa; no hace falta
  un modelo que entienda postura comentario por comentario.
- **Coordinación = repetición alineada**, no coincidencia. Los picos virales genuinos y los usuarios intensivos
  coinciden con todos; una operación coincide *empujando lo mismo*, una y otra vez, y forma triángulos.
- **El LLM, si está, es profesor y no motor**: ~13 llamadas por corrida (una por narrativa), con caché.

## Almacenamiento: por qué DuckDB + Parquet

- **DuckDB en proceso**: cero servidores, un solo comando reproducible, y SQL columnar vectorizado. Los joins que
  definen la coordinación (pares de cuentas en ventanas de tiempo sobre 200k comentarios -> 2,6 M pares) corren en
  menos de 1 s con *range joins*.
- **Parquet por etapa** (`interim/<set>/*.parquet`): cada etapa deja su contrato en disco (columnar, comprimido,
  tipado), así el pipeline se retoma desde cualquier punto y se inspecciona con SQL.
- **Caché de embeddings por hash del texto normalizado**: un texto repetido nunca se re-embebe, ni entre corridas.
- DuckDB con `memory_limit` y `max_temp_directory_size` acotados: nunca llena el disco.

### Cómo escala a millones de comentarios por día

| Hoy (batch, notebook) | A millones/día |
|---|---|
| CSV -> Parquet | ingesta por stream (Kafka/Redpanda) a Parquet particionado por hora (S3/GCS) |
| DuckDB local | ClickHouse (mismo SQL columnar; la sincronía alineada es un self-join por publicación y ventana) |
| embeddings de textos únicos | servicio de embeddings con caché por hash (la dedup baja el volumen ~3x); ~1.600 textos/s por núcleo GPU-lite |
| Leiden por corrida | asignación incremental: textos nuevos al microgrupo vecino (kNN) y re-agrupamiento por ventana |
| alertas en el dashboard | las mismas reglas como consultas continuas: nueva comunidad con pico real = narrativa emergente; nuevo grupo denso = operación |

Costo marginal de IA por comentario: ~0 (los LLM solo ven una muestra por narrativa).

## Código y librerías preexistentes

Todo el código de este repositorio se escribió durante el hackathon (desde el miércoles 11). Se desarrolló con
asistencia de un asistente de código con IA (Claude Code); el uso de IA dentro del pipeline se reporta en
`entrega/costo.json` (en la configuración por defecto, cero). Librerías públicas usadas (versiones exactas
en `uv.lock`): duckdb, pandas, pyarrow, numpy, scikit-learn, torch, sentence-transformers (modelo
`intfloat/multilingual-e5-small`), python-igraph, leidenalg, anthropic (opcional), pytest. Del desafío se usa su
script oficial de puntaje solo como referencia (`make score-oficial`, clonado en `vendor/`, no versionado).

## Estructura

```
radar/                 código
  stages/              ingest · narrativas · coordinacion · entrega
  narrativas/          grafo, postura, respuestas, origen, descripción
  coordinacion/        señales SQL y detección de grupos
  eval/                réplica del puntaje y validación de robustez
  llm.py · embed.py · texto.py · demo.py · cli.py
tests/                 76 tests (unidades con casos borde + etapas de punta a punta), cobertura 93%
experimentos/          E01–E37: hipótesis, medición y decisión
docs/                  PLAN · EVALUACION · VALIDACION · SINTETICOS · TAREAS · ROADMAP · PITCH
sinteticos/            generadores de sets sintéticos de prueba
config.yaml            todos los parámetros, cada uno con el experimento que lo justifica
```

## Licencia

MIT.
