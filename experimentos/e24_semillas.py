"""E24 — (a) sync>=2 con densidad más exigente; (b) semillas sync>=3 + expansión con sync>=2. Sobre variantes de estrés."""
import itertools
import numpy as np, pandas as pd
exec(open("experimentos/e23_coord_robusta.py").read().split("res = []")[0])

def expandir(base, sync, MS, frac):
    if not base: return base
    tam = pd.Series(base).value_counts()
    e = sync[sync.sync >= MS]
    l = pd.concat([e.rename(columns={"x": "c", "y": "m"})[["c", "m"]], e.rename(columns={"y": "c", "x": "m"})[["c", "m"]]])
    l = l[~l.c.isin(base.keys()) & l.m.isin(base.keys())]
    if l.empty: return base
    l["g"] = l.m.map(base); k = l.groupby(["c", "g"]).size().reset_index(name="k"); k["f"] = k.k / k.g.map(tam)
    k = k.sort_values("f", ascending=False).drop_duplicates("c"); k = k[k.f >= frac]
    return {**base, **dict(zip(k.c, k.g))}

def grupos_dens(sync, resp, MS, MN, D):
    e = sync[(sync.sync >= MS) & (sync.sync_n >= MN)]
    if e.empty: return {}
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    m = np.asarray(la.find_partition(g, la.ModularityVertexPartition, seed=42).membership); out = {}
    for k in np.unique(m):
        idx = np.flatnonzero(m == k)
        if len(idx) >= 5 and g.induced_subgraph(idx).density() >= D:
            for i in idx: out[nod[i]] = f"g{k}"
    return out

def evaluar(fn):
    pts = {}
    for v, (syncs, resp, verdad) in datos.items():
        gd = fn(syncs, resp)
        pts[v] = puntuar_coordinacion(verdad.to_dict("records"), [{"cuenta_id": a, "grupo": gd.get(a, "")} for a in verdad.cuenta_id])["puntos"]
    nucleo = [pts[v] for v in VARS if v != "solo_colectivo"]
    return dict(media=np.mean(nucleo), peor=min(nucleo), **pts)

res = []
for W, MN, D in itertools.product([20, 30], [0.15, 0.2], [0.3, 0.4, 0.5]):
    res.append(dict(cfg=f"a W={W} MS=2 MN={MN} D={D}", **evaluar(lambda s, r: grupos_dens(s[W], r, 2, MN, D))))
for W, MN, F in itertools.product([20, 30], [0.1, 0.15], [0.2, 0.3, 0.4, 0.5]):
    res.append(dict(cfg=f"b W={W} seed MS=3 MN={MN} exp>={F}", **evaluar(lambda s, r: expandir(grupos_dens(s[W], r, 3, MN, 0.3), s[W], 2, F))))
R = pd.DataFrame(res).sort_values("media", ascending=False)
pd.set_option("display.width", 250); print(R.head(20).round(2).to_string(index=False))
