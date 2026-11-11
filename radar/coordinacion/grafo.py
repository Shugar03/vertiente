"""Grupos de cuentas coordinadas: comunidades densas en el grafo de evidencia."""

from __future__ import annotations

import igraph as ig
import leidenalg as la
import numpy as np
import pandas as pd


def aristas_evidencia(sync: pd.DataFrame, resp: pd.DataFrame, min_sincronias: int, min_sincronia_norm: float) -> pd.DataFrame:
    """Arista = sincronía alineada repetida y relevante para la actividad de ambas cuentas.
    Las respuestas mutuas suman peso a una arista existente (no crean aristas solas: E14 mostró que son ruidosas)."""
    e = sync[(sync["sync"] >= min_sincronias) & (sync["sync_n"] >= min_sincronia_norm)][["x", "y", "sync_n"]].copy()
    if e.empty:
        return e.assign(w=pd.Series(dtype=float))
    e = e.merge(resp, on=["x", "y"], how="left").fillna({"resp": 0})
    e["w"] = e["sync_n"] + 0.5 * np.minimum(e["resp"], 2)
    return e


def detectar_grupos(sync: pd.DataFrame, resp: pd.DataFrame, min_sincronias: int, min_sincronia_norm: float,
                    min_tamano: int, min_densidad: float, seed: int) -> dict[str, str]:
    e = aristas_evidencia(sync, resp, min_sincronias, min_sincronia_norm)
    if e.empty:
        return {}
    nodos = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(e["x"]), nodos.get_indexer(e["y"]))))
    g.es["weight"] = e["w"].tolist()
    memb = np.asarray(la.find_partition(g, la.ModularityVertexPartition, weights="weight", seed=seed).membership)
    grupos: dict[str, str] = {}
    for k in np.unique(memb):
        idx = np.flatnonzero(memb == k)
        # Densidad del grupo completo, sin poda por nodo: las campañas no son camarillas perfectas (E22 refutó la poda).
        if len(idx) < min_tamano or g.induced_subgraph(idx).density() < min_densidad:
            continue
        for i in idx:
            grupos[nodos[i]] = f"g{int(k)}"
    # etiquetas estables y legibles: op01, op02... por tamaño
    orden = pd.Series(grupos).value_counts().index
    renombre = {g_: f"op{i + 1:02d}" for i, g_ in enumerate(orden)}
    return {c: renombre[g_] for c, g_ in grupos.items()}
