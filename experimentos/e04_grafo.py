"""E04 — Narrativas = comunidades del grafo (similitud entre textos + respuestas). Postura = 2-coloreo.

Pasos: 1) microgrupos por Leiden sobre kNN de textos únicos; 2) grafo de microgrupos con aristas de respuesta;
3) componentes/Leiden -> narrativas; 4) ruido = microgrupos sin respuestas; 5) postura por 2-coloreo + "quién empezó".
Se evalúa con la réplica del puntaje oficial.
"""
import sys, time
from collections import Counter, defaultdict
import duckdb, numpy as np, pandas as pd, torch, igraph as ig, leidenalg as la
from radar.embed import Embedder
from radar.eval.puntaje import puntuar_narrativas
from pathlib import Path

RES = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
K = 10
t0 = time.perf_counter()
c = duckdb.sql("select * from 'interim/practica/comentarios.parquet'").df()
u = c.groupby("texto_hash").agg(t=("texto_norm", "first"), n=("comentario_id", "size")).reset_index()
X, _ = Embedder("intfloat/multilingual-e5-small", Path("interim/cache_emb")).embeber(u.texto_hash.tolist(), u.t.tolist())
Xt = torch.from_numpy(X).to("mps")
src, dst, w = [], [], []
for i in range(0, len(Xt), 4096):
    S = Xt[i:i+4096] @ Xt.T
    S[torch.arange(S.shape[0]), torch.arange(i, i+S.shape[0])] = -1
    v, idx = S.topk(K, dim=1)
    src += np.repeat(np.arange(i, i+S.shape[0]), K).tolist(); dst += idx.flatten().cpu().tolist(); w += v.flatten().cpu().tolist()
g = ig.Graph(n=len(u), edges=list(zip(src, dst)), directed=False); g.es["weight"] = w; g.simplify(combine_edges="max")
part = la.find_partition(g, la.RBConfigurationVertexPartition, weights="weight", resolution_parameter=RES, seed=42)
u["micro"] = part.membership
print(f"microgrupos={len(set(part.membership))} ({time.perf_counter()-t0:.0f}s)")

c = c.merge(u[["texto_hash", "micro"]], on="texto_hash")
mic = dict(zip(c.comentario_id, c.micro)); padre = dict(zip(c.comentario_id, c.respuesta_a))
corto = c.texto_norm.str.split().str.len().fillna(0) <= 4
# textos de acompañamiento: respuestas cortas cuyo texto aparece respondiendo a muchos microgrupos distintos
resp = c[c.respuesta_a.notna()].copy(); resp["mp"] = resp.respuesta_a.map(mic)
disp = resp.groupby("texto_hash").mp.nunique()
acomp = set(disp[disp >= 5].index) & set(c[corto].texto_hash)
print("textos de acompañamiento:", len(acomp))
# aristas entre microgrupos por respuestas con contenido (inversión de postura)
E = Counter()
for r in resp.itertuples():
    if r.texto_hash in acomp: continue
    a, b = r.micro, r.mp
    if a != b: E[tuple(sorted((a, b)))] += 1
gm = ig.Graph(n=u.micro.max()+1, edges=list(E), directed=False); gm.es["weight"] = list(E.values())
deg = np.array(gm.strength(weights="weight"))
tam = c.groupby("micro").size().reindex(range(gm.vcount()), fill_value=0).to_numpy()
# narrativas: Leiden (modularidad) sobre el grafo de microgrupos con respuestas
pm = la.find_partition(gm, la.ModularityVertexPartition, weights="weight", seed=42)
narr_de_micro = np.array(pm.membership)
ratio = deg / np.maximum(tam, 1)
es_ruido_micro = ratio < 0.01
print("microgrupos ruido:", es_ruido_micro.sum(), "de", len(tam), "| comentarios en micro ruido:", tam[es_ruido_micro].sum())

# postura: 2-coloreo por BFS sobre aristas de inversión dentro de cada narrativa
lado = -np.ones(gm.vcount(), int)
for comp in set(narr_de_micro):
    nodos = [v for v in range(gm.vcount()) if narr_de_micro[v] == comp and not es_ruido_micro[v]]
    if not nodos: continue
    raiz = max(nodos, key=lambda v: tam[v]); lado[raiz] = 0; cola = [raiz]
    sub = set(nodos)
    while cola:
        v = cola.pop()
        for e in gm.incident(v):
            o = gm.es[e].target if gm.es[e].source == v else gm.es[e].source
            if o in sub and lado[o] < 0: lado[o] = 1 - lado[v]; cola.append(o)
