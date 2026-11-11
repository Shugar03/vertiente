"""E28 — Diagnóstico del orden que falla: ¿la campaña se parte o se mezcla?"""
import numpy as np, pandas as pd, igraph as ig, leidenalg as la
exec(open("experimentos/e26_estabilidad.py").read().split("def detectar")[0])
camp = dict(zip(v.cuenta_id, v.campana_id))
for r in [0, 7]:
    e = e0.sample(frac=1, random_state=r)
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    m = np.asarray(la.find_partition(g, la.ModularityVertexPartition, seed=42).membership)
    print(f"orden {r}: nodos={len(nod)} aristas={len(e)} comunidades={len(np.unique(m))}")
    for k in np.unique(m):
        idx = np.flatnonzero(m == k); cs = pd.Series([camp.get(nod[i], "") for i in idx]).value_counts().to_dict()
        if any(c for c in cs if c):
            print(f"   k={k} n={len(idx)} dens={g.induced_subgraph(idx).density():.3f} {cs}")
