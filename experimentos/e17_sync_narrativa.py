"""E17 — Ráfaga 'alineada': misma publicación + misma narrativa/postura + <= W min. ¿Separa campañas (incl. C2)?"""
import sys
import duckdb, numpy as np, pandas as pd, igraph as ig, leidenalg as la
from radar.eval.puntaje import puntuar_coordinacion
W = int(sys.argv[1]) if len(sys.argv) > 1 else 15
con = duckdb.connect()
con.execute("""create table c as select c.*, v.narrativa_id||'/'||coalesce(v.postura,'') np
  from 'interim/practica/comentarios.parquet' c join read_csv('datos/practica/verdad/comentarios.csv.gz', all_varchar=true) v using(comentario_id)
  where v.narrativa_id<>'ninguna'""")
con.execute("create table dn as select cuenta_id, count(distinct publicacion_id) d from c group by 1")
E = con.execute(f"""with s as (select least(a.cuenta_id,b.cuenta_id) x, greatest(a.cuenta_id,b.cuenta_id) y, count(distinct a.publicacion_id) sync
   from c a join c b on a.publicacion_id=b.publicacion_id and a.np=b.np and a.cuenta_id<>b.cuenta_id
   and b.ts between a.ts and a.ts + interval {W} minute group by 1,2)
   select s.*, s.sync/least(dx.d,dy.d) sync_n from s join dn dx on dx.cuenta_id=s.x join dn dy on dy.cuenta_id=s.y""").df()
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
E["mc"] = [camp.get(a, "") if camp.get(a, "") == camp.get(b, "") else "" for a, b in zip(E.x, E.y)]
print(E.groupby("mc")[["sync", "sync_n"]].describe(percentiles=[.5, .99, .999]).round(3).T.to_string())
for MS, MN in [(2, 0.2), (2, 0.3), (3, 0.2), (3, 0.3)]:
    F = E[(E.sync >= MS) & (E.sync_n >= MN)]
    nodos = pd.Index(pd.unique(F[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(F.x), nodos.get_indexer(F.y))))
    cc = pd.Series(g.transitivity_local_undirected(mode="zero"), index=nodos); dg = pd.Series(g.degree(), index=nodos)
    memb = np.array(la.find_partition(g, la.ModularityVertexPartition, seed=42).membership)
    grupos = {}
    for k in np.unique(memb):
        idx = np.where(memb == k)[0]
        if len(idx) < 5: continue
        sub = g.induced_subgraph(idx); dens = sub.density()
        if dens >= 0.3:
            for i in idx: grupos[nodos[i]] = f"g{k}"
    r = puntuar_coordinacion(v.to_dict("records"), [{"cuenta_id": a, "grupo": grupos.get(a, "")} for a in v.cuenta_id])
    print(f"W={W} sync>={MS} sync_n>={MN} aristas={len(F)} nodos={len(nodos)} P={r['precision']:.3f} R={r['recall']:.3f} "
          f"F1={r['f1']:.3f} grupos={r['grupos_bcubed_f1']:.3f} -> {r['puntos']}")
