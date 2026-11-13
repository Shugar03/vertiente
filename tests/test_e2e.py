"""Punta a punta sobre el set de práctica real (se salta si no está bajado: `make datos`)."""
import copy
from pathlib import Path

import pytest
import yaml

from radar.cli import run, score
from scripts.check_entrega import validar

PRACTICA = Path("datos/practica")


@pytest.mark.skipif(not (PRACTICA / "comentarios.csv.gz").exists(), reason="falta datos/practica (make datos)")
def test_pipeline_completo_valido_y_con_puntaje(tmp_path):
    cfg = copy.deepcopy(yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8")))
    cfg["interim_dir"] = str(tmp_path / "interim")
    etapas = run(PRACTICA, tmp_path / "entrega", cfg)
    assert validar(PRACTICA, tmp_path / "entrega") == []
    r = score(PRACTICA / "verdad", tmp_path / "entrega")
    assert r["narrativas"]["puntos"] >= 28
    assert r["coordinacion"]["puntos"] >= 22
    assert etapas["costo"]["comentarios_procesados"] == 200_000
