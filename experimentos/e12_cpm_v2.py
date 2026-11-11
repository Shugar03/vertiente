"""E12 — Evidencia de texto exige >=2 textos distintos compartidos (los memes comparten 1). Barrido + estadísticos de grupos."""
import itertools
import numpy as np, pandas as pd, igraph as ig, leidenalg as la
from radar.eval.puntaje import puntuar_coordinacion
exec(open("experimentos/e09_comunidades.py").read().split("LIFT =")[0])
v = pd.read_csv("datos/practica/verdad/cuentas.csv.gz", dtype=str, keep_default_na=False); camp = dict(zip(v.cuenta_id, v.campana_id))
E["lift"] = E.obs / E.esp.clip(lower=1e-6)

def detectar(L, RAF, TXT, GAMMA, PODA=0.3, MINN=5, MINRAF=0.0, mostrar=False):
    ev = ((E.lift >= L) & (E.obs >= 3)).astype(int) + (E.raf >= RAF).astype(int) + (E.txt >= TXT).astype(int) + (E.resp >= 1).astype(int)
    F = E[ev >= 1].copy(); F["ev"] = ev[ev >= 1]
    nodos = pd.Index(pd.unique(F[["x", "y"]].values.ravel()))
    g = ig.Graph(n=len(nodos), edges=list(zip(nodos.get_indexer(F.x), nodos.get_indexer(F.y)))); g.es["weight"] = F.ev.tolist()
    memb = np.array(la.find_partition(g, la.CPMVertexPartition, weights="weight", resolution_parameter=GAMMA, seed=42).membership)
    grupos, filas = {}, []
    for k in np.unique(memb):
        idx = np.where(memb == k)[0]
        if len(idx) < MINN: continue
        while True:
            sub = g.induced_subgraph(idx); d = np.array(sub.degree()); keep = d >= PODA * (len(d) - 1)
            if keep.all() or keep.sum() < MINN: break
            idx = idx[keep]
        if len(idx) < MINN or not keep.all(): continue
        miembros = set(nodos[idx]); e = F[F.x.isin(miembros) & F.y.isin(miembros)]; pares = len(idx) * (len(idx) - 1) / 2
        st = dict(k=k, n=len(idx), raf=e.raf.sum()/pares, txt=e.txt.sum()/pares, resp=e.resp.sum()/pares,
                  lift=((e.lift >= L) & (e.obs >= 3)).sum()/pares, frac_camp=np.mean([camp.get(m, "") != "" for m in miembros]))
        filas.append(st)
        if st["raf"] >= MINRAF:
            for m in miembros: grupos[m] = f"g{k}"
    pred = [{"cuenta_id": a, "grupo": grupos.get(a, "")} for a in v.cuenta_id]
    if mostrar: print(pd.DataFrame(filas).sort_values("raf", ascending=False).head(12).round(3).to_string())
    return puntuar_coordinacion(v.to_dict("records"), pred)

detectar(6, 2, 2, 0.5, mostrar=True)
for L, RAF, TXT, G, MR in itertools.product([6], [2, 3], [2], [0.3, 0.5], [0, 0.5, 1.0]):
    r = detectar(L, RAF, TXT, G, MINRAF=MR)
    print(f"L={L} RAF={RAF} TXT={TXT} gamma={G} minraf={MR} P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1']:.3f} grupos={r['grupos_bcubed_f1']:.3f} -> {r['puntos']}", flush=True)
