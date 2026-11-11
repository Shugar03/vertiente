"""Respuestas: textos de acompañamiento ("tal cual", "coincido") y herencia de narrativa/postura del padre."""

from __future__ import annotations

import numpy as np
import pandas as pd


def umbral_frecuencia_ruido(tasa_participacion: float, alfa: float) -> int:
    """Frecuencia mínima para declarar ruido a un texto que nunca participa de respuestas.

    Si un comentario con narrativa participa de una respuesta con probabilidad p, un texto con k apariciones y cero
    participación ocurre por azar con prob (1-p)^k. Se exige que eso sea < alfa.
    """
    if tasa_participacion <= 0:
        return 10**9
    return int(np.ceil(np.log(alfa) / np.log(1 - tasa_participacion)))


def textos_sin_respuestas(c: pd.DataFrame, min_frecuencia: int) -> set[str]:
    """Textos frecuentes que nunca responden ni reciben respuesta: nadie discute con ellos (saludos, preguntas sueltas)."""
    respondidos = set(c["respuesta_a"].dropna())
    participa = c["respuesta_a"].notna() | c["comentario_id"].isin(respondidos)
    g = c.assign(p=participa).groupby("texto_hash")["p"].agg(["size", "sum"])
    return set(g[(g["size"] >= min_frecuencia) & (g["sum"] == 0)].index)


def tasa_participacion(c: pd.DataFrame) -> float:
    respondidos = set(c["respuesta_a"].dropna())
    return float((c["respuesta_a"].notna() | c["comentario_id"].isin(respondidos)).mean())


def textos_acompanamiento(c: pd.DataFrame, min_dispersion: int, max_palabras: int) -> set[str]:
    """Textos cortos que, como respuesta, aparecen colgados de muchos microgrupos distintos: no tienen tema propio.

    `c`: comentario_id, respuesta_a, texto_hash, texto_norm, micro.
    """
    micro_de = dict(zip(c["comentario_id"], c["micro"]))
    resp = c[c["respuesta_a"].notna()]
    dispersion = resp.assign(mp=resp["respuesta_a"].map(micro_de)).groupby("texto_hash")["mp"].nunique()
    cortos = set(c.loc[c["texto_norm"].str.split().str.len().fillna(0) <= max_palabras, "texto_hash"])
    return set(dispersion[dispersion >= min_dispersion].index) & cortos


def heredar(c: pd.DataFrame, acomp: set[str], profundidad_max: int) -> pd.DataFrame:
    """Respuestas de acompañamiento heredan narr y lado del padre (cadenas incluidas). Sin padre => ruido (-1).

    `c`: comentario_id, respuesta_a, texto_hash, narr, lado. Devuelve copia con narr/lado resueltos y columna `heredado`.
    """
    out = c.copy()
    idx = {cid: i for i, cid in enumerate(out["comentario_id"])}
    narr = out["narr"].to_numpy().copy()
    lado = out["lado"].to_numpy().copy()
    es_ac = out["texto_hash"].isin(acomp).to_numpy()
    padre = out["respuesta_a"].to_numpy()
    heredado = np.zeros(len(out), bool)
    resuelto = ~es_ac.copy()

    for i in np.flatnonzero(es_ac):
        cadena, j = [], i
        while es_ac[j] and not resuelto[j] and len(cadena) <= profundidad_max:
            cadena.append(j)
            p = padre[j]
            if p is None or (isinstance(p, float) and np.isnan(p)) or p not in idx:
                j = -1
                break
            j = idx[p]
        n_, l_ = (narr[j], lado[j]) if j >= 0 and resuelto[j] else (-1, -1)
        for k in cadena:
            narr[k], lado[k], resuelto[k] = n_, l_, True
            heredado[k] = n_ >= 0
    out["narr"], out["lado"], out["heredado"] = narr, lado, heredado
    return out
