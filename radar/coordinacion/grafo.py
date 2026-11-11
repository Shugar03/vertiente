"""Grupos de cuentas coordinadas: comunidades densas en el grafo de sincronía alineada.

Selección del método (experimentos E20–E25, optimizando el promedio y el peor caso sobre variantes de estrés:
submuestreo, medio período, sin un tema):
  1. arista = >= 2 sincronías alineadas en publicaciones distintas, relevantes para la cuenta menos activa;
  2. se quitan las aristas sin vecinos comunes: las operaciones forman triángulos, el azar genuino no (E25:
     peor caso 0,7 -> 21,4 puntos);
  3. comunidades por modularidad (Leiden) y filtro de densidad del grupo completo (la poda por nodo, E22, falló);
  4. si una comunidad no alcanza la densidad porque se le pegaron cuentas genuinas activas, se RESCATA su núcleo
     k-core (coreness >= 0,5·máx) en vez de descartarla (E28–E30: peor caso por orden de filas 20,9 -> 23,5).
Las aristas se ordenan antes de armar el grafo: el resultado no depende del orden en que DuckDB devuelve filas.
"""

from __future__ import annotations

import igraph as ig
import leidenalg as la
import numpy as np
import pandas as pd


def filtrar_vecinos_comunes(e: pd.DataFrame, min_comunes: int) -> pd.DataFrame:
    """Conserva las aristas (x, y) cuyos extremos comparten al menos `min_comunes` vecinos."""
    if e.empty:
        return e
    nodos = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(e["x"]), nodos.get_indexer(e["y"]))))
    vecinos = [set(v) for v in g.neighborhood(mindist=1)]
    comunes = np.array([len(vecinos[a] & vecinos[b]) for a, b in g.get_edgelist()])
    return e[comunes >= min_comunes]


def nucleo_si_hace_falta(g: ig.Graph, idx: np.ndarray, min_densidad: float, fraccion_nucleo: float) -> np.ndarray:
    """La comunidad completa si es densa; si no, su núcleo k-core relativo (puede quedar vacío o chico)."""
    sub = g.induced_subgraph(idx)
    if sub.density() >= min_densidad:
        return idx
    core = np.asarray(sub.coreness())
    return idx[core >= fraccion_nucleo * core.max()]


def detectar_grupos(sync: pd.DataFrame, min_sincronias: int, min_sincronia_norm: float, min_vecinos_comunes: int,
                    min_tamano: int, min_densidad: float, seed: int, fraccion_nucleo: float = 0.5) -> dict[str, str]:
    """`sync`: x, y, sync, sync_n. Devuelve {cuenta_id: 'opNN'} solo para cuentas en operaciones detectadas."""
    e = sync[(sync["sync"] >= min_sincronias) & (sync["sync_n"] >= min_sincronia_norm)][["x", "y"]]
    e = e.sort_values(["x", "y"]).reset_index(drop=True)  # determinismo
    e = filtrar_vecinos_comunes(e, min_vecinos_comunes)
    if e.empty:
        return {}
    nodos = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(e["x"]), nodos.get_indexer(e["y"]))))
    memb = np.asarray(la.find_partition(g, la.ModularityVertexPartition, seed=seed).membership)
    grupos: dict[str, str] = {}
    for k in np.unique(memb):
        idx = np.flatnonzero(memb == k)
        if len(idx) < min_tamano:
            continue
        idx = nucleo_si_hace_falta(g, idx, min_densidad, fraccion_nucleo)
        if len(idx) < min_tamano or g.induced_subgraph(idx).density() < min_densidad:
            continue
        for i in idx:
            grupos[nodos[i]] = f"g{int(k)}"
    if not grupos:
        return {}
    orden = pd.Series(grupos).value_counts().index  # op01 = la más grande
    renombre = {g_: f"op{i + 1:02d}" for i, g_ in enumerate(orden)}
    return {c: renombre[g_] for c, g_ in grupos.items()}
