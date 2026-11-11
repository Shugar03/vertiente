import gzip

import pandas as pd

from radar.eval.sinteticos import por_campana, por_narrativa


def _gz(df, p):
    with gzip.open(p, "wt", encoding="utf-8") as f:
        df.to_csv(f, index=False)


def test_diagnostico_por_campana_y_narrativa(tmp_path):
    d, s = tmp_path / "d", tmp_path / "s"
    (d / "verdad").mkdir(parents=True)
    s.mkdir()
    _gz(pd.DataFrame({"cuenta_id": ["a", "b", "c", "z"], "campana_id": ["K1", "K1", "K2", ""]}), d / "verdad" / "cuentas.csv.gz")
    pd.DataFrame({"cuenta_id": ["a", "b", "c", "z"], "grupo": ["op01", "", "op02", "op02"]}).to_csv(s / "cuentas.csv", index=False)
    _gz(pd.DataFrame({"comentario_id": ["1", "2", "3"], "narrativa_id": ["X", "X", "ninguna"],
                      "postura": ["apoya", "rechaza", ""]}), d / "verdad" / "comentarios.csv.gz")
    pd.DataFrame({"comentario_id": ["1", "2", "3"], "narrativa": ["n0", "n0", ""],
                  "postura": ["apoya", "apoya", ""]}).to_csv(s / "comentarios.csv", index=False)
    c = por_campana(d, s).set_index("campana")
    assert c.loc["K1", "detectadas"] == 1 and c.loc["K2", "recall"] == 1.0
    assert c.loc["(genuinas marcadas)", "detectadas"] == 1
    n = por_narrativa(d, s).set_index("narrativa")
    assert n.loc["X", "cobertura"] == 1.0 and n.loc["X", "postura_ok"] == 0.5