# qué lado "apoya": el que aparece primero
c["narr"] = c.micro.map(lambda m: -1 if es_ruido_micro[m] else narr_de_micro[m])
c["lado"] = c.micro.map(lambda m: lado[m])
# herencia: acompañamiento hereda narrativa y lado del padre (recursivo)
cid_idx = dict(zip(c.comentario_id, range(len(c))))
narr = c.narr.to_numpy().copy(); ld = c.lado.to_numpy().copy(); th = c.texto_hash.to_numpy()
def resolver(i, prof=0):
    p = padre[c.comentario_id.iat[i]]
    if th[i] in acomp and p is not None and prof < 10:
        j = cid_idx[p]; resolver(j, prof+1); narr[i], ld[i] = narr[j], ld[j]
for i in np.where(c.respuesta_a.notna().to_numpy())[0]: resolver(i)
# no-respuestas de acompañamiento -> ruido
narr[np.isin(th, list(acomp)) & c.respuesta_a.isna().to_numpy()] = -1
c["narr"], c["lado"] = narr, ld
primero = c[c.narr >= 0].groupby(["narr", "lado"]).ts.min().reset_index()
apoya_lado = primero.sort_values("ts").groupby("narr").lado.first().to_dict()
c["postura"] = [("apoya" if l == apoya_lado.get(n) else "rechaza") if n >= 0 else "" for n, l in zip(c.narr, c.lado)]
c["narrativa"] = [f"n{n:03d}" if n >= 0 else "" for n in c.narr]
orig = c[c.narr >= 0].groupby("narrativa").ts.min()
pred_n = [{"narrativa": k, "fecha_origen": v.tz_convert("America/Argentina/Buenos_Aires").isoformat()} for k, v in orig.items()]
vc = pd.read_csv("datos/practica/verdad/comentarios.csv.gz", dtype=str, keep_default_na=False).to_dict("records")
vn = pd.read_csv("datos/practica/verdad/narrativas.csv", dtype=str, keep_default_na=False).to_dict("records")
r = puntuar_narrativas(vc, vn, c[["comentario_id", "narrativa", "postura"]].to_dict("records"), pred_n)
print(f"RES={RES} narrativas={c.narrativa[c.narrativa!=''].nunique()}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
print(f"total {time.perf_counter()-t0:.0f}s")

# ---------- diagnóstico ----------
if "--diag" in sys.argv:
    v = pd.DataFrame(vc)
    d = c.merge(v, on="comentario_id")
    mp = d[d.narrativa_id != "ninguna"].groupby("micro").apply(lambda g: (g.narrativa_id + g.postura_y).value_counts(normalize=True).iloc[0])
    print("pureza (narr,postura) por microgrupo: media=%.3f, microgrupos<0.9: %d" % (mp.mean(), (mp < 0.9).sum()))
    nn = d[d.narrativa_id != "ninguna"]
    for n_, g in nn.groupby("narrativa_id"):
        acc = (g.postura_x == g.postura_y).mean()
        print(n_, "acierto postura=%.2f (invertido=%.2f)" % (acc, 1 - acc), "narr_pred:", g.narrativa.value_counts().index[0])
    rr = d[d.narrativa_id == "ninguna"]
    print("ruido real -> predicho narrativa:", (rr.narrativa != "").sum(), "de", len(rr))
    print(rr[rr.narrativa != ""].groupby("micro").size().sort_values(ascending=False).head(10).to_string())
    top = rr[rr.narrativa != ""].groupby("micro").size().sort_values(ascending=False).head(3).index
    for m in top:
        print(m, "ratio=%.3f tam=%d" % (ratio[m], tam[m]), d[d.micro == m].texto.sample(5, random_state=0).tolist())
    l5 = d[d.narrativa_id == "L5"]; print("L5 min ts real:", l5.ts.min(), "| pred origen:", orig.get(l5.narrativa.value_counts().index[0]))
    print(d[(d.narrativa == l5.narrativa.value_counts().index[0])].sort_values("ts").head(5)[["ts", "narrativa_id", "texto"]].to_string())
