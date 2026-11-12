"""Corre el pipeline sobre los sets sintéticos (salida/sinteticos/<set>/) y diagnostica por campaña y por narrativa.

    uv run python -m radar.eval.sinteticos [--sets campanas_nuevas temas_nuevos]

Ver docs/SINTETICOS.md. Los sets los generan sinteticos/generar_*.py (diseñados sin mirar este pipeline).
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd
import yaml

from radar.cli import run
from radar.eval.validar import puntuar

BASE = Path("salida/sinteticos")


def _leer(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def por_campana(datos: Path, salida: Path) -> pd.DataFrame:
    """Por campaña verdadera: cuántas cuentas, cuántas marcadas, en cuántos grupos predichos quedó."""
    verdad = _leer(datos / "verdad" / "cuentas.csv.gz")
    pred = _leer(salida / "cuentas.csv")
    d = verdad.merge(pred, on="cuenta_id", how="left").fillna({"grupo": ""})
    filas = []
    for camp, g in d[d["campana_id"] != ""].groupby("campana_id"):
        marcadas = g[g["grupo"] != ""]
        filas.append({"campana": camp, "cuentas": len(g), "detectadas": len(marcadas),
                      "recall": round(len(marcadas) / len(g), 2),
                      "grupos_predichos": marcadas["grupo"].nunique()})
    falsos = d[(d["campana_id"] == "") & (d["grupo"] != "")]
    filas.append({"campana": "(genuinas marcadas)", "cuentas": int((d["campana_id"] == "").sum()),
                  "detectadas": len(falsos), "recall": None, "grupos_predichos": falsos["grupo"].nunique()})
    return pd.DataFrame(filas)


def por_narrativa(datos: Path, salida: Path) -> pd.DataFrame:
    """Por narrativa verdadera: a qué etiqueta predicha fue la mayoría, pureza y acierto de postura."""
    v = _leer(datos / "verdad" / "comentarios.csv.gz")
    p = _leer(salida / "comentarios.csv")
    d = v.merge(p, on="comentario_id", how="left").fillna({"narrativa": "", "postura_y": ""})
    d = d[d["narrativa_id"] != "ninguna"]
    filas = []
    for n, g in d.groupby("narrativa_id"):
        top = g["narrativa"].value_counts()
        filas.append({"narrativa": n, "comentarios": len(g), "etiqueta": top.index[0],
                      "cobertura": round(top.iloc[0] / len(g), 2),
                      "como_ruido": round((g["narrativa"] == "").mean(), 2),
                      "postura_ok": round((g["postura_x"] == g["postura_y"]).mean(), 2)})
    return pd.DataFrame(filas)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="*")
    ap.add_argument("--config", type=Path, default=Path("config.yaml"))
    a = ap.parse_args()
    cfg = yaml.safe_load(a.config.read_text(encoding="utf-8"))
    sets = a.sets or sorted(p.name for p in BASE.iterdir() if (p / "verdad").is_dir())
    pd.set_option("display.width", 200)
    for nombre in sets:
        datos = BASE / nombre
        salida = BASE / "_salida" / nombre
        c2 = copy.deepcopy(cfg)
        c2["interim_dir"] = str(BASE / "_interim")
        run(datos, salida, c2)
        r = puntuar(datos, salida)
        print(f"\n===== {nombre}: TOTAL {r['total']}/55 (narrativas {r['narr_pts']}, coordinación {r['coord_pts']})")
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})
        print(por_campana(datos, salida).to_string(index=False))
        print(por_narrativa(datos, salida).to_string(index=False))


if __name__ == "__main__":
    main()
