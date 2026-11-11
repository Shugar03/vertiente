"""E13 — Evidencia normalizada por actividad: fracción de las publicaciones de la cuenta menos activa que fueron ráfaga
compartida (raf_n) y solapamiento de publicaciones (obs/min(d)). Barrido."""
import itertools
import numpy as np, pandas as pd, igraph as ig, leidenalg as la
from radar.eval.puntaje import puntuar_coordinacion
exec(open("experimentos/e09_comunidades.py").read().split("LIFT =")[0])
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
deg = con.execute("select * from deg").df().set_index("cuenta_id").d
E["mind"] = np.minimum(deg.reindex(E.x).values, deg.reindex(E.y).values)
E["raf_n"] = E.raf / E.mind; E["ov"] = E.obs / E.mind
E["lift"] = E.obs / E.esp.clip(lower=1e-6)
print(E.assign(c=[(camp.get(a,'')!='' and camp.get(a)==camp.get(b)) for a,b in zip(E.x,E.y)]).groupby("c")[["raf_n","ov","lift","resp"]].describe(percentiles=[.5,.99,.999]).T.round(3).to_string())

def detectar(RAFN, OV, GAMMA, PODA=0.3, MINN=5):
    ev = ((E.raf >= 2) & (E.raf_n >= RAFN)).astype(int) + ((E.ov >= OV) & (E.obs >= 3) & (E.lift >= 3)).astype(int) \
         + (E.txt >= 2).astype(int) + (E.resp >= 1).astype(int)
    F = E[ev >= 1].copy(); F["ev"] = ev[ev >= 1]
    nodos = pd.Index(pd.unique(F[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(F.x), nodos.get_indexer(F.y)))); g.es["weight"] = F.ev.tolist()
    memb = np.array(la.find_partition(g, la.CPMVertexPartition, weights="weight", resolution_parameter=GAMMA, seed=42).membership)
    grupos = {}
    for k in np.unique(memb):
        idx = np.where(memb == k)[0]
        if len(idx) < MINN: continue
        while True:
            d = np.array(g.induced_subgraph(idx).degree()); keep = d >= PODA * (len(d) - 1)
            if keep.all() or keep.sum() < MINN: break
            idx = idx[keep]
        if len(idx) >= MINN and keep.all():
            for i in idx: grupos[nodos[i]] = f"g{k}"
    pred = [{"cuenta_id": a, "grupo": grupos.get(a, "")} for a in v.cuenta_id]
    return puntuar_coordinacion(v.to_dict("records"), pred), len(set(grupos.values()))

for RAFN, OV, G in itertools.product([0.15, 0.25], [0.3, 0.5], [0.3, 0.5]):
    r, ng = detectar(RAFN, OV, G)
    print(f"rafn={RAFN} ov={OV} gamma={G} grupos={ng} P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1']:.3f} grupos_b={r['grupos_bcubed_f1']:.3f} -> {r['puntos']}", flush=True)
