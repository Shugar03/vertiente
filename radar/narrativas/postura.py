"""Postura: bipartición espectral del grafo de inversión y elección del lado que apoya.

Una respuesta con contenido propio contradice a su padre (misma narrativa, postura opuesta). Entonces, dentro de
una narrativa, el grafo de microgrupos unidos por respuestas es (casi) bipartito: cada lado es una postura.
El autovector del menor autovalor de la matriz de adyacencia normalizada da esa bipartición, y tolera aristas ruidosas.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def bipartir(nodos: list[int], aristas: dict[tuple[int, int], float]) -> dict[int, int]:
    if len(nodos) == 1:
        return {nodos[0]: 0}
    pos = {v: i for i, v in enumerate(nodos)}
    W = np.zeros((len(nodos), len(nodos)))
    for (a, b), w in aristas.items():
        if a in pos and b in pos and a != b:
            W[pos[a], pos[b]] += w
            W[pos[b], pos[a]] += w
    d = W.sum(1) + 1e-9
    N = W / np.sqrt(np.outer(d, d))
    _, vecs = np.linalg.eigh(N)
    s = vecs[:, 0]
    return {v: int(s[pos[v]] > 0) for v in nodos}


_REFUTACION = re.compile(r"\b(?:no|nunca|nadie|nada|mentira|falso|verso|exager\w*|invent\w*)\b")
ESCALA_RESPUESTAS = 0.02   # E19: diferencia de proporción de respuestas que ya es concluyente
ESCALA_REFUTACION = 0.30   # E19: diferencia de tasa de negación/refutación concluyente
PESO_REFUTACION = 0.5      # la refutación solo desempata cuando las respuestas no deciden


def lado_apoya(nucleo: pd.DataFrame) -> dict[int, int]:
    """Elige, por narrativa, el lado que AFIRMA (postura "apoya"). Sin LLM.

    Señales (E05/E19), ambas agnósticas del tema:
      1. quien afirma recibe el debate: su lado tiene MENOR proporción de comentarios que son respuestas;
      2. quien rechaza niega/refuta más ("no", "mentira", "nadie"...). Pesa la mitad: solo desempata.
    Puntaje > 0 => el lado 0 apoya. Con LLM disponible, este juicio lo reemplaza el profesor.

    `nucleo`: narr, lado, es_respuesta, texto_norm (solo comentarios con contenido propio).
    """
    d = nucleo.assign(refuta=nucleo["texto_norm"].str.contains(_REFUTACION))
    st = d.groupby(["narr", "lado"])[["es_respuesta", "refuta"]].mean()
    out = {}
    for n in st.index.get_level_values(0).unique():
        s = st.loc[n]
        if len(s) < 2:
            out[int(n)] = int(s.index[0])
            continue
        d_resp = s.loc[1, "es_respuesta"] - s.loc[0, "es_respuesta"]
        d_ref = s.loc[1, "refuta"] - s.loc[0, "refuta"]
        puntaje = np.clip(d_resp / ESCALA_RESPUESTAS, -1, 1) + PESO_REFUTACION * np.clip(d_ref / ESCALA_REFUTACION, -1, 1)
        out[int(n)] = 0 if puntaje >= 0 else 1
    return out
