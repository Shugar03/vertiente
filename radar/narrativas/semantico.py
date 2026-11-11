"""Modo degradado: narrativas SIN estructura de respuestas (E32).

Si el set casi no trae respuestas, el grafo de respuestas no existe y el método principal colapsa (1,8/55 en E32).
Acá las narrativas salen solo del significado:
  - ruido: microgrupos de reacciones o de preguntas, y microgrupos diminutos;
  - narrativas: comunidades (Leiden) en el grafo kNN de centroides de microgrupos;
  - bandos: dentro de cada narrativa, partición en dos por similitud (2-means sobre centroides).
"""

from __future__ import annotations

import igraph as ig
import leidenalg as la
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from radar.texto import es_pregunta, solo_reaccion


def centroides(c: pd.DataFrame, X: np.ndarray, hashes: list[str], n_micro: int) -> np.ndarray:
    pos = {h: i for i, h in enumerate(hashes)}
    filas = c["texto_hash"].map(pos).to_numpy()
    C = np.zeros((n_micro, X.shape[1]), dtype=np.float32)
    np.add.at(C, c["micro"].to_numpy(), X[filas])
    C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-12
    return C


def microgrupos_ruido_semantico(c: pd.DataFrame, n_micro: int, min_frac_tamano: float) -> np.ndarray:
    g = c.assign(r=c["texto"].map(solo_reaccion), q=c["texto"].map(es_pregunta)).groupby("micro")
    reac = g["r"].mean().reindex(range(n_micro), fill_value=1.0).to_numpy()
    preg = g["q"].mean().reindex(range(n_micro), fill_value=0.0).to_numpy()
    tam = g.size().reindex(range(n_micro), fill_value=0).to_numpy()
    return (reac > 0.5) | (preg > 0.5) | (tam < min_frac_tamano * len(c))


def narrativas_semanticas(C: np.ndarray, ruido: np.ndarray, k: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    n_micro = len(C)
    narr = -np.ones(n_micro, int)
    lado = np.zeros(n_micro, int)
    validos = np.flatnonzero(~ruido)
    if len(validos) == 0:
        return narr, lado
    V = C[validos]
    S = V @ V.T
    np.fill_diagonal(S, -1)
    kk = min(k, len(validos) - 1)
    aristas, pesos = [], []
    if kk > 0:
        vecinos = np.argsort(-S, axis=1)[:, :kk]
        for i, fila in enumerate(vecinos):
            for j in fila:
                aristas.append((i, int(j)))
                pesos.append(max(float(S[i, j]), 1e-6))
    g = ig.Graph(n=len(validos), edges=aristas)
    g.es["weight"] = pesos
    g.simplify(combine_edges="max")
    memb = np.asarray(la.find_partition(g, la.ModularityVertexPartition, weights="weight", seed=seed).membership)
    narr[validos] = memb
    for m in np.unique(memb):
        idx = np.flatnonzero(memb == m)
        if len(idx) >= 2:
            lado[validos[idx]] = KMeans(n_clusters=2, n_init=4, random_state=seed).fit_predict(V[idx])
    return narr, lado
