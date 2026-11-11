# Radar — narrativas y coordinación a escala

Hackathon Argentina Space 2026 · Desafío QualyData (Big Data) · Salta, 11–13 nov.

Pipeline que, sobre cientos de miles de comentarios, **descubre las narrativas que circulan** (con su postura y su
origen) y **detecta las operaciones coordinadas** que las empujan — rápido, barato y sin depender de los temas del
set de práctica.

## Cómo correrlo

```bash
make setup                      # entorno (uv), modelos locales, datos de práctica y script oficial de puntaje
make run DATOS=datos/practica   # pipeline completo -> salida/practica/
make score                      # puntaje automático oficial sobre práctica
make check                      # valida el formato de la entrega

make entrega                    # VIERNES: corre sobre datos/final/ y escribe entrega/
```

Un solo comando de punta a punta: `make entrega`. Funciona sin clave de LLM (usa `cache/llm/` y reglas de respaldo).

## Stack

- **Python 3.12** + **uv** (versiones fijadas en `uv.lock`).
- **DuckDB sobre Parquet** para almacenamiento y features (ver "Almacenamiento").
- **Local (tipo BERT):** embeddings (multilingual-e5-small o EmbeddingGemma 2, se decide en Fase 0),
  clasificadores de decisión sobre embeddings, NLI multilingüe para casos dudosos.
- **LLM por API, solo como "profesor":** nombra/une grupos y etiqueta una muestra; nunca comentario por comentario.

## Almacenamiento

_TODO (Fran): por qué DuckDB + Parquet particionado por día, y cómo escala a millones de comentarios/día._

## Código y librerías preexistentes

_TODO: listar librerías (y versiones) y cualquier código previo al evento. El código de este repo se escribió durante
el hackathon._

## Documentación

- [docs/PLAN.md](docs/PLAN.md) — mapa del sistema, contratos, casos borde, velocidad y confiabilidad
- [docs/EVALUACION.md](docs/EVALUACION.md) — criterios de evaluación y requisitos excluyentes
- [docs/TAREAS.md](docs/TAREAS.md) — división tentativa de tareas
- [docs/ROADMAP.md](docs/ROADMAP.md) — fases y criterios de "listo"

## Licencia

MIT (sujeto a las bases del hackathon).
