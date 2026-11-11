"""E10 — CPM (densidad) sobre aristas con evidencia, poda por grado interno; barrido de umbrales. Mide F1 oficial."""
import sys, time, itertools
import duckdb, numpy as np, pandas as pd, igraph as ig, leidenalg as la
from radar.eval.puntaje import puntuar_coordinacion
exec(open("experimentos/e09_comunidades.py").read().split("LIFT =")[0])  # reutiliza la construcción de aristas E
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False)
E["lift"] = E.obs / E.esp.clip(lower=1e-6)

def detectar(L, OBS, GAMMA, PODA, MINN=5):
    ev = ((E.lift >= L) & (E.obs >= OBS)).astype(int) + (E.raf >= 2).astype(int) + (E.txt >= 1).astype(int) + (E.resp >= 1).astype(int)
    F = E[ev >= 1]
    nodos = pd.Index(pd.unique(F[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(F.x), nodos.get_indexer(F.y))))
    g.es["weight"] = ev[ev >= 1].tolist()
    memb = np.array(la.find_partition(g, la.CPMVertexPartition, weights="weight", resolution_parameter=GAMMA, seed=42).membership)
    grupos = {}
    for k in np.unique(memb):
        idx = np.where(memb == k)[0]
        if len(idx) < MINN: continue
        sub = g.induced_subgraph(idx)
        while True:  # poda: fuera los de grado interno bajo
            d = np.array(sub.degree()); keep = d >= PODA * (len(d) - 1)
            if keep.all() or keep.sum() < MINN: break
            idx = idx[keep]; sub = g.induced_subgraph(idx)
        if len(idx) >= MINN and keep.all():
            for i in idx: grupos[nodos[i]] = f"g{k}"
    pred = [{"cuenta_id": a, "grupo": grupos.get(a, "")} for a in v.cuenta_id]
    return puntuar_coordinacion(v.to_dict("records"), pred), len(set(grupos.values()))

for L, OBS, G, P in itertools.product([4, 6], [3], [0.3, 0.5], [0.3, 0.5]):
    r, ng = detectar(L, OBS, G, P)
    print(f"L={L} OBS={OBS} gamma={G} poda={P} grupos={ng} P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1']:.3f} "
          f"grupos={r['grupos_bcubed_f1']:.3f} -> {r['puntos']}", flush=True)
