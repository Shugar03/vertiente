"""E25 — Limpieza de aristas por vecinos comunes (las aristas de campaña están en triángulos; las genuinas al azar no)."""
import itertools
import numpy as np, pandas as pd
exec(open("experimentos/e23_coord_robusta.py").read().split("res = []")[0])

def grupos_vc(sync, MS, MN, C, D, metodo):
    e = sync[(sync.sync >= MS) & (sync.sync_n >= MN)]
    if e.empty: return {}
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    vec = [set(n) for n in g.neighborhood(mindist=1)]
    keep = [len(vec[a] & vec[b]) >= C for a, b in g.get_edgelist()]
    h = g.subgraph_edges(np.flatnonzero(keep), delete_vertices=False)
    if metodo == "comp":
        m = np.asarray(h.connected_components().membership)
    else:
        m = np.asarray(la.find_partition(h, la.ModularityVertexPartition, seed=42).membership)
    out = {}
    for k in np.unique(m):
        idx = np.flatnonzero(m == k)
        if len(idx) >= 5 and h.induced_subgraph(idx).density() >= D:
            for i in idx: out[nod[i]] = f"g{k}"
    return out

def evaluar(fn):
    pts = {}
    for v, (syncs, resp, verdad) in datos.items():
        gd = fn(syncs)
        pts[v] = puntuar_coordinacion(verdad.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in verdad.cuenta_id])["puntos"]
    nucleo = [pts[v] for v in VARS if v != "solo_colectivo"]
    return dict(media=np.mean(nucleo), peor=min(nucleo), **pts)

res = []
for W, MS, MN, C, D, met in itertools.product([20, 30, 45], [2], [0.1, 0.15, 0.2], [2, 3, 5], [0.2, 0.3], ["comp", "mod"]):
    res.append(dict(cfg=f"W={W} MS={MS} MN={MN} C={C} D={D} {met}", **evaluar(lambda s: grupos_vc(s[W], MS, MN, C, D, met))))
R = pd.DataFrame(res).sort_values("media", ascending=False)
pd.set_option("display.width", 250); print(R.head(20).round(2).to_string(index=False))
R.to_csv("salida/validacion/e25.csv", index=False)
