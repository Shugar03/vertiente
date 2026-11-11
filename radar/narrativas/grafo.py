"""Grafo de similitud entre textos y microgrupos (Leiden)."""

from __future__ import annotations

import igraph as ig
import leidenalg as la
import numpy as np
import torch

from radar.embed import dispositivo as resolver_dispositivo


def knn_aristas(X: np.ndarray, k: int, dispositivo: str = "auto", bloque: int = 4096):
    """k vecinos más cercanos por coseno (X normalizado). Devuelve listas src, dst, peso."""
    dev = resolver_dispositivo(dispositivo)
    Xt = torch.from_numpy(np.ascontiguousarray(X, dtype=np.float32)).to(dev)
    k = min(k, len(X) - 1)
    src, dst, w = [], [], []
    for i in range(0, len(Xt), bloque):
        S = Xt[i:i + bloque] @ Xt.T
        filas = torch.arange(S.shape[0], device=dev)
        S[filas, filas + i] = -1.0  # sin auto-aristas
        v, idx = S.topk(k, dim=1)
        src.append(np.repeat(np.arange(i, i + S.shape[0]), k))
        dst.append(idx.flatten().cpu().numpy())
        w.append(v.flatten().cpu().numpy())
    return np.concatenate(src), np.concatenate(dst), np.concatenate(w)


def microgrupos(n: int, src, dst, peso, resolucion: float, seed: int) -> np.ndarray:
    g = ig.Graph(n=n, edges=list(zip(map(int, src), map(int, dst))), directed=False)
    g.es["weight"] = [float(x) for x in peso]
    g.simplify(combine_edges="max")
    part = la.find_partition(g, la.RBConfigurationVertexPartition, weights="weight",
                             resolution_parameter=resolucion, seed=seed)
    return np.asarray(part.membership)
