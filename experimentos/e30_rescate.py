"""E30 — Núcleo k-core solo como RESCATE de comunidades que no pasan la densidad."""
import numpy as np, pandas as pd, igraph as ig, leidenalg as la
exec(open("experimentos/e29_kcore_relativo.py").read().split("for F in")[0])
def detectar(e, F, D=0.3, MINN=5):
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    m = np.asarray(la.find_partition(g, la.ModularityVertexPartition, seed=42).membership); out = {}
    for k in np.unique(m):
        idx = np.flatnonzero(m == k)
        if len(idx) < MINN: continue
        if g.induced_subgraph(idx).density() < D:
            core = np.asarray(g.induced_subgraph(idx).coreness()); idx = idx[core >= F * core.max()]
        if len(idx) >= MINN and g.induced_subgraph(idx).density() >= D:
            for i in idx: out[nod[i]] = f"g{k}"
    return out
for F in [0.4, 0.5, 0.6, 0.7, 0.8]:
    syncs, resp, verdad = datos["completo"]; e0 = aristas(syncs[30]); est = []
    for r in range(20):
        gd = detectar(e0.sample(frac=1, random_state=r), F)
        est.append(puntuar_coordinacion(verdad.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in verdad.cuenta_id])["puntos"])
    var = {}
    for vn, (syncs, resp, verdad) in datos.items():
        gd = detectar(aristas(syncs[30]), F)
        var[vn] = puntuar_coordinacion(verdad.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in verdad.cuenta_id])["puntos"]
    nucleo = [var[x] for x in VARS if x != "solo_colectivo"]
    print(f"rescate F={F}: estabilidad min={min(est):.2f} media={np.mean(est):.2f} | variantes media={np.mean(nucleo):.2f} peor={min(nucleo):.2f}", {k: round(x, 1) for k, x in var.items()})
