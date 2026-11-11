"""E26 — Estabilidad del detector ante el orden de filas. Leiden por defecto vs convergencia vs mejor de N semillas."""
import numpy as np, pandas as pd, igraph as ig, leidenalg as la, yaml
from pathlib import Path
from radar.stages import coordinacion as co
from radar.coordinacion.grafo import filtrar_vecinos_comunes
from radar.coordinacion.senales import sincronias_alineadas
from radar.eval.puntaje import puntuar_coordinacion
cfg = yaml.safe_load(open("config.yaml")); I = Path("interim/practica")
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False)
con = co.conectar(I, cfg); con.execute(f"""create table cm as select c.comentario_id, c.cuenta_id, c.publicacion_id, c.ts, c.respuesta_a,
    coalesce(a.narrativa,'') narrativa, coalesce(a.postura,'') postura from '{I}/comentarios.parquet' c left join '{I}/narrativas_asig.parquet' a using(comentario_id)""")
sync = sincronias_alineadas(con, "cm", 30)
e0 = filtrar_vecinos_comunes(sync[(sync.sync >= 2) & (sync.sync_n >= 0.1)][["x", "y"]].sort_values(["x", "y"]), 3)
def detectar(e, modo):
    nod = pd.Index(pd.unique(e[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nod), edges=list(zip(nod.get_indexer(e.x), nod.get_indexer(e.y))))
    if modo == "defecto": m = la.find_partition(g, la.ModularityVertexPartition, seed=42).membership
    elif modo == "converge": m = la.find_partition(g, la.ModularityVertexPartition, seed=42, n_iterations=-1).membership
    else:
        best = max((la.find_partition(g, la.ModularityVertexPartition, seed=s, n_iterations=-1) for s in range(10)), key=lambda p: p.quality())
        m = best.membership
    m = np.asarray(m); out = {}
    for k in np.unique(m):
        idx = np.flatnonzero(m == k)
        if len(idx) >= 5 and g.induced_subgraph(idx).density() >= 0.3:
            for i in idx: out[nod[i]] = k
    return out
for modo in ["defecto", "converge", "mejor10"]:
    pts = []
    for r in range(10):
        e = e0.sample(frac=1, random_state=r)
        gd = detectar(e, modo)
        pts.append(puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": str(gd.get(a, ""))} for a in v.cuenta_id])["puntos"])
    print(modo, "min=%.2f media=%.2f max=%.2f" % (min(pts), np.mean(pts), max(pts)), [round(p, 1) for p in pts])
