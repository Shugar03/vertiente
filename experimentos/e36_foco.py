"""E36 — Vía complementaria para campañas que rotan subgrupos: entre cuentas con FOCO alto (percentil del set) en la
misma narrativa+postura, una coincidencia alineada por par alcanza; grupos densos se suman a los del detector actual."""
import itertools, yaml
from pathlib import Path
import numpy as np, pandas as pd, igraph as ig, leidenalg as la
exec(open("experimentos/e35_eventos_chicos.py").read().split("datos = {}")[0])
def foco(con):
    return con.execute("""with t as (select cuenta_id, narrativa||'/'||postura k, count(*) n from cm where narrativa<>'' group by 1,2),
        tot as (select cuenta_id, sum(n) tot from t group by 1)
        select t.cuenta_id, arg_max(k, n) k, max(n)/any_value(tot.tot) foco, any_value(tot.tot) tot
        from t join tot using(cuenta_id) group by 1""").df()
def via_foco(s, f, q, min_com, D=0.3, MINN=5):
    cand = f[f.tot >= min_com]
    umbral = cand.foco.quantile(q)
    cand = cand[cand.foco >= umbral].set_index("cuenta_id")
    e = s[s.x.isin(cand.index) & s.y.isin(cand.index)]
    e = e[cand.k.reindex(e.x).values == cand.k.reindex(e.y).values]
    if e.empty: return {}
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    m = np.asarray(la.find_partition(g, la.ModularityVertexPartition, seed=42).membership); out = {}
    for c in np.unique(m):
        idx = np.flatnonzero(m == c)
        if len(idx) >= MINN and g.induced_subgraph(idx).density() >= D:
            for i in idx: out[nod[i]] = f"foco{c}"
    return out
datos = {}
for nombre, (I, D) in SETS.items():
    con = co.conectar(Path(I), cfg)
    con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts,
        coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura from '{I}/comentarios.parquet' c
        left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
    datos[nombre] = (pares(con), foco(con), pd.read_csv(f"{D}/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False))
    print("listo", nombre, flush=True)
res = []
for q, mc in itertools.product([None, 0.95, 0.97, 0.98, 0.99], [4, 6]):
    pts = {}
    for nombre, (s, f, v) in datos.items():
        g = detectar_grupos(s, 2, 0.1, 3, 5, 0.3, 42, 0.5)
        if q is not None:
            extra = via_foco(s, f, q, mc)
            g = {**{a: gr for a, gr in extra.items()}, **g}   # el detector principal manda
        pts[nombre] = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": g.get(a, "")} for a in v.cuenta_id])["puntos"]
    res.append(dict(q=q, min_com=mc, media=np.mean(list(pts.values())), peor=min(pts.values()), **pts))
pd.set_option("display.width", 240); print(pd.DataFrame(res).round(2).sort_values("media", ascending=False).to_string(index=False))
