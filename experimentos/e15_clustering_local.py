"""E15 — Clustering local (camarilla) en grafos de evidencia + rasgos de cuenta. ¿Qué separa campañas de genuinas?"""
import numpy as np, pandas as pd, igraph as ig
exec(open("experimentos/e09_comunidades.py").read().split("LIFT =")[0])
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
deg = con.execute("select * from deg").df().set_index("cuenta_id").d
E["mind"] = np.minimum(deg.reindex(E.x).values, deg.reindex(E.y).values)
E["raf_n"] = E.raf / E.mind; E["ov"] = E.obs / E.mind; E["lift"] = E.obs / E.esp.clip(lower=1e-6)
feat = pd.DataFrame(index=v.cuenta_id)
def trans(mask, nombre):
    F = E[mask]; nodos = pd.Index(pd.unique(F[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(F.x), nodos.get_indexer(F.y))))
    feat[nombre + "_cc"] = pd.Series(g.transitivity_local_undirected(mode="zero"), index=nodos)
    feat[nombre + "_deg"] = pd.Series(g.degree(), index=nodos)
trans((E.raf >= 2) & (E.raf_n >= 0.15), "raf")
trans((E.lift >= 4) & (E.obs >= 3), "lift")
trans(E.txt >= 2, "txt")
cu = con.execute("""select k.cuenta_id, date_diff('day', fecha_creacion, (select min(ts)::date from c)) antig,
   coalesce(siguiendo,0)/(coalesce(seguidores,0)+1) ratio_sig from 'interim/practica/cuentas.parquet' k""").df().set_index("cuenta_id")
ac = con.execute("""select cuenta_id, count(*) n_com, avg((hour(ts at time zone 'America/Argentina/Buenos_Aires') between 0 and 5)::int) noche,
   avg(regexp_matches(texto, '#\\w+')::int) hashtag, avg((respuesta_a is not null)::int) resp from c group by 1""").df().set_index("cuenta_id")
feat = feat.join(cu).join(ac).fillna(0)
feat["camp"] = [camp.get(a, "") for a in feat.index]
pd.set_option("display.width", 250)
print(feat.groupby("camp").median().round(3).to_string())
print(feat[feat.camp == ""].quantile([.9, .99, .999]).round(3).to_string())
feat.to_parquet("interim/e15_feat.parquet")
