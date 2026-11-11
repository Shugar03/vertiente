"""E27 — Si una comunidad no alcanza la densidad, re-particionarla recursivamente en vez de descartarla."""
import numpy as np, pandas as pd, igraph as ig, leidenalg as la
exec(open("experimentos/e26_estabilidad.py").read().split("def detectar")[0])
def comunidades_densas(g, idx, D, MINN, seed, prof=0):
    if len(idx) < MINN: return []
    sub = g.induced_subgraph(idx)
    if sub.density() >= D: return [idx]
    if prof >= 4: return []
    m = np.asarray(la.find_partition(sub, la.ModularityVertexPartition, seed=seed).membership)
    if len(np.unique(m)) == 1: return []
    out = []
    for k in np.unique(m): out += comunidades_densas(g, idx[m == k], D, MINN, seed, prof + 1)
    return out
def detectar(e):
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    m = np.asarray(la.find_partition(g, la.ModularityVertexPartition, seed=42).membership); out = {}
    for k in np.unique(m):
        for j, idx in enumerate(comunidades_densas(g, np.flatnonzero(m == k), 0.3, 5, 42)):
            for i in idx: out[nod[i]] = f"{k}_{j}"
    return out
pts = []
for r in range(20):
    gd = detectar(e0.sample(frac=1, random_state=r))
    pts.append(puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in v.cuenta_id])["puntos"])
print("recursivo min=%.2f media=%.2f max=%.2f" % (min(pts), np.mean(pts), max(pts)), [round(p, 1) for p in pts])
