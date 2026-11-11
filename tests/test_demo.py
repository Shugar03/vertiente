import json

import pandas as pd

from radar.demo import datos, render


def test_dashboard_autocontenido(tmp_path):
    i = tmp_path
    ts = pd.to_datetime(["2026-09-01T10:00:00Z", "2026-09-03T10:00:00Z", "2026-09-03T11:00:00Z"])
    pd.DataFrame({"comentario_id": ["a", "b", "c"], "ts": ts}).to_parquet(i / "comentarios.parquet")
    pd.DataFrame({"comentario_id": ["a", "b", "c"], "narrativa": ["n00", "n00", ""],
                  "postura": ["apoya", "rechaza", ""]}).to_parquet(i / "narrativas_asig.parquet")
    pd.DataFrame({"narrativa": ["n00"], "titulo": ["Algo <script>"], "frases_clave": ["x|y"],
                  "fecha_origen": [pd.Timestamp("2026-09-03T07:00:00-03:00")], "apoya": [1], "rechaza": [1],
                  "total": [2]}).to_parquet(i / "narrativas_meta.parquet")
    pd.DataFrame({"grupo": ["op01"], "cuentas": [5], "comentarios": [9], "narrativa": ["n00"], "postura": ["apoya"],
                  "foco": [0.9], "antiguedad_mediana_dias": [3.0], "frac_nocturna": [0.0],
                  "primera_actividad": [ts[1]]}).to_parquet(i / "operaciones_meta.parquet")
    d = datos(i)
    assert d["narrativas"][0]["emergente"] is True
    assert sum(d["narrativas"][0]["s_apoya"]) == 1 and sum(d["narrativas"][0]["s_rechaza"]) == 1
    assert [a["tipo"] for a in d["alertas"]] == ["Narrativa emergente", "Operación coordinada"]
    html = render(d)
    assert "<script src=" not in html and "http" not in html.split("<script>")[1]   # sin dependencias externas
    assert "</script>" not in json.dumps(d).replace("</", "<\\/")
