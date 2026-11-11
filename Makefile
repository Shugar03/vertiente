DATOS   ?= datos/practica
SALIDA  ?= salida/$(notdir $(DATOS))
DESAFIO := https://github.com/qualydata-org/desafio-qualydata.git
MODELO  := intfloat/multilingual-e5-small

.PHONY: setup datos modelos run score score-oficial check entrega test validar demo limpiar

setup: datos
	uv sync
	$(MAKE) modelos

# Baja el modelo de embeddings a la caché local para no depender de la red el viernes.
modelos:
	uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('$(MODELO)')"

datos:
	@test -d vendor/desafio || git clone -q --depth 1 $(DESAFIO) vendor/desafio
	@mkdir -p datos && test -e datos/practica || ln -s ../vendor/desafio/datos/practica datos/practica

run:
	uv run python -m radar run --datos $(DATOS) --salida $(SALIDA)

# Puntaje local con la réplica del script oficial (radar/eval/puntaje.py).
score:
	uv run python -m radar score --verdad $(DATOS)/verdad --entrega $(SALIDA)

# Puntaje con el script oficial del desafío (fuente de verdad).
score-oficial:
	uv run python vendor/desafio/evaluacion/puntuar.py --verdad $(DATOS)/verdad --entrega $(SALIDA)

check:
	uv run python scripts/check_entrega.py --datos $(DATOS) --entrega $(SALIDA)

# VIERNES: set final -> entrega/ (esta carpeta SÍ se commitea)
entrega:
	$(MAKE) run DATOS=datos/final SALIDA=entrega
	$(MAKE) check DATOS=datos/final SALIDA=entrega

test:
	uv run pytest -q

# Validación de robustez/generalización (dejar un tema afuera, submuestreo, datos ensuciados).
validar:
	uv run python -m radar.eval.validar --datos $(DATOS)

# Dashboard estático a partir de la última corrida.
demo:
	uv run python -m radar.demo --interim interim/$(notdir $(DATOS)) --salida $(SALIDA)/dashboard.html

limpiar:
	rm -rf interim/*/duckdb_tmp salida
