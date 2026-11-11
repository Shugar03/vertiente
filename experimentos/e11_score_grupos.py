"""E11 — ¿Qué separa a un grupo-campaña de un grupo denso genuino? Estadísticos por grupo (CPM L=6 gamma=0.5 poda=0.3)."""
import itertools
import duckdb, numpy as np, pandas as pd, igraph as ig, leidenalg as la
exec(open("experimentos/e09_comunidades.py").read().split("LIFT =")[0])
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
E["lift"] = E.obs / E.esp.clip(lower=1e-6)
ev = ((E.lift >= 6) & (E.obs >= 3)).astype(int) + (E.raf >= 2).astype(int) + (E.txt >= 1).astype(int) + (E.resp >= 1).astype(int)
F = E[ev >= 1].copy(); F["ev"] = ev[ev >= 1]
nodos = pd.Index(pd.unique(F[["x", "y"]].values.ravel()))
g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(F.x), nodos.get_indexer(F.y)))); g.es["weight"] = F.ev.tolist()
memb = np.array(la.find_partition(g, la.CPMVertexPartition, weights="weight", resolution_parameter=0.5, seed=42).membership)
grupo = pd.Series(memb, index=nodos)
acc = con.execute("""select k.cuenta_id, date_diff('day', fecha_creacion, (select min(ts)::date from c)) antig, seguidores, siguiendo,
  (select count(*) from c where c.cuenta_id=k.cuenta_id) n_com from 'interim/practica/cuentas.parquet' k""").df().set_index("cuenta_id")
hora = con.execute("""select cuenta_id, avg((hour(ts at time zone 'America/Argentina/Buenos_Aires') between 0 and 5)::int) noche,
  count(distinct texto_hash)/count(*) div_txt from c group by 1""").df().set_index("cuenta_id")
F["gx"] = grupo.reindex(F.x).values; F["gy"] = grupo.reindex(F.y).values
I = F[F.gx == F.gy]
filas = []
for k, mi in grupo.groupby(grupo):
    n = len(mi)
    if n < 5: continue
    e = I[I.gx == k]; pares = n * (n - 1) / 2
    a = acc.reindex(mi.index); h = hora.reindex(mi.index)
    filas.append(dict(g=k, n=n, dens=len(e)/pares, lift_frac=((e.lift >= 6) & (e.obs >= 3)).sum()/pares, raf=e.raf.sum()/pares,
        txt=e.txt.sum()/pares, resp=e.resp.sum()/pares, O_E=e.obs.sum()/max(e.esp.sum(), 1e-9),
        antig=a.antig.median(), ncom=a.n_com.median(), noche=h.noche.mean(), div=h.div_txt.mean(),
        camp=pd.Series([camp.get(x, "") for x in mi.index]).value_counts().index[0],
        frac_camp=np.mean([camp.get(x, "") != "" for x in mi.index])))
S = pd.DataFrame(filas)
pd.set_option("display.width", 250)
print(S[S.frac_camp > 0].round(3).to_string())
print(S[S.frac_camp == 0].describe(percentiles=[.5, .9, .99]).round(3).to_string())
S.to_parquet("interim/e11_grupos.parquet")
