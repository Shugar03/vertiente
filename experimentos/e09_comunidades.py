"""E09 — Comunidades en el grafo de pares con coincidencia alta; puntuación de cada comunidad vs lo esperable.
Aristas: publicaciones compartidas (lift) + ráfagas compartidas (misma publicación, <=15 min) + respuestas mutuas + textos idénticos."""
import sys, time
import duckdb, numpy as np, pandas as pd, igraph as ig, leidenalg as la
from radar.eval.puntaje import puntuar_coordinacion
t0 = time.perf_counter()
con = duckdb.connect()
con.execute("create table c as select * from 'interim/practica/comentarios.parquet'")
con.execute("create table ap as select distinct cuenta_id, publicacion_id from c")
con.execute("create table deg as select cuenta_id, count(*) d from ap group by 1")
con.execute("create table kp as select publicacion_id, count(*) k from ap group by 1")
S2, S1 = con.execute("select sum(k*(k-1)::double), sum(k::double) from kp").fetchone()
con.execute(f"""create table pares as
  select a.cuenta_id x, b.cuenta_id y, count(*) obs
  from ap a join ap b on a.publicacion_id=b.publicacion_id and a.cuenta_id<b.cuenta_id group by 1,2 having count(*)>=2""")
con.execute(f"""create table e_post as select p.x, p.y, p.obs, dx.d*dy.d*{S2}/({S1}*{S1}) esp
  from pares p join deg dx on dx.cuenta_id=p.x join deg dy on dy.cuenta_id=p.y""")
# ráfagas: misma publicación, a <= 15 min
con.execute("""create table e_raf as select least(a.cuenta_id,b.cuenta_id) x, greatest(a.cuenta_id,b.cuenta_id) y,
  count(distinct a.publicacion_id) raf from c a join c b on a.publicacion_id=b.publicacion_id and a.cuenta_id<>b.cuenta_id
  and b.ts between a.ts and a.ts + interval 15 minute group by 1,2 having count(distinct a.publicacion_id)>=2""")
con.execute("""create table e_txt as select least(a.cuenta_id,b.cuenta_id) x, greatest(a.cuenta_id,b.cuenta_id) y, count(distinct a.texto_hash) txt
  from c a join c b on a.texto_hash=b.texto_hash and a.cuenta_id<b.cuenta_id
  where a.texto_hash in (select texto_hash from c group by 1 having count(distinct cuenta_id) between 2 and 50) and length(a.texto_norm)>25
  group by 1,2""")
con.execute("""create table e_resp as select least(h.cuenta_id,p.cuenta_id) x, greatest(h.cuenta_id,p.cuenta_id) y, count(*) resp
  from c h join c p on h.respuesta_a=p.comentario_id where h.cuenta_id<>p.cuenta_id group by 1,2""")
E = con.execute("""select coalesce(p.x,r.x,t.x,q.x) x, coalesce(p.y,r.y,t.y,q.y) y, coalesce(p.obs,0) obs, coalesce(p.esp,0) esp,
   coalesce(r.raf,0) raf, coalesce(t.txt,0) txt, coalesce(q.resp,0) resp
  from e_post p full join e_raf r using(x,y) full join e_txt t using(x,y) full join e_resp q using(x,y)""").df()
print("aristas candidatas", len(E), f"{time.perf_counter()-t0:.0f}s")
LIFT = float(sys.argv[1]) if len(sys.argv) > 1 else 3
E["lift"] = E.obs / E.esp.clip(lower=1e-6)
E["w"] = (E.lift.clip(upper=50) * (E.obs >= 3) * (E.lift >= LIFT)) + 3 * E.raf + 3 * E.txt + 2 * E.resp
E = E[E.w > 0]
print("aristas fuertes", len(E))
nodos = pd.Index(pd.unique(E[["x", "y"]].values.ravel()))
g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(E.x), nodos.get_indexer(E.y)))); g.es["weight"] = E.w.tolist()
part = la.find_partition(g, la.ModularityVertexPartition, weights="weight", seed=42)
memb = np.array(part.membership)
# puntuar comunidades: densidad interna de aristas "con evidencia" y z del exceso de publicaciones compartidas
E["cx"] = memb[nodos.get_indexer(E.x)]; E["cy"] = memb[nodos.get_indexer(E.y)]
I = E[E.cx == E.cy]
st = I.groupby("cx").agg(aristas=("w", "size"), O=("obs", "sum"), Esp=("esp", "sum"), raf=("raf", "sum"), txt=("txt", "sum"), resp=("resp", "sum"))
st["n"] = pd.Series(memb).value_counts()
st["dens"] = st.aristas / (st.n * (st.n - 1) / 2)
st["z"] = (st.O - st.Esp) / np.sqrt(st.Esp + 1)
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False)
camp = dict(zip(v.cuenta_id, v.campana_id))
st["verdad"] = [pd.Series([camp.get(nodos[i], "") for i in np.where(memb == k)[0]]).value_counts().head(2).to_dict() for k in st.index]
print(st[(st.n >= 5)].sort_values("dens", ascending=False).head(15).to_string())
