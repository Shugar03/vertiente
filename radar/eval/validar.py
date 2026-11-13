"""Validación de robustez y generalización sobre el set de práctica.

El set final trae OTROS temas, narrativas y campañas. No podemos verlo, pero sí podemos estresar el pipeline con
variantes del set de práctica que imitan lo que puede cambiar:

  completo       línea de referencia
  sin_<tema>     se quita un tema entero (2 de 3 temas): ¿depende de cuántos temas hay?
  solo_<tema>    un solo tema: menos narrativas, más parecidas entre sí
  submuestra75   75% de los comentarios al azar (menos volumen, respuestas huérfanas)
  primera_mitad  primeros 7 días (las emergentes tardías no existen)
  ensuciado      typos, ids duplicados, fechas rotas, me_gusta inválidos, filas desordenadas
  semilla_<n>    otra semilla aleatoria (estabilidad de Leiden)

El tema de cada publicación se toma de la verdad SOLO para armar las variantes; el pipeline nunca lo ve.
Uso: python -m radar.eval.validar --datos datos/practica
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import random
import shutil
import time
from pathlib import Path

import pandas as pd
import yaml

from radar.cli import run
from radar.eval.puntaje import puntuar_coordinacion, puntuar_narrativas

TEMAS = {"L": "litio", "B": "colectivo", "H": "hospital"}


def _leer(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def _escribir_gz(df: pd.DataFrame, p: Path) -> None:
    with gzip.open(p, "wt", encoding="utf-8", newline="") as f:
        df.to_csv(f, index=False)


def _tema_por_publicacion(datos: Path) -> pd.Series:
    c = _leer(datos / "comentarios.csv.gz")[["comentario_id", "publicacion_id"]]
    v = _leer(datos / "verdad" / "comentarios.csv.gz")
    d = c.merge(v, on="comentario_id")
    d = d[d["narrativa_id"] != "ninguna"]
    return d.assign(t=d["narrativa_id"].str[0]).groupby("publicacion_id")["t"].agg(lambda s: s.mode().iloc[0])


def armar_variante(datos: Path, destino: Path, filtro_com, ensuciar: bool = False, seed: int = 0) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "verdad").mkdir(exist_ok=True)
    com = _leer(datos / "comentarios.csv.gz")
    com = filtro_com(com)
    ids = set(com["comentario_id"])
    cuentas_usadas = set(com["cuenta_id"])
    pubs = set(com["publicacion_id"])
    if ensuciar:
        com = _ensuciar(com, seed)
    _escribir_gz(com, destino / "comentarios.csv.gz")
    _escribir_gz(_leer(datos / "cuentas.csv.gz").query("cuenta_id in @cuentas_usadas"), destino / "cuentas.csv.gz")
    _escribir_gz(_leer(datos / "publicaciones.csv.gz").query("publicacion_id in @pubs"), destino / "publicaciones.csv.gz")
    shutil.copy(datos / "fuentes.csv", destino / "fuentes.csv")
    vc = _leer(datos / "verdad" / "comentarios.csv.gz")
    _escribir_gz(vc[vc["comentario_id"].isin(ids)], destino / "verdad" / "comentarios.csv.gz")
    va = _leer(datos / "verdad" / "cuentas.csv.gz")
    _escribir_gz(va[va["cuenta_id"].isin(cuentas_usadas)], destino / "verdad" / "cuentas.csv.gz")
    vn = _leer(datos / "verdad" / "narrativas.csv")
    presentes = set(vc.loc[vc["comentario_id"].isin(ids), "narrativa_id"])
    vn[vn["narrativa_id"].isin(presentes)].to_csv(destino / "verdad" / "narrativas.csv", index=False)
    return destino


def _ensuciar(com: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    com = com.copy()
    n = len(com)
    idx = rng.sample(range(n), n // 50)  # 2% con typos (intercambio de letras)
    for i in idx:
        t = com.at[i, "texto"]
        if len(t) > 6:
            j = rng.randrange(1, len(t) - 2)
            com.at[i, "texto"] = t[:j] + t[j + 1] + t[j] + t[j + 2:]
    for i in rng.sample(range(n), n // 500):
        com.at[i, "me_gusta"] = "N/A"
    for i in rng.sample(range(n), n // 1000):
        com.at[i, "fecha"] = "fecha-invalida"
    dup = com.sample(n // 1000, random_state=seed)
    return pd.concat([com, dup]).sample(frac=1, random_state=seed).reset_index(drop=True)


def puntuar(datos: Path, salida: Path) -> dict:
    v = datos / "verdad"
    n = puntuar_narrativas(_leer(v / "comentarios.csv.gz").to_dict("records"), _leer(v / "narrativas.csv").to_dict("records"),
                           _leer(salida / "comentarios.csv").to_dict("records"), _leer(salida / "narrativas.csv").to_dict("records"))
    c = puntuar_coordinacion(_leer(v / "cuentas.csv.gz").to_dict("records"), _leer(salida / "cuentas.csv").to_dict("records"))
    return {"bcubed": n["bcubed_f1"], "ruido": n["ruido_f1"], "postura": n["postura_macro_f1"], "origen": n["origen"],
            "narr_pts": n["puntos"], "coord_P": c["precision"], "coord_R": c["recall"], "grupos": c["grupos_bcubed_f1"],
            "coord_pts": c["puntos"], "total": round(n["puntos"] + c["puntos"], 2)}


def variantes(datos: Path) -> dict:
    tema = _tema_por_publicacion(datos)
    out = {"completo": lambda c: c}
    for t in TEMAS:
        out[f"sin_{TEMAS[t]}"] = lambda c, t=t: c[c["publicacion_id"].map(tema) != t]
        out[f"solo_{TEMAS[t]}"] = lambda c, t=t: c[c["publicacion_id"].map(tema) == t]
    out["submuestra75"] = lambda c: c.sample(frac=0.75, random_state=7).sort_index()
    out["primera_mitad"] = lambda c: c[c["fecha"] < "2026-09-08"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", type=Path, default=Path("datos/practica"))
    ap.add_argument("--base", type=Path, default=Path("salida/validacion"))
    ap.add_argument("--config", type=Path, default=Path("config.yaml"))
    ap.add_argument("--solo", nargs="*")
    a = ap.parse_args()
    cfg = yaml.safe_load(a.config.read_text(encoding="utf-8"))
    filas = []
    casos = [(k, f, False, cfg["seed"]) for k, f in variantes(a.datos).items()]
    casos += [("ensuciado", lambda c: c, True, cfg["seed"]), ("semilla_7", lambda c: c, False, 7),
              ("semilla_123", lambda c: c, False, 123)]
    for nombre, filtro, sucio, seed in casos:
        if a.solo and nombre not in a.solo:
            continue
        d = armar_variante(a.datos, a.base / "datos" / nombre, filtro, ensuciar=sucio, seed=seed)
        c2 = copy.deepcopy(cfg)
        c2["seed"] = seed
        c2["interim_dir"] = str(a.base / "interim")
        t0 = time.perf_counter()
        run(d, a.base / "salida" / nombre, c2)
        fila = {"variante": nombre, "segundos": round(time.perf_counter() - t0, 1), **puntuar(d, a.base / "salida" / nombre)}
        print(json.dumps(fila, ensure_ascii=False), flush=True)
        filas.append(fila)
    df = pd.DataFrame(filas).round(3)
    df.to_csv(a.base / "resultados.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
