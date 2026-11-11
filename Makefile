DATOS   ?= datos/practica
SALIDA  ?= salida/$(notdir $(DATOS))
DESAFIO := https://github.com/qualydata-org/desafio-qualydata.git

.PHONY: setup datos run score check entrega test

setup: datos
	uv sync
	# TODO(Fran): pre-descargar modelos locales a modelos/ para no depender de la red el viernes

datos:
	@test -d vendor/desafio || git clone -q --depth 1 $(DESAFIO) vendor/desafio
	@mkdir -p datos && test -e datos/practica || ln -s ../vendor/desafio/datos/practica datos/practica

run:
	uv run python -m radar run --datos $(DATOS) --salida $(SALIDA)

score:
	uv run python vendor/desafio/evaluacion/puntuar.py --verdad $(DATOS)/verdad --entrega $(SALIDA)

check:
	uv run python scripts/check_entrega.py --datos $(DATOS) --entrega $(SALIDA)

# VIERNES: set final -> entrega/ (esta carpeta SÍ se commitea)
entrega:
	$(MAKE) run DATOS=datos/final SALIDA=entrega
	$(MAKE) check DATOS=datos/final SALIDA=entrega

test:
	uv run pytest -q
