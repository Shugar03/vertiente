import json

import pandas as pd
import pytest

from radar.stages import entrega


@pytest.fixture
def interim(tmp_path):
    i = tmp_path / "interim"
    i.mkdir()
    pd.DataFrame({"comentario_id": ["c1", "c2", "c3"], "cuenta_id": ["u1", "u2", "u3"],
                  "ts": pd.to_datetime(["2026-09-01T10:00:00Z"] * 3)}).to_parquet(i / "comentarios.parquet")
    pd.DataFrame({"cuenta_id": ["u1", "u2", "u3", "u4"]}).to_parquet(i / "cuentas.parquet")
    pd.DataFrame({"comentario_id": ["c1", "c2"], "narrativa": ["n00", ""], "postura": ["rechaza", ""],
                  "micro": [0, 1], "heredado": [False, False]}).to_parquet(i / "narrativas_asig.parquet")
    pd.DataFrame({"narrativa": ["n00"], "titulo": ["Algo, con coma"], "frases_clave": ["a|b"],
                  "fecha_origen": [pd.Timestamp("2026-09-01T07:00:00-03:00")],
                  "apoya": [0], "rechaza": [1], "total": [1]}).to_parquet(i / "narrativas_meta.parquet")
    pd.DataFrame({"cuenta_id": ["u2"], "grupo": ["op01"]}).to_parquet(i / "grupos.parquet")
    return i


def test_escribe_los_cuatro_archivos_validos(interim, tmp_path):
    out = tmp_path / "entrega"
    entrega.run(interim, out, {"llm": {}}, segundos=12.5, uso_llm={"tokens": 1000, "usd": 0.01})
    com = pd.read_csv(out / "comentarios.csv", dtype=str, keep_default_na=False)
    assert com["comentario_id"].tolist() == ["c1", "c2", "c3"]          # todos, incluso c3 sin asignación
    assert com.loc[com.comentario_id == "c3", "narrativa"].item() == ""
    cue = pd.read_csv(out / "cuentas.csv", dtype=str, keep_default_na=False)
    assert set(cue["cuenta_id"]) == {"u1", "u2", "u3", "u4"}
    assert cue.loc[cue.cuenta_id == "u2", "grupo"].item() == "op01"
    nar = pd.read_csv(out / "narrativas.csv", dtype=str, keep_default_na=False)
    assert nar["fecha_origen"].item() == "2026-09-01T07:00:00-03:00"
    assert not (out / "comentarios.csv").read_bytes().startswith(b"\xef\xbb\xbf")
    costo = json.loads((out / "costo.json").read_text(encoding="utf-8"))
    assert costo["comentarios_procesados"] == 3 and costo["tokens_ia"] == 1000
    assert costo["usd_por_mil_comentarios"] == pytest.approx(0.01 / 3 * 1000, rel=1e-3)
    assert {"segundos", "hardware", "almacenamiento", "notas", "usd_ia"} <= set(costo)
